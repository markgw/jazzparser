"""Grammar rules module for the music_halfspan formalism.

Grammatical rules for the keyspan formalism. A lot of this is standard 
CCG, with a few special additions.

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

import logging, copy
from jazzparser.formalisms.base.rules import ApplicationRuleBase, CompositionRuleBase, \
                        Rule
from jazzparser.formalisms.base.semantics.temporal import temporal_rule_apply
from jazzparser.formalisms.base.semantics.lambdacalc import distinguish_variables, \
                        next_unused_variable
from .syntax import AtomicCategory, Sign
from .semantics import concatenate, Variable, LambdaAbstraction, \
                        FunctionApplication, Semantics, Now, \
                        EnharmonicCoordinate, Coordination
from jazzparser.parsers import RuleApplicationError
from jazzparser import settings
from jazzparser.utils.tonalspace import coordinate_to_et_2d

# Get the logger from the logging system
logger = logging.getLogger("main_logger")


class ApplicationRule(ApplicationRuleBase):
    def __init__(self, *args, **kwargs):
        from . import Formalism
        super(ApplicationRule, self).__init__(Formalism, *args, **kwargs)
        
    def apply_rule(self, cat_list, proc_sems=None, *args, **kwargs):
        """
        For halfspan, the definition of the application rule is very 
        important. It's not the standard CCG application. Crucially, 
        it requires the argument part of the slash category to match 
        the nearest end of the argument category.
        
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
        if not self.formalism.Syntax.is_atomic_category(argument.category):
            return None
        if not self.formalism.Syntax.is_complex_category(functor.category):
            return None
        # Check right slash direction
        if functor.category.slash.forward != self.forward:
            return None
        
        if self.forward:
            near_argument = argument.category.from_half
        else:
            near_argument = argument.category.to_half
        
        # Here's the crucial check: 
        # in W/X Y-Z, X must match Y
        # in W-V Y\Z, Z must match V
        if not functor.category.argument.matches(near_argument):
            return None
        
        ################## Checks passed: apply the rule
        # Apply the unification substitutions
        # Build the new category out of the result part of the slash 
        #  category and the far part of the argument
        functor_cat = functor.category.copy()
        argument_cat = argument.category.copy()
        
        if self.forward:
            category = AtomicCategory(functor_cat.result, argument_cat.to_half)
        else:
            category = AtomicCategory(argument_cat.from_half, functor_cat.result)
        
        semantics = self.apply_rule_semantics(cat_list, proc_sems=proc_sems)[0]
        result = self.formalism.Syntax.Sign(category, semantics)
        
        if settings.WARN_ABOUT_FREE_VARS:
            free_vars = semantics.lf.get_unbound_variables()
            if free_vars:
                logger.warn("Found free variables after application: %s in %s" % (",".join(["%s" % var for var in free_vars]), semantics))
                
        return [result]
    
    @temporal_rule_apply(semantics_only=True)
    def apply_rule_semantics(self, cat_list, proc_sems=None):
        """
        Provides the semantic part of rule application separately from the 
        syntactic part.
        
        @see: L{jazzparser.formalisms.base.rules.Rule.apply_rule_semantics}
        
        """
        # Assume all syntactic checks have succeeded and do the semantic processing
        if self.forward:
            # X/Y Y => X
            functor = cat_list[0]
            argument = cat_list[1]
        else:
            # Y X\Y => X
            functor = cat_list[1]
            argument = cat_list[0]
        
        # Combine semantics by function application
        new_functor = functor.semantics.copy()
        new_argument = argument.semantics.copy()
        # Run any additional processing on the semantics of the inputs
        if proc_sems is not None:
            proc_sems(new_functor, new_argument)
        
        semantics = self.formalism.Semantics.apply(new_functor, new_argument, grammar=self.grammar)
        
        if settings.WARN_ABOUT_FREE_VARS:
            free_vars = semantics.lf.get_unbound_variables()
            if free_vars:
                logger.warn("Found free variables after application: %s in %s" % (",".join(["%s" % var for var in free_vars]), semantics))
        return [semantics]
                

