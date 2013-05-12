"""Harmonic structure from semantics.

Functions for converting a logical form to trees representing the harmonic 
structure. This is a list of trees of the dependencies in the logical form.

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

from .semantics import Semantics, List, EnharmonicCoordinate, \
            FunctionApplication, Predicate, Coordination, Variable, \
            LambdaAbstraction, Now
from jazzparser.misc.tree import ImmutableTree, Node
from jazzparser.data.dependencies import DependencyGraph

def semantics_to_dependency_trees(sems):
    """
    Converts the given Semantics (logical form) to a tree representation 
    of the dependencies in it.
    
    """
    if not isinstance(sems, Semantics):
        raise SemanticsToTreesError, "input must be a Semantics"
    if not isinstance(sems.lf, List):
        raise SemanticsToTreesError, "top level of semantics must be a List"
    
    trees = []
    # Process each lf in the list individually
    for lf in sems.lf:
        root = lf_to_depedency_tree(lf)
        tree = ImmutableTree(root)
        trees.append(tree)
    
    return trees

def lf_to_depedency_tree(lf, bound_var=None):
    if type(lf) is EnharmonicCoordinate:
        # Base case: a final resolution, root of the tree
        return Node(lf.zero_coord)
    elif type(lf) is FunctionApplication:
        # Recurse to get the tree for the argument first
        arg_tree = lf_to_depedency_tree(lf.argument, bound_var=bound_var)
        
        if isinstance(lf.functor, Predicate):
            if type(lf.functor) is Now:
                # Exclude this from the trees
                return arg_tree
            # Predicate becomes a node label
            leaf = Node(lf.functor.name)
            arg_tree.leftmost_leaf().children.append(leaf)
            return arg_tree
        elif type(lf.functor) is Coordination:
            # Coordination does the interesting stuff
            trees = []
            for cadence in lf.functor:
                # Each cadence should be a function
                if type(cadence) is not LambdaAbstraction:
                    raise SemanticsToTreesError, "invalid cadence: %s" % cadence
                var = cadence.variable
                # Get a tree for the cadence
                # Request that its variable be returned as the root
                tree = lf_to_depedency_tree(cadence.expression, bound_var=var)
                # The root node should be that corresponding to the bound variable
                # We can throw that away and take its subtree
                trees.append(tree[0])
            # Connect these trees up with the argument's tree
            arg_tree.leftmost_leaf().children = trees
            return arg_tree
        else:
            raise SemanticsToTreesError, "unknown functor: %s (%s)" % \
                    (lf.functor, type(lf).__name__)
    elif type(lf) is Variable:
        # Check it's the right variable
        if lf != bound_var:
            raise SemanticsToTreesError, "got unbound variable '%s'. Bound "\
                "variable was '%s'" % (lf, bound_var)
        # Return this as the root of the (sub)tree
        return Node("var")
    else:
        raise SemanticsToTreesError, "unhandled lf type: %s (%s)" % \
                (lf, type(lf).__name__)
                

def semantics_to_dependency_graph(sems):
    """
    Converts the semantics to a L{jazzparser.data.dependencies.DependencyGraph} 
    of the dependencies in it. Returns this graph and a mapping from the 
    indices of the graph to the timings in the semantics.
    
    """
    if not isinstance(sems, Semantics):
        raise SemanticsToDependenciesError, "input must be a Semantics. "\
            "Got: %s" % type(sems).__name__
    if not isinstance(sems.lf, List):
        raise SemanticsToDependenciesError, "top level of semantics must be a "\
            "List. Got '%s'" % type(sems.lf).__name__
    
    all_arcs = []
    next_index = 1
    time_mapping = {}
    # Process each lf in the list individually
    root_arcs = []
    for lf in sems.lf:
        # Get the arcs for this part of the graph
        arcs,node_times,__,root_arc = lf_to_depedency_arcs(lf)
        
        # It's possible to end up with nodes occurring at the same time
        #  from this. These should be merged and arcs between them removed
        time_nodes = {}
        rename = {}
        for node,time in node_times.items():
            if time in time_nodes:
                rename[node] = time_nodes[time]
            else:
                time_nodes[time] = node
        arcs = [(rename.get(source, source), rename.get(target, target), label) \
                for (source,target,label) in arcs]
        # Get rid of the arcs between them
        arcs = [(s,t,l) for (s,t,l) in arcs if s != t]
        for node in rename:
            del node_times[node]
        
        # The nodes are arbitrarily ordered: reorder according to times
        arcs,node_times,root_arc = \
                    _reorder_nodes(arcs, node_times, root_arc, shift=next_index)
        all_arcs.extend(arcs)
        root_arcs.append(root_arc)
        time_mapping.update(node_times)
        
        # Take the last numbered node in this graph so we know where to 
        #  start numbering the next
        next_index += len(node_times)
    
    # Add a root node and make all the tonic arcs point to it
    for (source, label) in root_arcs:
        all_arcs.append((source,0,label))
    
    return DependencyGraph(all_arcs), time_mapping

def _reorder_nodes(arcs, node_times, root_arc, shift=0):
    # Sort by the times and enumerate in that order to key new node indices
    ordering = list(enumerate(sorted(node_times.items(), key=lambda x:x[1])))
    # Shift all the indices on by a fixed amount
    ordering = [(i+shift, old) for (i,old) in ordering]
    # Construct a mapping from the old node labels to the new
    node_map = dict([(old_node,new_node) for (new_node,(old_node,time)) \
                            in ordering])
    new_node_times = dict([(new_node,time) for (new_node,(old_node,time)) \
                            in ordering])
    # Apply the mapping to the node indices in the arcs
    new_arcs = [(node_map[source], node_map[target], label) for \
                            (source,target,label) in arcs]
    # Apply the mapping to the special root arc
    if root_arc is not None:
        root_arc = (node_map[root_arc[0]], root_arc[1])
    return new_arcs,new_node_times,root_arc
    
def lf_to_depedency_arcs(lf, start_index=0, bound_var=None):
    if type(lf) is EnharmonicCoordinate:
        # Base case: a final resolution
        # Add a node to the graph
        # Set the special arc to the root node to go from here
        return [], {start_index: lf.time}, start_index, (start_index, lf)
    elif type(lf) is FunctionApplication:
        # Recurse to get the arcs for the argument
        if type(lf.argument) is Variable:
            # We're applying to a variable
            # Assume it's the one that's been bound, create arcs pointing to 
            #  the node that was associated with it
            if bound_var is None:
                raise SemanticsToDependenciesError, "got unbound variable "\
                    "'%s'" % lf
            arcs = []
            node_times = {}
            arg_start_index = bound_var
            root_arc = None
        else:
            arcs,node_times,arg_start_index,root_arc = \
                    lf_to_depedency_arcs(lf.argument, 
                                         start_index=start_index,
                                         bound_var=bound_var)
        # Take indices greater than those used in the argument
        start_index += len(node_times)
        
        if isinstance(lf.functor, Predicate):
            if type(lf.functor) is Now:
                # Exclude this from the trees
                return arcs,node_times,arg_start_index,root_arc
            # Predicate becomes a label on an arc going to the argument
            # Create a new node (implicitly) and add an arc to the arg
            arcs.append((start_index, arg_start_index, lf.functor.name))
            node_times[start_index] = lf.functor.time
            outer_index = start_index
        elif type(lf.functor) is Coordination:
            # Coordination does the interesting stuff
            for i,cadence in enumerate(lf.functor):
                # Each cadence should be a function
                if type(cadence) is not LambdaAbstraction:
                    raise SemanticsToDependenciesError, "invalid cadence: %s" % cadence
                # Get a tree for the cadence
                # Give the index of the arg's start so the cad can resolve to it
                cad_arcs,cad_times,cad_outer,__ = \
                                lf_to_depedency_arcs(cadence.expression, 
                                                     start_index=start_index,
                                                     bound_var=arg_start_index)
                # Increment the start index by the number of nodes that 
                #  were added by the cadence
                start_index += len(cad_times)
                # Add all the cadence's arcs
                arcs.extend(cad_arcs)
                # Merge in the timings for the cadence's nodes
                node_times.update(cad_times)
                # The node for the outermost element comes from the first cad
                if i == 0:
                    outer_index = cad_outer
        else:
            raise SemanticsToTreesError, "unknown functor: %s (%s)" % \
                    (lf.functor, type(lf).__name__)
        
        return arcs,node_times,outer_index,root_arc
    elif type(lf) is Variable:
        raise SemanticsToDependenciesError, "variable '%s' was found on its "\
            "own. It should have had something applied to it" % lf
    else:
        raise SemanticsToDependenciesError, "unhandled lf type: %s (%s)" % \
                (lf, type(lf).__name__)
                

class SemanticsToTreesError(Exception):
    pass

class SemanticsToDependenciesError(Exception):
    pass
