"""Base classes for grammatical rules.

Base formalism rules: this provides the base classes for formalisms 
to define their rules with. All behaviour in here should be core CCG
rule behaviour common to all CCG formalisms.
Subclasses these rules in specific formalisms.

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
import copy

from jazzparser import settings

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class Rule(object):
    readable_rule = "Undefined"
    
    def __init__(self, formalism, *args, **kwargs):
        from jazzparser.grammar import GrammarReadError
        modalities = kwargs.pop('modalities', None)
        grammar = kwargs.pop('grammar', None)
        
        if formalism is None:
            raise GrammarReadError, "%s rule object was instantiated without a formalism argument." % type(self).__name__
        self.formalism = formalism
        if grammar is None:
            logger.warn("%s rule object was instantiated without a pointer to the grammar." % type(self).__name__)
        self.grammar = grammar
        if modalities is None:
            if self.grammar is None or self.grammar.modality_tree is None:
                raise GrammarReadError, "%s rule object was instantiated without a modality hierarchy and the grammar doesn't contain one" % type(self).__name__
            self.modalities = self.grammar.modality_tree
        else:
            self.modalities = modalities
        
    def apply_rule(self, cat_list):
        """
        *** This should be overridden by subclasses. ***
        Applies the rule to combine the categories in cat_list.
        
        Note that the returned semantics should always be in beta-normal form.
        
        @return: a list of the possible categories resulting from the 
        application if the rule is valid for the given arguments,
        otherwise None.
        
        """
        raise NotImplementedError, "Called abstract Rule.apply_rule()"
    
    def __str__(self):
        # This should be set for each implementation
        return "%s" % (self.readable_rule)
        
    def apply_rule_semantics(self, cat_list):
        """
        Performs the semantic processing involved in applying the rule to these 
        arguments.
        
        This doesn't do any checks on the syntactic type. If it's not used 
        in a situation where you know that the syntactic part of the application 
        will work, it could produce a non-sensical semantics or even raise 
        errors. It's designed for speeding up applying a rule to many signs 
        known to have the same syntactic type (so that the syntactic checks 
        only need to be done once).
        
        Depending on the formalism, this may not be any faster than calling 
        L{apply_rule} and getting the semantics from the results. In fact, 
        this is the default behaviour. Any sensible formalism will provide 
        a faster implementation of this method, though.
        
        @return: list of the Semantics objects that would be the logical 
        form parts of the results of the rule application.
        
        """
        return [res.semantics for res in self.apply_rule(cat_list)]
    
class ApplicationRuleBase(Rule):
    """
    Rule for standard CCG application.
    """
    def __init__(self, *args, **kwargs):
        """
        An application rule. May be forward or backward, depending on 
        the direction given in XML element.
        
        """
        self.forward = (kwargs.get('dir', "forward") == "forward")
        if self.forward:
            self.name = ">"
            self.internal_name = "appf"
        else:
            self.name = "<"
            self.internal_name = "appb"
        self.arity = 2
        if self.forward:
            self.readable_rule = "X/Y Y => X"
        else:
            self.readable_rule = "Y X\\Y => X"
        
        super(ApplicationRuleBase, self).__init__(*args, **kwargs)
    
    def apply_rule(self, cat_list, conditions=None, proc_sems=None):
        """
        conditions should be a callable that takes the functor followed 
        by the argument and returns a boolean. It will be run after 
        the basic applicability tests to check whether the rule should 
        be applied.
        If a function is given in proc_sems, it will be called to 
        process the semantics of the inputs before the resultant 
        semantics is built.
        """
        ################## Check the rule is valid
        # Must be applied to 2 args
        if len(cat_list) != 2:
            return None
        
        # Functor arg must be a slash category in the right direction        
        if self.forward:
            # X/Y Y => X
            functor = cat_list[0]
            argument = cat_list[1]
        else:
            # Y X\Y => X
            functor = cat_list[1]
            argument = cat_list[0]
        
        # Check correct cat type
        if not self.formalism.Syntax.is_complex_category(functor.category):
            return None
        
        # Check right slash direction
        if functor.category.slash.forward != self.forward:
            return None
        
        if conditions is not None:
            if not conditions(functor, argument):
                return None
        
        functor_cat = functor.category.copy()
        argument_cat = argument.category.copy()
        self.formalism.distinguish_categories(functor_cat, argument_cat)
        
        # Here's the crucial check: that the Y in the functor X/\Y is the same 
        #  as the argument
        unification_result = self.formalism.unify(functor_cat.argument, argument_cat, grammar=self.grammar)
        if unification_result is None:
            # Couldn't unify
            return None
        
        ################## Checks passed: apply the rule
        # Just return category X
        # Apply the unification substitutions
        # No need to apply the mappings: they were only applicable to the argument
        # Now ready to make the variable substitutions
        category = unification_result.constraints.apply(functor_cat.result)
            
        # Combine semantics by function application
        new_functor = functor.semantics.copy()
        new_argument = argument.semantics.copy()
        # Run any additional processing on the semantics of the inputs
        if proc_sems is not None:
            proc_sems(new_functor, new_argument)
        
        semantics = self.formalism.Semantics.apply(new_functor, new_argument, grammar=self.grammar)
        
        result = self.formalism.Syntax.Sign(category, semantics)
        
        if settings.WARN_ABOUT_FREE_VARS:
            free_vars = semantics.lf.get_unbound_variables()
            if free_vars:
                logger.warn("Found free variables after application: %s in %s" % (",".join(["%s" % var for var in free_vars]), semantics))
                
        return [result]
    


class CompositionRuleBase(Rule):
    """
    Rule for standard CCG composition.
    """
    def __init__(self, *args, **kwargs):
        super(CompositionRuleBase, self).__init__(*args, **kwargs)
        forward = (kwargs.get("dir", "forward") == "forward")
        harmonic = (kwargs.get("harmonic", "true") == "true")
        if forward:
            if harmonic:
                self.name = ">B"
                self.readable_rule = "X/Y Y/Z =>B X/Z"
                self.internal_name = "compf"
            else:
                self.name = ">Bx"
                self.readable_rule = "X/Y Y\\Z =>Bx X\\Z"
                self.internal_name = "xcompf"
        else:
            if harmonic:
                self.name = "<B"
                self.readable_rule = "Y\\Z X\\Y =>B X\\Z"
                self.internal_name = "compb"
            else:
                self.name = "<Bx"
                self.readable_rule = "Y/Z X\\Y =>Bx X/Z"
                self.internal_name = "xcompb"
                
        self.forward = forward
        self.harmonic = harmonic
        self.arity = 2
        
    def apply_rule(self, cat_list, conditions=None, proc_sems=None):
        ################## Check the rule is valid
        # Can only operate on 2 categories
        if len(cat_list) != 2:
            return None
        
        first = cat_list[0]
        second = cat_list[1]
        
        if not self.formalism.Syntax.is_complex_category(first.category) or \
                not self.formalism.Syntax.is_complex_category(second.category):
            return None
          
        if self.harmonic:
            if first.category.slash.forward != self.forward or \
                    second.category.slash.forward != self.forward:
                return None
        else:
            if not first.category.slash.forward or \
                    second.category.slash.forward:
                return None
        
        if conditions is not None:
            # Check extra conditions
            if not conditions(first, second):
                return None
                
        # Now we try the unification
        first_cat = first.category.copy()
        second_cat = second.category.copy()
        self.formalism.distinguish_categories(first_cat, second_cat)
        
        # Extract the right bits according to whether it's forward or backward
        if self.forward:
            middle1 = first_cat.argument
            middle2 = second_cat.result
        else:
            middle1 = first_cat.result
            middle2 = second_cat.argument
        
        # Check that composition is possible
        unification_result = self.formalism.unify(middle1, middle2, grammar=self.grammar)
        if unification_result is None:
            return None
        
        ################## Checks passed: apply the rule
        # Extract the right bits according to whether it's forward or backward.
        # This bit is the same for harmonic and crossing.
        if self.forward:
            result = first_cat.result
            argument = second_cat.argument
        else:
            result = second_cat.result
            argument = first_cat.argument
            
        if not self.forward:
            # Rename things like variables and slashes to match the unification conditions
            unification_result.apply_all_mappings(result)
        # Now ready to apply the variable bindings
        result = unification_result.constraints.apply(result)
        
        if self.forward:
            # Rename things like variables and slashes to match the unification conditions
            unification_result.apply_all_mappings(argument)
        # Now ready to apply the bindings to this one
        argument = unification_result.constraints.apply(argument)
        
        # Harmonic: forward slashed result for forward slashed rule.
        # Crossing: backward slashed result for forward slashed rule.
        slash = self.formalism.Syntax.Slash(self.forward == self.harmonic)
        category = self.formalism.Syntax.ComplexCategory(
                                result, \
                                slash, \
                                argument)
        
        # Now sort out the semantics
        if self.forward:
            fun_f = first.semantics.copy()
            fun_g = second.semantics.copy()
        else:
            fun_g = first.semantics.copy()
            fun_f = second.semantics.copy()
        
        # Make sure we don't confuse similarly-named variables
        from jazzparser.formalisms.base.semantics.lambdacalc import distinguish_variables
        distinguish_variables(fun_f, fun_g)
        
        if proc_sems is not None:
            proc_sems(fun_f, fun_g)
        semantics = self.formalism.Semantics.compose(fun_f, fun_g)
        
        # Make sure semantics is in BNF
        semantics.beta_reduce(grammar=self.grammar)
        
        if settings.WARN_ABOUT_FREE_VARS:        
            free_vars = semantics.lf.get_unbound_variables()
            if free_vars:
                logger.warn("Found free variables after composition: %s in %s" % (",".join(["%s" % var for var in free_vars]), semantics))
        
        result = self.formalism.Syntax.Sign(category, semantics)
        return [result]
    
