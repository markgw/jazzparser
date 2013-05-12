"""Syntactic categories module for the music_halfspan formalism.

Syntactic classes for the halfspan formalism. Atomic categories in this 
formalism carry information about the start and end keys of the span 
and some cadence features. The formalism also uses modalities.

It's similar to music_keyspan, but simpler.

The old music_keyspan formalism used to have loads of unification 
stuff. At the moment, this formalism avoids the need for unification 
altogether. It may be that we need some (milder) form of unification, 
at which point we can use the same framework that keyspan used. For 
now, this is much neater for not needing this stuff.

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

import logging
import copy, re
from jazzparser.formalisms.base.syntax import SlashBase, SignBase, \
                ComplexCategoryBase, VariableSubstitutor, VariableSubstitution, \
                UnificationResultBase, AtomicCategoryBase, DummyCategoryBase
from jazzparser.formalisms.base.modalities import ModalSlash, \
                ModalComplexCategory, ModalAtomicCategory
from jazzparser.utils.chords import ChordError, chord_numeral_to_int, int_to_pitch_class
from jazzparser.utils.latex import filter_latex
from jazzparser.utils.tonalspace import root_to_et_coord
from .semantics import make_absolute_lf_from_relative

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class Slash(SlashBase, ModalSlash):
    def __init__(self, dir, modality=None, **kwargs):
        from . import Formalism
        if modality is None:
            modality = ''
        SlashBase.__init__(self, Formalism, dir, **kwargs)
        ModalSlash.__init__(self, modality)
        
    def copy(self):
        return Slash(self.forward, 
                     modality=self.modality)

class Sign(SignBase):
    """
    A CCG category and its associated semantics: a CCG sign.
    
    Keeps a note of which rules have been applied and which other 
    signs they were applied to, so that the parser can avoid re-applying 
    the same rule to the same inputs again.
    
    This overrides the base sign implementation with a few 
    formalism-specific things.
    
    """
    def __init__(self, *args, **kwargs):
        from . import Formalism
        super(Sign, self).__init__(Formalism, *args, **kwargs)
        
    def copy(self):
        return Sign(self.category.copy(),\
                    self.semantics.copy(),\
                    copy.copy(self.derivation_trace))
        
    def apply_lexical_features(self, features):
        if 'root' in features:
            # Assume the category and LF are supposed to be relative to the 
            #  chord root and make them absolute
            make_absolute_category_from_relative(self.category, features['root'])
            make_absolute_lf_from_relative(self.semantics, root_to_et_coord(features['root']))
        if 'duration' in features:
            self.set_duration(features['duration'])
        if 'time' in features:
            self.semantics.set_all_times(features['time'])
    
    def __str__(self):
        return "%s : %s" % (self.category, self.semantics)
        
    def format_result(self):
        return "%s : %s" % (self.category, self.semantics.format_result())
    
    def set_time(self, time):
        self.semantics.set_time(time)
        
    def set_duration(self, duration):
        self.semantics.lf.duration = duration

class ComplexCategory(ComplexCategoryBase, ModalComplexCategory):
    """
    In the halfspan formalism, complex categories are made up of an 
    argument half category, a slash and a result half category. Neither 
    the argument nor the result may be whole categories, atomic or 
    complex.
    
    This kind of complex category is hugely simpler than previous 
    incarnations, since there are no unification variables involved 
    anywhere.
    
    """
    ATOMIC = False
    
    def __init__(self, *args, **kwargs):
        from . import Formalism
        ComplexCategoryBase.__init__(self, Formalism, *args, **kwargs)
        
    def copy(self):
        return ComplexCategory(result=self.result.copy(),
                               slash=self.slash.copy(),
                               argument=self.argument.copy())
                               
    def __eq__(self, other):
        return type(other) == type(self) and \
               self.slash == other.slash and \
               self.argument == other.argument and \
               self.result == other.result

class HalfCategory(object):
    """
    One half of an atomic category, or the argument or result of a 
    complex category.
    Stores a root value and a chord function marker (which may be 
    a set of functions in the case of an argument half category).
    
    """
    def __init__(self, root_symbol=None, function='T', root_number=None):
        """
        Either root_symbol or root_number must be given.
        
        Will raise a ChordError if the root symbol can't be interpreted 
        as a root number.
        
        @type root_symbol: string
        @param root_symbol: symbol to interpret as the root of this 
            category. This will be converted to a root number.
        @type function: string or list of strings
        @param function: either a single function marker (usually 
            'T', 'D' and 'S') or a list of such function markers, 
            as in the case of a complex category's argument.
        @type root_number: int
        @param root_number: alternative to setting the root by a 
            symbol. This will be used in preferance to root_symbol if 
            given.
        
        """
        if root_number is not None:
            # This is already a numeric root
            self.root = root_number
        elif root_symbol is not None:
            try:
                # Try treating this as a chord root
                self.root = chord_numeral_to_int(root_symbol, strict=True)
            except ChordError, err:
                raise ChordError, "could not treat '%s' as a root "\
                    "symbol: %s" % (root_symbol, err)
        else:
            raise ValueError, "either root_symbol or root_number must "\
                "be given when creating a half category"
        
        if type(function) == str:
            self.functions = set([function])
        else:
            if len(function) == 0:
                raise ValueError, "cannot create a category with an "\
                    "empty set of possible functions"
            self.functions = set(function)
        
    def __str__(self):
        return "%s^%s" % (self.symbol, self.function_symbol)
        
    @property
    def function_symbol(self):
        """
        Readable representation of the category's function or 
        alternative functions.
        
        """
        if len(self.functions) > 1:
            return "|".join(self.functions)
        else:
            return self.function
    
    @property
    def function(self):
        """
        If the category has only one function (not a set of possible 
        functions), returns this. Otherwise returns None.
        
        """
        if len(self.functions) > 1:
            return None
        else:
            return list(self.functions)[0]
        
    @property
    def symbol(self):
        """Readable symbol of the category's root."""
        return int_to_pitch_class(self.root)
    
    @property
    def ambiguous_function(self):
        """True if the category has multiple possible functions"""
        return len(self.functions) > 1
        
    def __eq__(self, other):
        return type(self) == type(other) and \
                self.root == other.root and \
                self.functions == other.functions
    
    def __ne__(self, other):
        return not (self == other)
        
    def __hash__(self):
        return self.root
        
    def set_relative_to(self, root):
        """
        Changes the root value to a new root that is the original 
        root relative to the given root.
        """
        self.root = (root + self.root) % 12
        
    def copy(self):
        return HalfCategory(root_number=self.root,
                            function=[copy.copy(f) for f in self.functions])

    def to_latex(self):
        return "%s^{%s}" % (self.symbol, self.function_symbol)
        
    def matches(self, other):
        """
        Returns True if this half category, as the argument part of 
        a complex category, would accept the other half category as 
        the relevant part of its argument (in function application).
        
        """
        if other.ambiguous_function:
            # The other category must have only one possible function
            return False
        return other.root == self.root and other.function in self.functions

