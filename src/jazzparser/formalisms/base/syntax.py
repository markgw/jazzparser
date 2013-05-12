"""Generic base CCG syntax classes.

Defines the internal representation of CCG categories for the Jazz Parser.
These should be subclassed in specific formalisms.
Everything in these base classes should be behaviour common to all 
CCG formalisms and defines the core CCG syntactic functionality.

"""
"""
============================== License ========================================
 Copyright (C) 2008, 2010-12 University of Edinburgh, Mark Granroth-Wilding
 
 This file is part of The Jazz Parser.
 
 The Jazz Parser is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 The Jazz Parser is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 
 You should have received a copy of the GNU General Public License
 along with The Jazz Parser.  If not, see <http://www.gnu.org/licenses/>.

============================ End license ======================================

"""
__author__ = "Mark Granroth-Wilding <mark.granroth-wilding@ed.ac.uk>" 

from jazzparser.utils.base import filter_latex
from jazzparser.utils.domxml import remove_unwanted_elements
from jazzparser.data.assignments import EquivalenceAssignment
from jazzparser.utils.chords import ChordError, chord_numeral_to_int, int_to_chord_numeral
from jazzparser.grammar import GrammarReadError
import logging, copy, re

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class SlashBase(object):
    def __init__(self, formalism, forward, id=0):
        self.forward = forward
        self.formalism = formalism
        self.id = id
                
    def __hash__(self):
        if self.forward:
            return 1
        else:
            return 0
            
    def __str__(self):
        if self.forward:
            val = "/"
        else:
            val = "\\"
        if hasattr(self, '_post_string'):
            val += self._post_string
        if hasattr(self, '_pre_string'):
            val = self._pre_string + val
        return val
    
    def to_latex(self):
        if self.forward:
            str = "/"
        else:
            str = "\\backslash "
        return filter_latex(str)
    
    def __eq__(self, other):
        if not ((self.__class__ == other.__class__) and \
                (self.forward == other.forward)):
            return False
        if hasattr(self, '_extra_eq') and not self._extra_eq(other):
            return False
        return True
               
    def __ne__(self, other):
        return not (self == other)
        
    def __repr__(self):
        return str(self)
        
    def copy(self):
        return SlashBase(self.formalism, self.forward, self.id)

class SignBase(object):
    """
    A CCG category and its associated semantics: a CCG sign.
    
    Keeps a note of which rules have been applied and which other 
    signs they were applied to, so that the parser can avoid re-applying 
    the same rule to the same inputs again.
    
    """
    def __init__(self, formalism, category, semantics, derivation_trace=None):
        """
        @type formalism: L{FormalismBase subclass<FormalismBase>}
        @param formalism: the formalism of the subclass.
        @type category: L{Category}
        @param category: the top level node of the category instance.
        @type semantics: L{Semantics<semantics.lambdacalc.Semantics>}
        @param semantics: the semantics part of the sign
        @type derivation_trace: L{DerivationTrace<jazzparser.data.DerivationTrace>}
        @param derivation_trace: a derivation trace to store how the 
            sign was derived (optional).
        
        """
        self.formalism = formalism
        self.category = category
        self.semantics = semantics
        self.unary_rules_applied = False
        self.derivation_trace = derivation_trace
        # This is not used until results are being processed. We give it
        #  a default value so it will be clear if the value hasn't been stored.
        self.result_index = -1
        # Note which rules have been applied
        self._unary_applied = []
        self._binary_applied = {}
        
    def __hash__(self):
        return hash(self.category)
        
    def copy(self):
        return SignBase(self.category.copy(),\
                        self.semantics.copy(),\
                        copy.copy(self.derivation_trace))
    
    def __str__(self):
         return "%s:%s" % (self.category, self.semantics)
     
    def __eq__(self, other):
        # Semantics need only be alpha-equivalent
        return (self.__class__ == other.__class__) and \
               (self.category == other.category) and \
               (self.semantics.alpha_equivalent(other.semantics))
    
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __repr__(self):
        return str(self)
    
    def to_latex(self):
        """
        @return: a Latex source representation of the object.
        """
        return "$%s:%s$" % (self.category.to_latex(), \
                               self.semantics.to_latex())
    
    def format_result(self):
        """
        Format the sign as a string for display in a list of results.
        By default, this just uses the class' str(), but subclasses 
        may provide an alternative format if required (you may want 
        signs to look different in results and in, e.g., chart 
        representation).
        
        """
        return str(self)
        
    def format_latex_result(self):
        """
        Same as L{format_result}, but returns latex source. By default 
        uses the class' L{to_latex} method.
        
        @see: L{format_result}
        
        """
        return self.to_latex()
    
    def apply_lexical_features(self, features):
        """
        Given a dictionary of features, applies any changes to this 
        sign that need to be made before it is added to the chart on 
        the basis of surface-level features (e.g. pitch, time).
        """
        return
                               
    def set_time(self, time):
        """
        Must be implemented by subclasses. Adds timing information 
        to components such that the start time of the whole sign 
        is encoded as the given time.
        
        """
        raise NotImplementedError, "set_time must be implemented by Sign subclasses."
        
    def set_duration(self, duration):
        """
        Must be implemented by subclasses. Adds duration information 
        to all components that store durations.
        """
        raise NotImplementedError, "set_duration must be implemented by Sign subclasses."
    
    def check_rule_applied(self, rule, other_input=None):
        """
        Returns True if the given rule instance has been applied to 
        this sign previously in the parse. If the rule is binary, 
        other_input should be given and this sign is assumed to be 
        the leftmore input.
        
        """
        if rule.arity == 1:
            return rule in self._unary_applied
        else:
            # Binary rule
            if other_input is None:
                raise ValueError, "tried to check whether a binary rule "\
                    "has been applied, but didn't give a second input"
            return rule in self._binary_applied and \
                    id(other_input) in self._binary_applied[rule]
                    
    def note_rule_applied(self, rule, other_input=None):
        """
        Keeps a note that the given rule was applied to this sign. If 
        it is a binary rule, you must also specify what the second 
        input was.
        
        """
        if rule.arity == 1:
            self._unary_applied.append(rule)
        else:
            if other_input is None:
                raise ValueError, "tried to note that a binary rule "\
                    "has been applied, but didn't give a second input"
            self._binary_applied.setdefault(rule, []).append(id(other_input))


