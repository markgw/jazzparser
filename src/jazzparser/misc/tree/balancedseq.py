"""Representation of trees as balanced sequences.

This representation is used by Lozano and Valiente, 2004 (On the Maximum 
Common Embedded Subtree Problem for Ordered Trees).

We currently only support conversion of I{unlabeled} trees to balanced 
sequences, though Lozano and Valiente do mention how their algorithms could 
be extended to labeled trees.

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

class BalancedSequence(object):
    """
    Elements should be just 0s and 1s.
    
    """
    def __init__(self, sequence):
        self._items = sequence
        
    def __getitem__(self, i):
        if type(i) == slice:
            # Slice of a BalancedSequence should be a BalancedSequence itself
            return BalancedSequence(self._items[i])
        return self._items[i]
        
    def __len__(self):
        return len(self._items)
        
    def __str__(self):
        return "".join(str(i) for i in self)
        
    def __repr__(self):
        return str(self)
        
    def __add__(self, seq):
        return BalancedSequence(self._items + seq._items)
    
    def __eq__(self, other):
        return self._items == other._items
    
    def __hash__(self):
        # Convert to a binary number
        # This doesn't give a unique id to every sequence, since some items 
        #  may constitute zero-padding
        return int("".join(str(i) for i in self), 2)
        
    def check(self):
        """
        Checks that the balanced sequence is in fact balanced. For efficiency, 
        this check is not carried out every time a sequence is created. You 
        should make sure, therefore, to call this whenever you might generate 
        an ill-formed sequence (e.g. when accepting input).
        
        """
        # Check that every 0 is matched by a 1
        if self._items.count(0) != self._items.count(1):
            raise UnbalancedSequenceError, "unmatched brackets in sequence %s" \
                % self
        
    def balance(self, i):
        """ Find the balanced subsequence beginning at i. """
        if self[i] != 0:
            raise ValueError, "balanced subsequence must begin with a 0. "\
                "Cannot get a balanced sequence beginning at %dth item in %s" \
                    % (i, self)
        nesting = 1
        cursor = i
        while nesting > 0:
            cursor += 1
            if self[cursor] == 0:
                nesting += 1
            else:
                nesting -= 1
        return BalancedSequence(self._items[i:cursor+1])
    
    def head(self):
        """ Pull the head out of the sequence """
        if len(self) == 0:
            raise EmptySequenceError, "cannot get the head of an empty sequence"
        first_tree = self.balance(0)
        # Strip the outermost embedding from this
        return first_tree[1:-1]
        
    def head_tail(self):
        """
        Splits the sequence into its head and tail. Since the head has to 
        be computed in order to get the tail, it's best to do these at the 
        same time and throw away the head if you don't need it.
        
        """
        # First get the head
        head = self.head()
        # Everything after the head is the tail
        # The head had its outer level of nesting stripped, so we add 2 back on
        tail = self[len(head)+2:]
        return head,tail
        
    @staticmethod
    def cat(head, tail):
        """
        Produce a balanced sequence that is the result of taking C{head} as 
        the head and C{tail} as the tail. This is equivalent to::
          0<head>1<tail>
        
        """
        return BalancedSequence([0]+head._items+[1]+tail._items)
    
    def decompose(self):
        """
        Returns a set containing the composition of the balanced sequence.
        This is as defined in definition 4 of the paper, I{decomp(s)}.
        
        """
        return set(self._list_decompose())
    
    def _list_decompose(self):
        """
        Instead of doing all our operations on sets, do the recursive 
        computation on lists and then convert to a set.
        
        """
        # First include ourselves
        decomp = [self]
        # Split into head and tail
        head,tail = self.head_tail()
        # Include the decomposition of head, tail and head~tail
        # These include the sequences themselves
        if len(head):
            decomp.extend(head._list_decompose())
        if len(tail):
            decomp.extend(tail._list_decompose())
        if len(head) and len(tail):
            decomp.extend((head+tail)._list_decompose())
        return decomp
    
    @staticmethod
    def from_tree(tree):
        """
        Converts an unlabeled tree representation to its equivalent 
        balanced sequence. If there are labels on the tree, they will just 
        be ignored.
        
        """
        def _from_node(node):
            if len(node.children) == 0:
                # Leaf node: empty sequence
                return []
            else:
                node_seqs = []
                for child in node.children:
                    # Mark the start of the subtree by 0
                    node_seqs.append(0)
                    # Recurse
                    node_seqs.extend(_from_node(child))
                    # Mark the end of the subtree by 1
                    node_seqs.append(1)
                return node_seqs
        
        # Get a sequence of 0s and 1s for the tree
        seq = _from_node(tree.root)
        # Make a balanced sequence from this
        return BalancedSequence(seq)
    
    def to_tree(self):
        """
        Creates an unlabeled tree from the balanced sequence.
        
        """
        from .datastructs import Node, ImmutableTree
        unode = Node.unode
        
        # Make sure we're balanced, or else this won't work
        self.check()
        
        stack = []
        current_node = unode()
        
        # Work through the sequence, spawning nodes as appropriate
        for val in self:
            if val == 0:
                # This means a branch to a subtree
                # Put the current node on the stack, so we can trace back up
                stack.append(current_node)
                # Spawn a new node as a child of the current node
                new_node = unode()
                current_node.children.append(new_node)
                # Carry on down to this node's subtree
                current_node = new_node
            else:
                # End of a subtree
                # Move back up the tree to the node on top of the stack
                current_node = stack.pop()
        
        # If the tree was balanced, the stack should now be empty
        assert len(stack) == 0
        # The current node should be the root now
        return ImmutableTree(current_node)

class EmptySequenceError(Exception):
    pass

class UnbalancedSequenceError(Exception):
    pass
