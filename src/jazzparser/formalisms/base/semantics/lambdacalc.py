"""Lambda calculus semantic representations for the Jazz Parser.

Defines a set of base classes for use in defining and handling semantic 
interpretations of jazz chord sequences. These take the form of 
lambda-expressions containing predicates.

A semantic representation should be created as a Semantics object.
This should be initialised with a LogicalForm object defining
the logical form it represents.

LambdaAbstraction, FunctionApplication and Variable define the 
basic lambda expressions.

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

import copy
import logging
from jazzparser import settings

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class Semantics(object):
    """This acts as the root node in the LF's tree structure. Any
    LF that is built as a semantic representation should 
    be contained in an instance of Semantics.
    
    """
    def __init__(self, lf):
        """
        Creates a new container for a logical form. The
        logical form itself should be given as lf (an instance  
        of a subclass of LogicalForm)
        
        """
        self.lf = lf
        lf.parent = self
    
    def beta_reduce(self, *args, **kwargs):
        """
        Beta-reduction. Takes place in place 
        (i.e. the result will be substituted into the parent), but the 
        final result is returning, for convenience.
        
        """
        return self.lf.beta_reduce(*args, **kwargs)
    
    def replace_immediate_constituent(self, old_lf, new_lf):
        if self.lf is old_lf:
            self.lf = new_lf
            new_lf.parent = self
    
    def __eq__(self, expr):
        return (type(self) == type(expr)) and \
               (self.lf == expr.lf)
               
    def __ne__(self, other):
        return not (self == other)
               
    def alpha_equivalent(self, other):
        # Start with an empty substitution
        return self.lf.alpha_equivalent(other.lf, {})
    
    def __str__(self):
        return "%s" % (self.lf)
    
    def to_latex(self):
        return self.lf.to_latex()
    
    def get_children(self):
        return [self.lf]
    
    def copy(self):
        return type(self)(self.lf.copy())
        
    def get_ancestor_bound_variables(self):
        return set()
        
    def __repr__(self):
        return str(self)
        

class LogicalForm(object):
    """
    A semantic element, used to build the semantic
    interpretations returned by the parser.
    This class is effectively abstract. Most of its methods
    should be overridden.
    
    """
    def __init__(self):
        """ Builds a basic logical form object. """
        self.parent = None
    
    def alpha_convert(self, source_var, target_var):
        """This should be overridden by subclasses."""
        raise NotImplementedError, "Called abstract "\
            "LogicalForm.alpha_convert() on %s" % type(self).__name__
        
    def beta_reduce(self, *args, **kwargs):
        """This should be overridden by subclasses."""
        raise NotImplementedError, "Called abstract "\
            "LogicalForm.beta_reduce() on %s" % type(self).__name__
    
    def substitute(self, source_variable, target_expression):
        """This should be overridden by subclasses."""
        raise NotImplementedError, "Called abstract "\
            "LogicalForm.substitute() on %s" % type(self).__name__
        
    def replace_immediate_constituent(self, old_lf, new_lf):
        """
        This should be overridden by subclasses.
        It should replace the LogicalForm old_lf with new_lf if it
        appears as an immediate constituent of this LogicalForm.
        
        """
        raise NotImplementedError, "Called abstract "\
            "LogicalForm.replace_immediate_constituent() on %s" % \
            type(self).__name__
    
    def get_variables(self):
        """
        This should be overridden by subclasses.
        
        This method returns a list of all the variables
        used in this LF. This includes bound and unbound variables.
        (Only unbound variables need to be alpha-converted to 
        avoid accidental binding, but we will convert bound variables
        too for readability.)
        
        Note that this only contains one instance of each variable, 
        not every occurrence.
        
        """
        raise NotImplementedError, "Called abstract "\
            "LogicalForm.get_variables() on %s" % type(self).__name__
    
    def get_bound_variables(self):
        """This should be overridden by subclasses."""
        raise NotImplementedError, "Called abstract "\
            "LogicalForm.get_variables() on %s" % type(self).__name__
        
    def get_unbound_variables(self):
        return set(self.get_variables()) - set(self.get_bound_variables())
    
    def get_children(self):
        """This should be overridden by subclasses."""
        raise NotImplementedError, "Called abstract "\
            "LogicalForm.get_children() on %s" % type(self).__name__
    
    def get_instances(self, lf):
        """
        Returns all instances of logical forms equal to L{lf} among this 
        logical form and its descendents.
        This is particularly useful for getting all instances of a 
        variable.
        
        """
        insts = []
        if self == lf:
            insts.append(self)
        for child in self.get_children():
            insts.extend(child.get_instances(lf))
        return insts
    
    def alpha_equivalent(self, other, substitution):
        """This should be overridden by subclasses."""
        raise NotImplementedError, "Called abstract "\
            "LogicalForm.alpha_equivalent() on %s" % type(self).__name__
    
    def __eq__(self, other):
        """This should be overridden by subclasses."""
        raise NotImplementedError, "Called abstract "\
            "LogicalForm.__eq__() on %s" % type(self).__name__
    
    def __ne__(self, lf):
        return not (self == lf)
    
    def copy(self):
        """This should be overridden by subclasses."""
        raise NotImplementedError, "Called abstract "\
            "LogicalForm.copy() on %s" % type(self).__name__
        
    def replace_in_parent(self, other):
        """
        Replaces references in this LF's parent to this LF with references
        to the LF other.
        """
        self.parent.replace_immediate_constituent(self, other)
        
    def get_ancestor_bound_variables(self):
        """
        Returns all the variables that are bound at some point 
        higher up the structure and can therefore be used unbound within 
        this element.
        """
        if self.parent is not None:
            vars = self.parent.get_ancestor_bound_variables()
            if isinstance(self.parent, LambdaAbstraction):
                vars.add(self.parent.variable)
            return vars
        else:
            return set()
        
    def __repr__(self):
        return str(self)
      

class LambdaAbstraction(LogicalForm):
    """
    A type of complex logical form element corresponding
    to a lambda abstraction.
    
    """
    
    def __init__(self, variable, expression):
        """
        Builds a lambda abstraction. variable should be a 
        Variable object and expression should be another 
        LogicalForm, potentially containing the variable, 
        bound by this abstraction.
        
        """
        super(LambdaAbstraction, self).__init__()
        self.variable = variable.copy()
        self.variable.parent = self
        self.expression = expression.copy()
        self.expression.parent = self
        
    def copy(self):
        # Copying of these args is already done in the constructor
        return type(self)(self.variable, self.expression)
        
    def alpha_convert(self, source_var, target_var):
        self.variable.alpha_convert(source_var, target_var)
        self.expression.alpha_convert(source_var, target_var)
    
    def beta_reduce(self, *args, **kwargs):
        self.expression.beta_reduce(*args, **kwargs)
        return self
    
    def substitute(self, source_variable, target_expression):
        # Note: should never end up having to substitute the abstracted variable
        if source_variable == self.variable:
            logger.warning("Trying to substitute a bound variable: %s for %s in abstraction %s" % (target_expression, source_variable, self))
            raise ValueError, "Trying to substitute a bound variable: %s for %s in abstraction %s" % (target_expression, source_variable, self)
        self.expression.substitute(source_variable, target_expression)
        
    def replace_immediate_constituent(self, old_lf, new_lf):
        if self.variable is old_lf:
            self.variable.parent = None
            self.variable = new_lf
            new_lf.parent = self
        if self.expression is old_lf:
            self.expression.parent = None
            self.expression = new_lf
            new_lf.parent = self
            
    def get_variables(self):
        # Add the abstracted variable to the list
        our_var = [self.variable]
        # Recursively add all variables in sub-expressions
        return list(set(self.expression.get_variables() + our_var))
    
    def get_bound_variables(self):
        # Start with the abstracted variable
        vars = [self.variable]
        # Add any bound vars in the subexpression
        vars.extend(self.expression.get_bound_variables())
        return vars
    
    def __eq__(self, lf):
        return (type(lf) == type(self)) and \
               (self.variable == lf.variable) and \
               (self.expression == lf.expression)
               
    def alpha_equivalent(self, other, substitution):
        """
        Checks whether self is equal to a LF that can be derived by 
        some variable substitution S into other, where S contains the 
        substitution T given by "substitution".
        """
        # Must both be lambda abstractions
        if type(self) != type(other):
            return False
        # If the abstracted variable is in T, something's gone horribly wrong:
        #  it shouldn't yet be bound, so can't be in the current substitution.
        if other.variable in substitution:
            return False
        
        # Check self isn't already the target of a substitution
        if self in substitution.values():
            return False
        
        # We're allowed now to add a substitution to make the abstracted 
        #  variables equal
        # We might need to use a Variable class specific to the formalism
        if hasattr(type(self), 'VARIABLE_CLASS'):
            var_cls = type(self).VARIABLE_CLASS
        else:
            var_cls = Variable
        # This new substitution should only be used within this scope
        new_subst = copy.copy(substitution)
        new_subst[other.variable] = var_cls(self.variable.name, \
                                              self.variable.index)
        
        # Check that the subexpressions are alpha-equivalent, using this subst
        return self.expression.alpha_equivalent(other.expression, new_subst)
    
    def comma_string(self):
        """Returns the string that is to be used if this expression 
        follows another lambda abstraction.
        
        """
        output = self.variable.__str__()
        ## If the sub-expression is another abstraction, use comma notation for that
        if self.expression.__class__ == self.__class__:
            output += ","
            output += self.expression.comma_string()
        else:
            output += "."
            output += self.expression.__str__()
        return output
    
    def comma_latex(self):
        """Returns the Latex representation that is to be used if this expression 
        follows another lambda abstraction.
        
        """
        output = self.variable.to_latex()
        ## If the sub-expression is another abstraction, use comma notation for that
        if self.expression.__class__ == self.__class__:
            output += ","
            output += self.expression.comma_latex()
        else:
            output += "."
            output += self.expression.to_latex()
        return output
    
    def __str__(self):
        output = ""
        output += "\\"
        ## From here on, same as the comma string
        output += self.comma_string()
        return output
    
    def to_latex(self):
        output = "\\lambda "
        ## From here on, same as the comma string
        output += self.comma_latex()
        return output
    
    def get_children(self):
        return [self.variable, self.expression]

class Variable(LogicalForm):
    """A variable in a semantic expression."""
    
    def __init__(self, name, index=0):
        """Creates a new variable object, representing the 
        variable given by name.
        
        """
        super(Variable, self).__init__()
        self.name = name
        self.index = index
        
    def copy(self):
        return type(self)(copy.copy(self.name),copy.copy(self.index))
    
    def get_variable_name(self):
        return "%s%d" % (self.name, self.index)
        
    def alpha_convert(self, source_var, target_var):
        if (self.name == source_var.name) and (self.index == source_var.index):
            self.name = target_var.name
            self.index = target_var.index
    
    def beta_reduce(self, *args, **kwargs):
        # Doesn't do anything
        return self

    def substitute(self, source_variable, target_expression):
        if source_variable==self:
            new_expression = target_expression.copy()
            ## We've been asked to substitute self with another expression
            self.parent.replace_immediate_constituent(self, \
                                                      new_expression)
        
    def replace_immediate_constituent(self, old_lf, new_lf):
        # Variable has no constituents
        pass
    
    def get_variables(self):
        # This is a variable: base case
        return [self]
    
    def get_bound_variables(self):
        # This is an unbound variable. Return nothing.
        return []
    
    def __eq__(self, lf):
        """For the time being, two variables are considered equal
        if they have the same name. We could use some more elaborate
        internal representation if this turns out to be a problem,
        but if alpha conversion is carried out when it should be this
        method ought to be ok.
        
        """
        return (type(lf) == type(self)) and \
            (lf.name == self.name) and \
            (lf.index == self.index)
            
    def alpha_equivalent(self, other, substitution):
        """
        Checks whether self is equal to a LF that can be derived by 
        some variable substitution S into other, where S contains the 
        substitution T given by "substitution".
        """
        # Must both be variables
        if type(self) != type(other):
            return False
        
        # If there's a substitution for other, we use it. Otherwise,
        #  it must have been a free variable, so we add it to the substitution
        #  to make sure it's substituted in the same way everywhere
        if other in substitution:
            return self == substitution[other]
        else:
            # Check self isn't already the target of a substitution
            if self in substitution.values():
                return False
            substitution[other] = self.copy()
            return True
    
    def __str__(self):
        output = self.get_variable_name() 
        return output
    
    def to_latex(self):
        # Put the index as a subscript
        from jazzparser.utils.latex import filter_latex
        return "%s_{%d}" % (filter_latex(self.name), self.index)
    
    def get_children(self):
        return []
    
    def get_sibling_variables(self):
        """
        Returns a list of all the instances of Variable within 
        the logical form that represent the same variable.
        
        If it's a free variable, returns all other occurrences 
        within the logical form. If it's bound, returns all 
        other variables bound by the same abstraction.
        
        """
        parent = self
        while not (isinstance(parent, LambdaAbstraction) and \
                        parent.variable == self) and \
              not isinstance(parent, Semantics) and \
              parent.parent is not None:
            parent = parent.parent
        return parent.get_instances(self)
    
    def __hash__(self):
        return self.index
        

class FunctionApplication(LogicalForm):
    """
    A function application in a semantic expression.
    This is where all the real work goes on. Beta-reduction of function
    applications is the only bit that really does anything interesting.
    
    """
    INFIX_OPERATORS = []
    
    def __init__(self, functor, argument):
        """
        functor must be a lambda abstraction.
        argument can be any LogicalForm.
        
        """
        super(FunctionApplication, self).__init__()
        self.functor = functor.copy()
        self.functor.parent = self
        self.argument = argument.copy()
        self.argument.parent = self
        
    def copy(self):
        # Copying of args is done in the constructor anyway
        return type(self)(self.functor, self.argument)
        
    def alpha_convert(self, source_var, target_var):
        self.functor.alpha_convert(source_var, target_var)
        self.argument.alpha_convert(source_var, target_var)
    
    def beta_reduce(self, *args, **kwargs):
        ## Before doing anything else, the functor must be beta-converted
        self.functor.beta_reduce(*args, **kwargs)
        ## Now if the functor is a lambda expression, we must apply it to the arg
        if isinstance(self.functor, LambdaAbstraction):
            ## First make sure no variable in the functor occurs in the arg.
            # Free variables are fine to overlap - they might be bound higher up.
            arg_vars = set(self.argument.get_bound_variables())
            fun_vars = set(self.functor.get_bound_variables())
            # Also avoid using any variables bound higher up
            used_vars = set([
                            var.copy() for var in \
                                (arg_vars | 
                                 fun_vars | 
                                 self.get_ancestor_bound_variables())])
            # Alpha-convert each of the intersection's variables 
            #  in one of the expressions
            overlap = [var.copy() for var in (arg_vars & fun_vars)]
            for var in overlap:
                # Alpha-convert the argument to remove the potential accidental binding
                # Get a variable that's not been used yet in either expression
                new_var = next_unused_variable(var, used_vars)
                self.argument.alpha_convert(var, new_var)
                # Don't use the variable again
                used_vars.add(new_var)
            
            self.functor.expression.substitute(self.functor.variable, self.argument)
               
            ## self should now be replaced by this converted argument
            expr = self.functor.expression
            self.replace_in_parent(expr)
            
            ## Continue beta-conversion on the resulting expression
            return expr.beta_reduce(*args, **kwargs)
        elif hasattr(self.functor,'_function_apply'):
            # The functor defines its own function application behaviour
            self.argument.beta_reduce(*args, **kwargs)
            result = self.functor._function_apply(self.argument)
            if result is None:
                # Function application gave up: this means we're 
                #  in beta normal form already
                return self
            parent = self.parent
            self.replace_in_parent(result)
            
            # The new thing we've just put into our parent might not 
            #  yet be in BNF
            return result.beta_reduce(*args, **kwargs)
        else:
            ## Otherwise, just beta-convert the constituents
            # Functor already done
            self.argument.beta_reduce(*args, **kwargs)
            return self
    
    def substitute(self, source_variable, target_expression):
        try:
            self.functor.substitute(source_variable,target_expression)
            self.argument.substitute(source_variable,target_expression)
        except ValueError, err:
            raise ValueError, "%s. Within: %s" % (err, self)
        
    def replace_immediate_constituent(self, old_lf, new_lf):
        if self.functor is old_lf:
            old_functor = self.functor
            self.functor = new_lf
            new_lf.parent = self
            # Make sure the old functor is now orphaned
            old_functor.parent = None
        if self.argument is old_lf:
            old_argument = self.argument
            self.argument = new_lf
            new_lf.parent = self
            # Make sure the old argument is now orphaned
            old_argument.parent = None
    
    def get_variables(self):
        return list(set(self.functor.get_variables() + self.argument.get_variables()))
    
    def get_bound_variables(self):
        vars = []
        vars.extend(self.functor.get_bound_variables())
        vars.extend(self.argument.get_bound_variables())
        return vars
    
    def __eq__(self, lf):
        return (type(lf) == type(self)) and \
               (self.functor == lf.functor) and \
               (self.argument == lf.argument)
               
    def alpha_equivalent(self, other, substitution):
        """
        Checks whether self is equal to a LF that can be derived by 
        some variable substitution S into other, where S contains the 
        substitution T given by "substitution".
        """
        # Must both be applications
        if type(self) != type(other):
            return False
        
        # Recursively check equivalence of functor and arg using same substitution
        return self.functor.alpha_equivalent(other.functor, substitution) \
            and self.argument.alpha_equivalent(other.argument, substitution)
            
    def _format(self, formatter):
        """Put together the arguments in a suitable format, using formatter to produce the arguments' output."""
        # Special notation for infix operators
        if isinstance(self.functor, FunctionApplication):
            # Check whether this is one of the special infix operators
            operator = self.functor.functor
            if isinstance(operator, Literal) and operator.name in self.INFIX_OPERATORS:
                # Output the whole thing as a single binary infix operation
                arg1 = self.functor.argument
                arg2 = self.argument
                operator_name,brackets = self.INFIX_OPERATORS[operator.name]
                if brackets:
                    return "(%s%s%s)" % (formatter(arg1), operator_name, formatter(arg2))
                else:
                    return "%s%s%s" % (formatter(arg1), operator_name, formatter(arg2))
        # Not infix: just a normal function app
        return "(%s %s)" % (formatter(self.functor), formatter(self.argument))
    
    def __str__(self):
        output = self._format(str)
        return output
    
    def to_latex(self):
        return self._format(lambda x: x.to_latex())
    
    def get_children(self):
        return [self.functor, self.argument]