class Category(object):
    """
    Parent class of categories (i.e. functional and atomic).
    """
    def __init__(self, formalism):
        self.formalism = formalism
    
    def __ne__(self, other):
        return not (self == other)
        
    def __repr__(self):
        return str(self)
        
    class CategoryParseError(Exception):
        pass


class ComplexCategoryBase(Category):
    def __init__(self, formalism, result, slash, argument):
        """A slash category must be initialised with
        a pair of categories (argument and result) that 
        appear on the right and left of the slash (respectively)
        and a Slash object.
        
        """
        super(ComplexCategoryBase, self).__init__(formalism)
        self.result = result
        self.argument = argument
        self.slash = slash
    
    def __hash__(self):
        return hash(self.result) + hash(self.argument) + hash(self.slash)
    
    def __str__(self):
        out_string = "("
        out_string += str(self.result)
        out_string += str(self.slash)
        out_string += str(self.argument)
        out_string += ")"
        return out_string
    
    def to_latex(self):
        out_string = "("
        out_string += self.result.to_latex()
        out_string += self.slash.to_latex()
        out_string += self.argument.to_latex()
        out_string += ")"
        return out_string
    
    def __eq__(self, other):
        return (other.__class__ == self.__class__) and \
               (other.result == self.result) and \
               (other.argument == self.argument) and \
               (other.slash == self.slash)
               
    def copy(self):
        return ComplexCategoryBase(self.formalism,
                                   self.result.copy(),
                                   self.slash.copy(),
                                   self.argument.copy())
        
    def _get_slash_ids(self):
        """
        Get a set of the ids on the slashes in this category.
        """
        return self.argument.slash_ids | self.result.slash_ids | set([self.slash.id])
    slash_ids = property(_get_slash_ids)
    
    def replace_slash_id(self, old_id, new_id):
        if self.slash.id == old_id:
            self.slash.id = new_id
        self.argument.replace_slash_id(old_id, new_id)
        self.result.replace_slash_id(old_id, new_id)

class AtomicCategoryBase(Category):
    """
    Much of the implementation of an atomic category is left to 
    subclasses, since this is where the most formalism-dependence is.
    """
    def __init__(self, formalism):
        super(AtomicCategoryBase, self).__init__(formalism)
        
    def __hash__(self):
        return 0
        
    def __str__(self):
        return "<?>"
        
    def to_latex(self):
        return "\textbf{?}"
        
    def copy(self):
        return AtomicCategoryBase(self.formalism)
        
    def _get_slash_ids(self):
        return set()
    slash_ids = property(_get_slash_ids)
    
    def replace_slash_id(self, old_id, new_id):
        pass
        
class DummyCategoryBase(Category):
    """
    A category type with no combinatorial power at all. This should never be 
    used in derivations, but supplies something to put in the category part 
    of a sign that has only a semantics (e.g. one that comes from a backoff 
    model).
    
    """
    def __init__(self, formalism):
        super(DummyCategoryBase, self).__init__(formalism)
        
    def __hash__(self):
        -1
        
    def __str__(self):
        return "DUMMY"
        
    def to_latex(self):
        return "$\epsilon$"
        
    def copy(self):
        return type(self)()
        
    slash_ids = set()
    def replace_slash_id(self, old, new):
        pass