class CompositionRule(CompositionRuleBase):
    def __init__(self, *args, **kwargs):
        from . import Formalism
        super(CompositionRule, self).__init__(Formalism, *args, **kwargs)
                
    def apply_rule(self, cat_list, proc_sems=None, *args, **kwargs):
        """
        Unlike application, composition could use the standard CCG 
        definition, but here we redefine it. This allows us to handle 
        multiple functions on arguments not by using unification, but 
        just by calling C{matches}.
        
        """
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
        
        # Extract the right bits according to whether it's forward or backward
        if self.forward:
            middle_arg = first.category.argument
            middle_res = second.category.result
        else:
            middle_arg = second.category.argument
            middle_res = first.category.result
        
        if not middle_arg.matches(middle_res):
            return None
        
        ################## Checks passed: apply the rule
        first_cat = first.category.copy()
        second_cat = second.category.copy()
        # Extract the right bits according to whether it's forward or backward.
        # This bit is the same for harmonic and crossing.
        if self.forward:
            result = first_cat.result
            argument = second_cat.argument
        else:
            result = second_cat.result
            argument = first_cat.argument
        
        # Harmonic: forward slashed result for forward slashed rule.
        # Crossing: backward slashed result for forward slashed rule.
        slash = self.formalism.Syntax.Slash(self.forward == self.harmonic)
        
        # Set the slash modality
        if first.category.slash.modality == '':
            slash.modality = second.category.slash.modality
        else:
            # The first slash is cadential. If the second is cadential, 
            #  they agree, so the result is cadential. If the second is empty, 
            #  the result is still cadential, since the first one wins.
            slash.modality = first.category.slash.modality
        
        category = self.formalism.Syntax.ComplexCategory(
                                result, \
                                slash, \
                                argument)
        
        semantics = self.apply_rule_semantics(cat_list, proc_sems=proc_sems)[0]
        result = self.formalism.Syntax.Sign(category, semantics)
        
        return [result]
    
    @temporal_rule_apply(semantics_only=True)
    def apply_rule_semantics(self, cat_list, proc_sems=None):
        """
        Provides the semantic part of rule application separately from the 
        syntactic part.
        
        @see: L{jazzparser.formalisms.base.rules.Rule.apply_rule_semantics}
        
        """
        # Assume all syntactic checks have succeeded and do the semantic processing
        if self.forward:
            fun_f = cat_list[0].semantics.copy()
            fun_g = cat_list[1].semantics.copy()
        else:
            fun_g = cat_list[0].semantics.copy()
            fun_f = cat_list[1].semantics.copy()
        
        # Make sure we don't confuse similarly-named variables
        # Don't think we should need to do this, because fun app should take care of it
        #from jazzparser.formalisms.base.semantics.lambdacalc import distinguish_variables
        #distinguish_variables(fun_f, fun_g)
        
        if proc_sems is not None:
            proc_sems(fun_f, fun_g)
        
        semantics = self.formalism.Semantics.compose(fun_f, fun_g)
        
        # Make sure semantics is in BNF
        semantics.beta_reduce(grammar=self.grammar)
        
        if settings.WARN_ABOUT_FREE_VARS:        
            free_vars = semantics.lf.get_unbound_variables()
            if free_vars:
                logger.warn("Found free variables after composition: %s in %s" % (",".join(["%s" % var for var in free_vars]), semantics))
        return [semantics]


