"""
Building derivation trees from annotated chord sequences.

Trees are minimally represented in the database. Each chord may define 
certain pieces of additional tree information which influence the 
way its tree structure is built.

A default tree structure is defined by a left-to-right parsing algorithm,
which applies rules as it may in a particular order. The algorithm does 
not parse properly, but uses only the slash direction information to 
decide what rule to apply.
Essentially this results in trees in which slash categories are always 
composed as soon as possible and then applied. Consecutive atomic 
categories must unambiguously be combined by continuation.
Coordination will never be used by the default trees. A minimal amount 
of information (the end of each coordinated constituent) can be 
specified on the chords to prompt the tree to use coordination. The 
first constituent is always as long as possible (which is a reasonable 
arbitrary canonical tree).

Note that this should not operate directly on sequences read from the 
database, but on their mirrors (see jazzparser.data.db_mirrors), since
this allows it potentially to be used independently of the database.

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

import jazzparser.settings as jazzsettings
from jazzparser.grammar import get_grammar
from jazzparser.utils.strings import strs

class GeneralizedCategory(object):
    """
    Partially represents a CCG category in a simple way. This only 
    contains the information that's important to inferring the tree 
    structure. It's a heavily abstracted form of CCG.
    
    """
    tree = None
    
    def is_complex(self):
        return isinstance(self, SlashCategory)
    complex = property(is_complex)
    
    def __repr__(self):
        return str(self)
    
class SlashCategory(GeneralizedCategory):
    def __init__(self, result, forward, argument):
        self.result = result
        self.forward = forward
        self.argument = argument
    
    def __str__(self):
        return "%s%s%s" % (self.result, self.forward and "/" or "\\", self.argument)
        
    def copy(self):
        return SlashCategory(
            self.result.copy(),
            self.forward,
            self.argument.copy())
            
    def __eq__(self, other):
        return type(self) == type(other) and \
            self.result == other.result and \
            self.argument == other.argument and \
            self.forward == other.forward
        
class AtomicCategory(GeneralizedCategory):
    def __init__(self):
        pass
        
    def __str__(self):
        return "X"
        
    def copy(self):
        return AtomicCategory()
        
    def __eq__(self, other):
        return type(self) == type(other)
        
class UnknownCategory(GeneralizedCategory):
    """
    The categories of some chords are unknown and not specified in the 
    annotation. We still need to parse the rest of the sequence, so 
    we just leave this in the tree as a marker of the unknown category.
    
    """
    def __str__(self):
        return "?"
        
    def copy(self):
        return UnknownCategory()
        
    def __eq__(self, other):
        # Can't be equal if we don't know what we are!
        return False
        
class StackMarker(object):
    """
    Special type to place markers among the categories in the stack.
    
    """
    pass
    
class CoordinationMiddleMarker(StackMarker):
    """
    Marks the end of the first part of a coordination.
    
    """
    def __str__(self):
        return "&"
    __repr__ = __str__


class SyntacticTreeNode(object):
    """
    Superclass of nodes in syntactic trees. These classes are used to 
    represent the trees that we build using basic category information 
    with minimal manually-specified structural ambiguity resolution.
    
    """
    pass
    
class SyntacticNonTerminal(SyntacticTreeNode):
    """
    An internal node in a syntactic tree.
    
    """
    def __init__(self, children, rule):
        self.children = children
        self.rule = rule
        
    def __str__(self):
        return "(%s)%s" % (" ".join(["%s" % c for c in self.children]),self.rule)
        
    def _get_span_length(self):
        return sum([c.span_length for c in self.children])
    span_length = property(_get_span_length)
        
class SyntacticTerminal(SyntacticTreeNode):
    """
    A terminal node (leaf) in a syntactic tree.
    
    """
    def __init__(self, chord, category=None):
        self.chord = chord
        self.category = category
        
    def __str__(self):
        return str(self.chord)
        
    span_length = 1
        
class SyntacticTreeRoot(object):
    """
    The root of a syntactic tree. Note that this may be a parent node 
    of multiple tree unrelated by rule applications, if the derivation 
    did not build a single tree.
    
    """
    def __init__(self, children, shift_reduce=None):
        self.children = children
        self.shift_reduce = shift_reduce
        
    def __str__(self):
        return "Trees:%s" % " | ".join([str(tree) for tree in self.children])


################### Grammatical rules for generalized categories ##########
"""
These are a very simple form of the grammatical rules we use in the 
Music Keyspan formalism. They just do category structure checks.