class Terminal(LogicalForm):
    """
    Base class for any logical forms that are atomic: have no children.
    This overrides abstract classes that will always have the same 
    behaviour for terminals.
    
    """
    def alpha_convert(self, source_var, target_var):
        """Alpha-converting a terminal does nothing."""
        return
        
    def beta_reduce(self, *args, **kwargs):
        """Beta-converting a terminal does nothing."""
        return self
    
    def substitute(self, source_variable, target_expression):
        """There are no variables in a terminal, so this does nothing."""
        return
        
    def replace_immediate_constituent(self, old_lf, new_lf):
        """A terminal has no constituents, so this does nothing."""
        return
    
    def get_variables(self):
        """No variables in a terminal."""
        return []
    
    def get_bound_variables(self):
        """No variables in a terminal."""
        return []
        
    def get_children(self):
        """No children of a terminal."""
        return []
    
    def alpha_equivalent(self, other, substitution):
        """
        Checks whether self is equal to a LF that can be derived by 
        some variable substitution S into other, where S contains the 
        substitution T given by "substitution".
        
        Substitution has no effect on a terminal, so they're only 
        alpha-equivalent if they're equal.
        
        """
        return self == other
        
class Literal(Terminal):
    """
    Represents any literal that is used in a semantic
    expression. These are the predicates that are glued 
    together using lambda expressions.
    
    """
    
    def __init__(self, name):
        """Builds a basic logical form object for a literal.
        
        """
        super(Literal, self).__init__()
        self.name = name
            
    def copy(self):
        return type(self)(copy.copy(self.name))
    
    def __eq__(self, lf):
        ## Check this is the same literal
        return type(lf) == type(self) and lf.name == self.name
               
    def __str__(self):
        output = self.name
        return output

    def to_latex(self):
        output = self.name
        return output