class DevelopmentRule(Rule):
    """
    The development rule strings together sequences of resolved cadences.
    
    This used to be called "continuation" and was renamed long ago, but 
    the old name persisted in the keyspan implementation.
    
    """
    def __init__(self, *args, **kwargs):
        from . import Formalism
        super(DevelopmentRule, self).__init__(Formalism, *args, **kwargs)
        self.name = "<dev>"
        self.internal_name = "dev"
        self.readable_rule = "W-X Y-Z =>dev W-Z"
        
        self.arity = 2
    
    def apply_rule(self, cat_list, proc_sems=None):
        from . import Formalism
        ################## Check the rule is valid
        # Only 2 categories at a time
        if len(cat_list) != 2:
            return None
            
        # Can only apply to atomic categories
        if not Formalism.Syntax.is_atomic_category(cat_list[0].category) or \
           not Formalism.Syntax.is_atomic_category(cat_list[1].category):
            return None
        
        ################## Checks passed: apply the rule
        # Build the resulting syntactic category
        first_cat = cat_list[0].category
        second_cat = cat_list[1].category
        
        from .syntax import AtomicCategory
        result_cat = AtomicCategory(
            first_cat.from_half.copy(),
            second_cat.to_half.copy())
            
        semantics = self.apply_rule_semantics(cat_list, proc_sems=proc_sems)[0]
        
        return [Sign(result_cat, semantics)]
    
    @temporal_rule_apply(semantics_only=True)
    def apply_rule_semantics(self, cat_list, proc_sems=None):
        """
        Provides the semantic part of rule application separately from the 
        syntactic part.
        
        @see: L{jazzparser.formalisms.base.rules.Rule.apply_rule_semantics}
        
        """
        # Assume all syntactic checks have succeeded and do the semantic processing
        sem0 = cat_list[0].semantics.copy()
        sem1 = cat_list[1].semantics.copy()
        
        if proc_sems is not None:
            proc_sems(sem0, sem1)
        
        # The two inputs should be lists: just concatenate them
        semantics = concatenate(sem0, sem1)
        return [semantics]

class CoordinationRule(Rule):
    """
    The coordination rule allows partial cadences to combine and share 
    a resolution.
    
    """
    def __init__(self, *args, **kwargs):
        from . import Formalism
        super(CoordinationRule, self).__init__(Formalism, *args, **kwargs)
        self.name = "<&>"
        self.internal_name = "coord"
        self.readable_rule = "X/Y Z/Y =>& X/Y"
        
        self.arity = 2
    
    def apply_rule(self, cat_list, proc_sems=None):
        from . import Formalism
        ################## Check the rule is valid
        # Only 2 categories at a time
        if len(cat_list) != 2:
            return None
        cat0, cat1 = cat_list[0], cat_list[1]
            
        # Can only apply to cadential slash categories
        if not Formalism.Syntax.is_complex_category(cat0.category) or \
           not Formalism.Syntax.is_complex_category(cat1.category):
            return None
        
        # Both categories must have a cadence modality
        if not (cat0.category.slash.modality == cat1.category.slash.modality == 'c'):
            return None
        
        arg0, arg1 = cat0.category.argument, cat1.category.argument
        # Both categories must have an identical argument (except for 
        #  functions, see below)
        if not (arg0.root == arg1.root):
            return None
            
        # The categories must at least share some function on their arguments
        if arg0.functions.isdisjoint(arg1.functions):
            return None
            
        # They must have the same function on their result
        if not (cat0.category.result.functions == cat1.category.result.functions):
            return None
        
        ################## Checks passed: apply the rule
        # The result is syntactically the same as the first input
        new_cat = cat0.category.copy()
        # Restrict the argument to functions allowed by both the inputs' arguments
        new_cat.argument.functions = arg0.functions & arg1.functions
        
        semantics = self.apply_rule_semantics(cat_list, proc_sems=proc_sems)[0]
        result = self.formalism.Syntax.Sign(new_cat, semantics)
        
        return [result]
    
    @temporal_rule_apply(semantics_only=True)
    def apply_rule_semantics(self, cat_list, proc_sems=None):
        """
        Provides the semantic part of rule application separately from the 
        syntactic part.
        
        @see: L{jazzparser.formalisms.base.rules.Rule.apply_rule_semantics}
        
        """
        # Assume all syntactic checks have succeeded and do the semantic processing
        cad0 = cat_list[0].semantics.lf.copy()
        cad1 = cat_list[1].semantics.lf.copy()
        
        if proc_sems is not None:
            proc_sems(cad0, cad1)
        
        # Use the special coordination logical operator to combine these
        semantics = Semantics(
                        Coordination([cad0, cad1]))
        semantics.beta_reduce()
        
        if settings.WARN_ABOUT_FREE_VARS:        
            free_vars = semantics.lf.get_unbound_variables()
            if free_vars:
                logger.warn("Found free variables after coordination: %s in %s" % (",".join(["%s" % var for var in free_vars]), semantics))
        return [semantics]
        