class AtomicCategory(AtomicCategoryBase, ModalAtomicCategory):
    """
    An atomic category is of the form A-B, where A and B are 
    half categories.
    
    """
    ATOMIC = True
    
    def __init__(self, from_half, to_half):
        from . import Formalism
        super(AtomicCategory, self).__init__(Formalism)
        self.from_half = from_half
        self.to_half = to_half
        
    @staticmethod
    def span(from_root, from_function,
             to_root, to_function):
        """
        Construct an atomic category without having to construct 
        the root parts yourself every time.
        
        C{from_root} and C{from_function} will get passed on to the 
        L{HalfCategory} constructor. Likewise C{to_root} and 
        C{to_function}.
        
        """
        return AtomicCategory(
            HalfCategory(from_root, from_function),
            HalfCategory(to_root, to_function))
    
    def copy(self):
        return AtomicCategory(self.from_half.copy(),
                              self.to_half.copy())
    
    def __hash__(self):
        return hash(self.from_half) + hash(self.to_half)
        
    def __str__(self):
        if self.from_half == self.to_half:
            return "%s" % self.from_half
        else:
            return "%s-%s" % (self.from_half, self.to_half)

    def to_latex(self):
        return "\\kcat{%s}{%s}" % (self.from_half.to_latex(),
                                    self.to_half.to_latex())
    
    def __eq__(self, other):
        return type(self) == type(other) and \
            self.from_half == other.from_half and \
            self.to_half == other.to_half