"""
def attach_tree(cat, inputs, rule):
    """
    Attach a non-terminal tree to a category on the basis of the inputs 
    from which it was built.
    """
    cat.tree = SyntacticNonTerminal([c.tree for c in inputs], rule)

def _comp(dir, stack):
    """ Generic composition (use compf or compb). """
    if len(stack) < 2:
        return False
    if not isinstance(stack[-1], GeneralizedCategory) or \
      not isinstance(stack[-2], GeneralizedCategory):
        return False
    if not isinstance(stack[-2], SlashCategory) or \
      not isinstance(stack[-1], SlashCategory) or \
      not stack[-2].forward == dir or not stack[-1].forward == dir:
        return False
    else:
        cat1 = stack.pop()
        cat0 = stack.pop()
        stack.append(SlashCategory(cat0.result.copy(), dir, cat1.argument.copy()))
        attach_tree(stack[-1], [cat0, cat1], dir and "compf" or "compb")
        return True
        
def compf(stack):
    """ Forward composition """
    return _comp(True, stack)
compf.name = "compf"
        
def compb(stack):
    """ Backward composition """
    return _comp(False, stack)
compb.name = "compb"
    
def appf(stack):
    """ Forward application """
    if len(stack) < 2:
        return False
    if not isinstance(stack[-1], GeneralizedCategory) or \
      not isinstance(stack[-2], GeneralizedCategory):
        return False
    if not isinstance(stack[-2], SlashCategory) or \
      not stack[-2].forward or \
      not stack[-2].argument == stack[-1]:
        return False
    else:
        cat1 = stack.pop()
        cat0 = stack.pop()
        stack.append(cat0.result.copy())
        attach_tree(stack[-1], [cat0, cat1], "appf")
        return True
appf.name = "appf"

def appb(stack):
    """ Backward application """
    if len(stack) < 2:
        return False
    if not isinstance(stack[-1], GeneralizedCategory) or \
      not isinstance(stack[-2], GeneralizedCategory):
        return False
    if not isinstance(stack[-1], SlashCategory) or \
      stack[-1].forward or \
      not stack[-1].argument == stack[-2]:
        return False
    else:
        cat1 = stack.pop()
        cat0 = stack.pop()
        stack.append(cat1.result.copy())
        attach_tree(stack[-1], [cat0, cat1], "appb")
        return True
appb.name = "appb"
        
def cont(stack):
    """ Tonic continuation """
    if len(stack) < 2:
        return False
    if not isinstance(stack[-1], GeneralizedCategory) or \
      not isinstance(stack[-2], GeneralizedCategory):
        return False
    if not isinstance(stack[-2], AtomicCategory) or \
      not isinstance(stack[-1], AtomicCategory):
        return False
    else:
        cat1 = stack.pop()
        cat0 = stack.pop()
        stack.append(AtomicCategory())
        attach_tree(stack[-1], [cat0, cat1], "cont")
        return True
cont.name = "cont"
        
def coord(stack):
    """ Cadence coordination """
    # stack should look like this: [... cadence, marker, cadence]
    if len(stack) < 3:
        return False
    if not isinstance(stack[-1], GeneralizedCategory) or \
      not isinstance(stack[-3], GeneralizedCategory) or \
      not isinstance(stack[-2], CoordinationMiddleMarker):
        return False
    if not isinstance(stack[-3], SlashCategory) or \
      not isinstance(stack[-1], SlashCategory) or \
      not stack[-3].forward or not stack[-1].forward:
        return False
    else:
        cat1 = stack.pop()
        marker = stack.pop()
        cat0 = stack.pop()
        stack.append(cat0.copy())
        attach_tree(stack[-1], [cat0, cat1], "coord")
        return True
coord.name = "coord"



def generalize_category(category, formalism):
    """
    Builds a simple GeneralizedCategory from a real grammatical category 
    as represented in the parser (see the Music Keyspan formalism).
    
    """
    if isinstance(category, GeneralizedCategory):
        return category
    # Allow the formalism to specify its own way of handling as much 
    #  as it likes
    if hasattr(formalism.Syntax, "pre_generalize_category"):
        gencat = formalism.Syntax.pre_generalize_category(category)
        # It can return None to pass it back to the standard 
        #  generalization below
        if gencat is not None:
            return gencat
    
    # Put an unknown category marker in the stack where the category isn't given
    if category is None:
        return UnknownCategory()
    if formalism.Syntax.is_atomic_category(category):
        return AtomicCategory()
    else:
        result = generalize_category(category.result, formalism)
        argument = generalize_category(category.argument, formalism)
        return SlashCategory(result, category.slash.forward, argument)


def build_tree_for_sequence(sequence, debug_stack=False, grammar=None, logger=None):
    """
    Run through the motions of parsing the sequence in order to build 
    its tree structure. Most of the structure is implicit in the 
    lexical categories. Additional information is given in the TreeInfo
    model, associated with chords.
    
    """
    # Read in the possible categories from the grammar
    if grammar is None:
        grammar = get_grammar()
    # This function will format a string and output it to a logger if logging
    if logger is None:
        def _log(*args):
            pass
    else:
        def _log(string, *args):
            string = string % args
            logger.info(string)
    
    input = []
    shift_reduce = []
    
    categories = []
    for chord in sequence.iterator():
        # Try getting a family for the specified category
        if chord.category is None or chord.category == "":
            category = None
            cat_name = None
        else:
            if chord.category not in grammar.families:
                raise TreeBuildError, "Could not find the category %s in "\
                    "the lexicon" % chord.category
            # Assume there's only one entry per family, or at least that if 
            #  there are multiple they have the same argument structure.
            category = grammar.families[chord.category][0].entries[0].sign.category
            cat_name = chord.category
        # Put the generalized form of the category into the stack
        gen_cat = generalize_category(category, grammar.formalism)
        # Attached a tree leaf to this chord
        gen_cat.tree = SyntacticTerminal(chord, category=cat_name)
        input.append(gen_cat)
        categories.append("%s <= %s" % (chord,category))
    _log("CATEGORIES %s", categories)
        
    input = list(reversed(input))
    stack = []
    rules = [ compf, compb, appf, appb, cont ]
    # Now do the vague pseudo-parse
    while len(input) > 0:
        # SHIFT
        shift_reduce.append("S")
        stack.append(input.pop())
        if debug_stack:
            print stack
        _log("SHIFT stack = %s, input = %s", stack, input)
        # Use the additional information given to us to override default
        #  rule applications
        coord_unresolved = False
        coord_resolved = False
        if stack[-1].tree.chord.treeinfo.coord_unresolved:
            # This is the end of the first part of a coordination.
            # Continue reducing, but add a special marker afterwards
            coord_unresolved = True
        if stack[-1].tree.chord.treeinfo.coord_resolved:
            # The end of the second part of a coordination.
            # Continue reducing, then apply coordination
            coord_resolved = True
            
        # REDUCE
        # Try combining the top categories on the stack
        changed = True
        while changed:
            changed = False
            # Try each rule and see whether it applies
            for rule in rules:
                res = rule(stack)
                if res:
                    shift_reduce.append("R(%s)" % rule.name)
                    changed = True
                    _log("REDUCE %s, stack = %s", rule.name, stack)
        
        if coord_resolved:
            # Try to reduce the coordination
            coord(stack)
        if coord_unresolved:
            # Add a special marker to the stack so we know where the 
            #  coordination began
            stack.append(CoordinationMiddleMarker())
    for cat in stack:
        if isinstance(cat, CoordinationMiddleMarker):
            raise TreeBuildError, "Coordination middle marker not "\
                "matched by an end marker. Stack: %s" % strs(stack, ", ")
    tree = SyntacticTreeRoot([cat.tree for cat in stack], shift_reduce=shift_reduce)
    return tree

def tree_to_nltk(intree):
    """
    Given a syntactic tree using the SyntacticTreeNode classes, 
    produces an NLTK tree.
    This is useful, for example, to display a tree: tree.draw().
    You need NLTK installed to be able to do this.
    
    """
    from jazzparser.utils.base import load_optional_package
    tree = load_optional_package('nltk.tree', 'NLTK', 'doing NLTK tree operations')
    def _node_to_nltk_tree(node):
        if isinstance(node, SyntacticNonTerminal):
            # Recursive case: build an internal node
            children = []
            for child in node.children:
                children.append(_node_to_nltk_tree(child))
            return tree.Tree("%s" % node.rule, children)
        elif isinstance(node, SyntacticTreeRoot):
            # Recursive case (root): build an internal node
            children = []
            for child in node.children:
                children.append(_node_to_nltk_tree(child))
            return tree.Tree("Root", children)
        elif isinstance(node, SyntacticTerminal):
            # Base case: build a leaf
            leaf = tree.Tree("%s" % node.chord, [])
            if node.category is not None:
                # Add an extra node to represent the category with one child
                leaf = tree.Tree("%s" % node.category, [leaf])
            return leaf
    return _node_to_nltk_tree(intree)

    
class TreeBuildError(Exception):
    pass