class TonicRepetitionRule(Rule):
    """
    A special unary rule for expanding the lexicon to add tonic 
    repetition categories, generated from the tonic categories already 
    in the lexicon.
    
    This doesn't get used during parsing, but only to generate the 
    full lexicon when it's loaded up.
    
    It will expand any tonic category: X[T] => X[T]/X[T] : \\x.x
    
    """
    def __init__(self, *args, **kwargs):
        from . import Formalism
        super(TonicRepetitionRule, self).__init__(Formalism, *args, **kwargs)
        self.name = "<rep>"
        self.internal_name = "rep"
        self.readable_rule = "X[T] =>rep X[T]/X[T]"
        self.arity = 1
        
    def apply_rule(self, cat_list, proc_sems=None):
        from . import Formalism
        ################## Check the rule is valid
        # Unary rule
        if len(cat_list) != 1:
            return None
        sign = cat_list[0]
        cat = sign.category
            
        if not Formalism.Syntax.is_atomic_category(cat):
            return None
            
        # Lexical categories will only ever be specified as half 
        #  categories, since their start and end will always be equal.
        # Check that this is only being applied to such categories
        if cat.from_half != cat.to_half:
            return None
            
        ################## Checks passed: apply the rule
        # We need two half categories: both are the same as the halves 
        #  of the input cat
        new_res = cat.from_half.copy()
        new_arg = cat.from_half.copy()
        new_cat = Formalism.Syntax.ComplexCategory(
                    new_res,
                    Formalism.Syntax.Slash(dir=True),
                    new_arg)
        
        # Semantics for every result should be just \x.x
        semantics = Semantics(
                        LambdaAbstraction(
                            Variable("x"),
                            FunctionApplication(
                                Now(),
                                Variable("x")
                            )
                        ))
        
        result = Formalism.Syntax.Sign(new_cat, semantics)
        return [result]


class CadenceRepetitionRule(Rule):
    """
    A special unary rule for expanding the lexicon to add dominant 
    or subdominant repetition categories for all the substitutions, 
    generated from the cadential categories already in the lexicon.
    
    This doesn't get used during parsing, but only to generate the 
    full lexicon when it's loaded up.
    
    It will expand any cadence category: X[f]/c Y => X[f]/X[f] : \\x.x
    
    """
    def __init__(self, *args, **kwargs):
        from . import Formalism
        super(CadenceRepetitionRule, self).__init__(Formalism, *args, **kwargs)
        self.name = "<crep>"
        self.internal_name = "crep"
        self.readable_rule = "X[f]/c Y =>crep X[f]/X[f]"
        self.arity = 1
        
    def apply_rule(self, cat_list, proc_sems=None):
        from . import Formalism
        ################## Check the rule is valid
        # Unary rule
        if len(cat_list) != 1:
            return None
        sign = cat_list[0]
        cat = sign.category
            
        if not Formalism.Syntax.is_complex_category(cat):
            return None
            
        # Slash modality must be cadential
        if cat.slash.modality != "c":
            return None
            
        # Double-check that the function on the result is dominant 
        #  or subdominant (it should be, if the modality is cadential)
        if cat.result.function not in ["D","S"]:
            return None
            
        ################## Checks passed: apply the rule
        # We're only interested in the result part (because that 
        #  gives the syntactic starting point)
        new_res = cat.result.copy()
        new_arg = cat.result.copy()
        # The output has a non-cadential slash, because these things 
        #  don't constitute cadences on their own - only once they've 
        #  combined with another cadential cat
        new_cat = Formalism.Syntax.ComplexCategory(
                    new_res,
                    Formalism.Syntax.Slash(dir=True),
                    new_arg)
        
        # Semantics for every result should be just \x.x
        semantics = Semantics(
                        LambdaAbstraction(
                            Variable("x"),
                            FunctionApplication(
                                Now(),
                                Variable("x")
                            )
                        ))
        
        result = Formalism.Syntax.Sign(new_cat, semantics)
        return [result]