class DummyLogicalForm(LogicalForm):
    """
    A logical form that doesn't really represent anything, but 
    implements the full interface of LogicalForm. You shouldn't 
    use this class or even subclass it, as it essentially just bypasses 
    the interface's requirements on subclasses.
    
    It's useful for getting a formalism off the ground before you've 
    got as far as implementing the semantics.
    
    """
    def alpha_convert(self, *args):
        pass
        
    def beta_reduce(self, *args, **kwargs):
        return self
        
    def substitute(self, *args):
        pass
        
    def replace_immediate_constituent(self, old, new):
        pass
        
    def get_variables(self):
        return []
        
    def get_bound_variables(self):
        return []
        
    def get_children(self):
        return []
        
    def alpha_equivalent(self, other, substitution):
        return self == other
        
    def __eq__(self, other):
        return type(self) == type(other)
        
    def copy(self):
        return type(self)()
        
    def __str__(self):
        return "<Dummy>"
        
def multi_apply(application, fun, arg, *args):
    """
    Given a function application class, uses it to produce the curried 
    application of multiple arguments.
    """
    leftapp = application(fun, arg)
    for next_arg in args:
        leftapp = application(leftapp, next_arg)
    return leftapp
    
def multi_abstract(abstraction, arg0, arg1, *args):
    """
    Given a lambda abstraction class, uses it to produce the nested 
    abstraction over any number of variables.
    """
    # Work backwards through the arguments, using the last one as the 
    #  expression and all others as abstracted variables
    all_args = list(reversed([arg0, arg1]+list(args)))
    expr = all_args[0]
    vars = all_args[1:]
    # Abstract over each variable in turn, backwards
    for var in vars:
        expr = abstraction(var, expr)
    return expr

##########################################
###   Utility functions                ###
##########################################

def distinguish_variables(sem1, sem2, semantics=True):
    """
    Utility method. Given two instances of Semantics, check to 
    make sure they have no common variable names and renames them
    if there are any.
    Modifies the object in situ.
    The semantics flag indicates that the arguments are within 
    a Semantics object.
    
    """
    if semantics:
        sem1 = sem1.lf
        sem2 = sem2.lf
    vars1 = set(sem1.get_variables())
    vars2 = set(sem2.get_variables())
    all_vars = vars1 | vars2
    intersection = vars1 & vars2
    # Replace each variable that appears in both
    for var in intersection:
        # Find a variable name not used in the second lf or the first
        new_var = next_unused_variable(var, list(all_vars))
        # Use alpha-conversion to rename the variable
        sem1.alpha_convert(var.copy(),new_var)
        all_vars.add(new_var)
                
def next_unused_variable(start_var, var_list):
    """
    Returns an altered version of the start_var to represent 
    a new variable such that it is not equal to the original 
    value and is not in the var_list
    
    """
    new_var = start_var.copy()
    new_var.index = 0
    # Check whether this variable name is used already
    while new_var in var_list:
        # Try incrementing the index if it is
        new_var.index += 1
    return new_var