class DummyCategory(DummyCategoryBase):
    ATOMIC = None
    
    def __init__(self):
        from . import Formalism
        super(DummyCategory, self).__init__(Formalism)

################ Chart operations
def merge_equal_signs(existing_sign, new_sign):
    """
    Used when adding equal signs to the same edge in the chart. 
    Currently does nothing.
    
    """
    pass


########################################
######## Unification
"""
We don't use unification in this formalism (currently), but I'm 
keeping to the old unification framework so we can just slot into 
my nice general CCG base classes.

"""
class UnificationResult(UnificationResultBase):
    """
    Dummy unification results which allows us to use the unification 
    formalism without actually unifying any variables.
    
    """
    def apply_all_mappings(self, obj):
        """No mappings to distinguish variables, since we don't have any."""
        pass

def unify(category1, category2, grammar=None):
    """
    Dummy unification procedure.
    
    Unification succeeds if and only if the two categories are equal 
    (using their own definition of equality). The unification 
    constraints do nothing to the categories when applied.
    
    """
    if category1 != category2:
        return None
    category1 = category1.copy()
    category2 = category2.copy()
    # Create an empty constraint set using the base class for constraints
    constraints = VariableSubstitution()
    return UnificationResult(
            category1,
            constraints,
            [category1, category2]
        )

#######################
##     Utilities     ##
#######################
def make_absolute_category_from_relative(relative_cat, base_root):
    """
    Given a CCGCategory and an absolute chord root in integer form, 
    alters the category to that given by considering chord roots in the 
    input category to be relative to the root of base_chord.
    E.g. a V category when considered relative to a IV
    chord would render a I chord.
    
    """
    if type(relative_cat) == AtomicCategory:
        # Atomic category: adjust chord roots on either side
        relative_cat.from_half.set_relative_to(base_root)
        relative_cat.to_half.set_relative_to(base_root)
    elif type(relative_cat) == ComplexCategory:
        # Complex category: adjust roots of argument and result
        # No need for recursion in this formalism
        relative_cat.argument.set_relative_to(base_root)
        relative_cat.result.set_relative_to(base_root)
    else:
        raise TypeError, "Tried to alter a category object of the wrong type"
    return

def pre_generalize_category(category):
    """
    When abstracting categories to something general that just 
    represents the structure of the category, we have to do something 
    special with half categories, since the standard abstraction 
    routine expects the children of a complex category to be 
    atomic or complex categories themselves.
    
    @see: L{jazzparser.data.trees.build_tree_for_sequence}
    @see: L{jazzparser.data.trees.generalize_category}
    
    """
    from jazzparser.data.trees import AtomicCategory as GeneralAtomic
    if isinstance(category, HalfCategory):
        # Just treat it as an atomic category
        # This renders the structure fine: a complex category becomes 
        #  Atom/Atom or Atom\Atom, instead of Half/Half or Half\Half.
        return GeneralAtomic()
    else:
        # Pass processing on to the normal generalization routine
        return None


