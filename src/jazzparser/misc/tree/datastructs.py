"""Data structures for representing generic trees.

These are for applying generic algorithms to.
Note that the trees represented here are ordered trees: their children are 
ordered. They also contain some methods relating to unordered interpretation, 
but take care if you want to implement an algorithm on unordered trees that 
all your operations are unordered.

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

class BaseTree(object):
    """
    Base class for representing trees. Don't instantiate this: use 
    L{ImmutableTree} or L{MutableTree}.
    
    """
    def __init__(self, root):
        self.root = root
    
    def __getitem__(self, index):
        # As a shorthand, let tree[i] point straight to tree.root[i]
        return self.root[index]
    
    def __len__(self):
        """ Number of nodes in total. """
        return len(self.root.all_nodes())
    
    def postorder(self):
        """
        Returns a postorder list of all the nodes in this node's subtree, 
        including itself.
        
        """
        return self.root.postorder()
        
    def postorder_index(self, node):
        """
        Returns the index of this node in the tree according to a postorder 
        ordering. This is inefficient, because it has to recompute the 
        postorder every time. It is more efficient on L{ImmutableTree}, 
        because it can precompute the postorder.
        
        Note that it is looking for a node by identity, not equality.
        
        @raise ValueError: if the node is not found in the graph.
        
        """
        try:
            return [id(n) for n in self.postorder()].index(id(node))
        except ValueError:
            # Give a more informative error
            raise ValueError, "node '%s' (%d) not in tree" % (node, id(node))
    
    def find_parent(self, node):
        """
        Searches for the by of the given node (by identity). Returns the parent, 
        or None if the node is not found.
        
        """
        return self.root.find_parent(node)
        
    def replace_node(self, postorder_index, new_node):
        """
        Removes the node and the given postorder index and replaces it 
        with another node.
        
        """
        # Get the node itself that we're interested in
        node = self.postorder()[postorder_index]
        # Search for it in the tree to find its parent
        parent = self.find_parent(node)
        if parent is None:
            return False
        else:
            i = [id(c) for c in parent.children].index(id(node))
            parent.children.pop(i)
            parent.children.insert(i, new_node)
        
    def __str__(self):
        return "%s" % self.root
        
    def __repr__(self):
        return "%s:%s" % (type(self).__name__, self.root)
    
    def __eq__(self, other):
        return isinstance(other, BaseTree) and self.root == other.root
        
    def unordered_equal(self, other):
        return isinstance(other, BaseTree) and self.root.unordered_equal(other.root)
    
    def copy(self):
        """ Deep copy """
        root = self.root.copy()
        # Create a new tree with this root (using whatever type we were before)
        return type(self)(root)
        
    def can_embed_subtree(self, node):
        return self.root.can_embed_subtree(node)


class Node(object):
    """
    Node of a tree.
    
    """
    def __init__(self, label, *args):
        self.label = label
        self.children = list(args)
        
    @staticmethod
    def unode(*args):
        """ Creates an unlabeled node. Label will be set to C{None}. """
        return Node(None, *args)
        
    def is_leaf(self):
        return len(self.children) == 0
        
    def __len__(self):
        """ Returns number of children """
        return len(self.children)
    
    def all_nodes(self):
        return [self] + sum([child.all_nodes() for child in self.children], [])
    
    def __str__(self):
        string = ""
        # Represent this node
        if self.label is None:
            string += "."
        else:
            string += "%s" % str(self.label)
        
        if len(self.children):
            # Represent the children
            child_strings = []
            for child in self.children:
                child_strings.append(str(child))
            string += "(%s)" % " ".join(child_strings)
        return string
    
    def __repr__(self):
        if self.label is None:
            return "<Node>"
        else:
            return "<Node '%s'>" % str(self.label)
    
    def __getitem__(self, index):
        return self.children[index]
    
    def find_parent(self, node):
        """
        Searches for the by of the given node (by identity). Returns all of 
        the parents of that node we can find.
        
        """
        if id(node) in [id(n) for n in self.children]:
            return self
        else:
            for child in self.children:
                found = child.find_parent(node)
                if found is not None:
                    return found
        return None
    
    def postorder(self):
        """
        Returns a postorder list of all the nodes in this node's subtree, 
        including itself.
        
        """
        descs = []
        # Get nodes from all the children first
        for child in self.children:
            descs.extend(child.postorder())
        descs.append(self)
        return descs
        
    def __eq__(self, other):
        return type(other) == Node and \
                self.label == other.label and \
                len(self.children) == len(other.children) and \
                all(self.children[i] == other.children[i] for i in range(len(self.children)))
    
    def unordered_equal(self, other):
        """
        Our tree representation preserves the order of children of a node. 
        Two trees are only equal according to __eq__ if their child ordering 
        is the same at every node. This method checks if the two can be 
        considered equal if the same ordering is not required.
        
        """
        # We still require all this to hold
        if type(other) != Node or self.label != other.label or \
                len(self.children) != len(other.children):
            return False
        # We need to match every child, but not in the same order
        for child in self.children:
            # Look for a match in the other
            if not any(child.unordered_equal(other_child) for \
                    other_child in other.children):
                # No match found anywhere in the children
                return False
        # All children matched some child of other
        return True
    
    def copy(self):
        children = [child.copy() for child in self.children]
        return Node(self.label, *children)
    
    def leftmost_leaf(self):
        """ Returns the leftmost leaf of this subtree. """
        if self.is_leaf():
            return self
        else:
            return self.children[0].leftmost_leaf()
            
    def rightmost_leaf(self):
        """ Returns the rightmost leaf of this subtree. """
        if self.is_leaf():
            return self
        else:
            return self.children[-1].rightmost_leaf()


class ImmutableTree(BaseTree):
    """
    Tree data structure. This is immutable and assumes that the data structure 
    will never be changed. Don't try to change it, as this will violate 
    key assumptions. Instead, convert to a mutable tree.
    
    Immutability is not enforced at all, just assumed.
    
    The advantage of using this over the mutable tree is that certain things, 
    like postorder numbers, can be precomputed, since we know the graph won't 
    change.
    
    """
    def __init__(self, root):
        # Make sure the whole tree is immutable
        BaseTree.__init__(self, root)
        if not isinstance(root, Node):
            raise TypeError, "ImmutableTree must have a Node as a root: got "\
                "%s" % (type(root).__name__)
        # Precompute the postorder of the nodes
        self._postorder = super(ImmutableTree, self).postorder()
        self._postorder_ids = [id(n) for n in self._postorder]
        # Precompute the descendents of every node
        self._descendents = {}
        for node in self._postorder:
            self._descendents[id(node)] = node.postorder()
    
    def mutable(self):
        """ Get a mutable version of the graph. """
        return MutableTree(self.root.copy())
    
    def immutable(self):
        return self
        
    def postorder(self):
        # No need to recompute this - we've already done it
        return self._postorder
    
    def postorder_index(self, node):
        # Inherit doc
        try:
            return self._postorder_ids.index(id(node))
        except ValueError:
            # Give a more informative error
            raise ValueError, "node '%s' (%d) not in tree" % (node, id(node))
        
    def descendents(self, node):
        """
        ImmutableTree can precompute the descendents of every node, because we 
        know they won't change.
        
        """
        if id(node) not in self._descendents:
            raise ValueError, "node '%s' (%d) not in tree" % (node, id(node))
        else:
            return self._descendents[id(node)]
    
class MutableTree(BaseTree):
    """
    Normal mutable tree data structure. This should be used for most purposes.
    
    """
    def __init__(self, root):
        BaseTree.__init__(self, root)
    
    def immutable(self):
        """ Get an immutable version of the graph. """
        return ImmutableTree(self.root.copy())
        
    def mutable(self):
        return self