class VariableSubstitutor(object):
    """
    An instance of VariableSubstitutor defines a type of variable forming 
    a component of categories. The instance defines how this variable type 
    is accessed and set, given a category and a key.
    """
    def __init__(self, name, value_setter, key_replacer, canonical_key=min):
        self.name = name
        self.methods = {
            'set' : value_setter,
            'replace' : key_replacer,
            'canonical' : canonical_key
        }
    
    def substitute(self, category, key, value):
        return self.methods['set'](category, key, value)
    def get_canonical_key(self, keylist):
        return self.methods['canonical'](keylist)
    def replace_key(self, category, old_key, new_key):
        self.methods['replace'](category, old_key, new_key)
        
    class InconsistencyError(Exception):
        pass
    class SubstitutionError(Exception):
        pass

class VariableSubstitution(dict):
    """
    A mapping from some sort of variable subject to unification that 
    appears in categories.
    The types of variables included in the substitution are defined by 
    variable substitutors. It is recommended that you subclass 
    variable substitution to provide a type of substition suitable to a 
    formalism.
    """
    def __init__(self, variable_types):
        self.assignments = {}
        self.types = {}
        for type in variable_types:
            super(VariableSubstitution, self).__setitem__(type.name, EquivalenceAssignment())
            self.types[type.name] = type
        # Once this is set, the equations will never be consistent again
        self._inconsistent = False
        
    def _is_inconsistent(self):
        for ass in self.values():
            if ass.inconsistent:
                return True
        return self._inconsistent
    inconsistent = property(_is_inconsistent)
    
    def __getitem__(self, type):
        if type not in self:
            raise VariableSubstitution.InvalidVariableTypeError, \
                "Tried to access assignments to a %s variable, but this "\
                "substitution doesn't store that type of assignment." % type
        return super(VariableSubstitution, self).__getitem__(type)
    
    def __setitem__(self, type, assignment):
        raise VariableSubstitution.VariableSubstitutionError, "Cannot change the variable "\
                "types of a variable substitution after instantiation"
            
    def add_assignment(self, type, key, value):
        """ Constrain the key to take a value that matches this one. """
        self[type][key] = value
    
    def add_equality(self, type, key, other_key):
        """ Constrain the two keys to take the same value. """
        self[type].add_equivalence(key, other_key)
        
    def get_assignment(self, type, key):
        """ Returns the value that this key is constrained to match. """
        return self[type][key]
        
    def get_equalities(self, type, key, pop=False):
        """ Returns all the key that are constrained to be equal to this one.
        Optionally remove this equivalence class in the process. """
        if pop:
            return self[type]._pop_class(key)
        else:
            return self[type]._get_class(key)
            
    def apply(self, category, make_copy=True):
        """ Applies the variable substitution to the given category object. """
        if make_copy:
            category = category.copy()
        for typename,assignment in self.items():
            type = self.types[typename]
            # For every key in the assignment that has a value, make 
            #  the actual assignment
            for key in assignment.keys():
                # Apply the setter to set the value of anything with 
                # this key in the category to be the assigned value
                type.substitute(category, key, assignment[key])
            # Replace each key remaining with the canonical key for its 
            #  equivalence class, so that the equivalence is implemented 
            #  even if there's no assignment to that key.
            keylists = assignment.classes
            for keylist in keylists:
                canonical = type.get_canonical_key(keylist)
                for key in keylist:
                    if key != canonical:
                        type.replace_key(category, key, canonical)
        return category
        
    def __str__(self):
        return "".join(["%s:%s" % (type, ass) for type,ass in self.items()])
        
    def __repr__(self):
        return str(self)
        
    class InvalidVariableTypeError(Exception):
        pass
    class VariableSubstitutionError(Exception):
        pass

                
class UnificationResultBase(object):
    """
    Class for the object returned as the result of unification. This 
    just bundles together the various bits of information that you 
    might need to get at after performing unification.
    It should be subclassed to add information specific to the formalism.
    """
    def __init__(self, result, constraints, inputs):
        self.result = result
        self.constraints = constraints
        self.inputs = inputs
        
    def apply_all_mappings(self, obj):
        """
        Most types of unification will require some mapping of variable 
        names to be applied to ensure they don't get clobbered. The 
        unification result should store all these mappings and supply 
        this method to apply them all at once to a category.
        """
        raise NotImplementedError, "The unification result class %s has not "\
            "supplied an implementation of apply_all_mappings()" % type(self).__name__