def syntax_from_string(string):
    """
    Builds a L{Category} instance from a string representation of the syntactic 
    category. This is mainly for testing and debugging and shouldn't be used in 
    the wild (in the parser, for example). This is not how we construct 
    categories out of the lexicon: they're specified in XML, which is a 
    safer way to build them, though more laborious to write.
    
    The strings may be constructed as follows.
    
    B{Full atomic category}: A-B. A and B are half categories (see below).
    
    B{Slash category}. Forward slash: A/B; optionally with a slash modality, 
    A/E{lb}mE{rb}B. Backward slash: A\\B or A\\E{lb}mE{rb}B. A and B are half 
    categories.
    
    B{Half category}: part of the above types. X^Y. 
    X must be a roman numeral chord root. 
    Y must be a function character (T, D or S), or multiple function characters. 
    E.g. I^T or VI^TD
    
    """
    def _find_matching(s, opener="{", closer="}"):
        opened = 0
        for i,char in enumerate(s):
            if char == closer:
                if opened == 0:
                    return i
                else:
                    opened -= 1
            elif char == opener:
                opened += 1
        # Matching brace not found
        raise SyntaxStringBuildError, "%s was not matched by a %s in %s" % \
            (opener, closer, s)
    
    fun_re = re.compile(r'^(?P<funs>[TDS]+)(?P<rest>.*)$')
    
    # Function to build a half category: used by atomic and complex categories
    def _build_half(text):
        text = text.strip()
        root,caret,functions = text.partition("^")
        
        # Check that the caret was in there
        if len(caret) == 0:
            raise SyntaxStringBuildError, "'%s' is not a valid half-category - "\
                "it has no ^ in it. Found in '%s'" % (text, string)
        # Check that valid function characters were used
        match = fun_re.match(functions)
        if match is None:
            raise SyntaxStringBuildError, "no function characters found at the "\
                "start of '%s' in '%s'" % (text,string)
        matchgd = match.groupdict()
        functions = list(matchgd['funs'])
        leftover = matchgd['rest'].strip()
        
        cat = HalfCategory(root_symbol=root, function=functions)
        return cat,leftover
    
    # Any category should start with a half category
    first_half,rest = _build_half(string)
    # Work out whether it's atomic or complex from what follows
    if rest.startswith("-"):
        # Atomic category
        # Get the second half
        second_half,rest = _build_half(rest[1:])
        
        cat = AtomicCategory(first_half, second_half)
    elif rest.startswith("\\") or rest.startswith("/"):
        # Complex category
        # Get the slash direction
        forward = (rest[0] == "/")
        rest = rest[1:].strip()
        # Look for a modality (optional)
        if rest[0] == "{":
            end = _find_matching(rest[1:]) + 1
            modality = rest[1:end]
            rest = rest[end+1:]
        else:
            modality = None
        slash = Slash(forward, modality=modality)
        
        # Interpret the remainder as a half-category
        second_half,rest = _build_half(rest)
        
        cat = ComplexCategory(first_half, slash, second_half)
    elif len(rest) == 0:
        # Implicit atomic category from half-category
        second_half = first_half.copy()
        cat = AtomicCategory(first_half, second_half)
    else:
        raise SyntaxStringBuildError, "couldn't recognise a category in '%s'" \
            % string
    
    if len(rest):
        raise SyntaxStringBuildError, "unexpected text '%s' in '%s'" % \
            (rest, string)
    return cat

def sign_from_string(string):
    """
    Simple combination of L{syntax_from_string} and 
    L{jazzparser.formalisms.music_halfspan.semantics.semantics_from_string} 
    to build a full sign from a string.
    
    """
    from .semantics import semantics_from_string
    
    synstr,colon,semstr = string.partition(":")
    if not colon:
        raise SignStringBuildError, "a sign must be of the form "\
            "'<syntax> : <semantics>'"
    category = syntax_from_string(synstr.strip())
    semantics = semantics_from_string(semstr.strip())
    return Sign(category, semantics)

class SyntaxStringBuildError(Exception):
    pass

class SignStringBuildError(Exception):
    pass

