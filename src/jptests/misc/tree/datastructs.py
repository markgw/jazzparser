"""Unit tests for jazzparser.misc.tree datastructures.

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

import unittest
from jazzparser.misc.tree.datastructs import Node, MutableTree, \
                    ImmutableTree

class TestNode(unittest.TestCase):
    def test_leaf(self):
        """ Create a leaf node. """
        node = Node("test")
        self.assertEqual(len(node.children), 0)
        
    def test_internal(self):
        """ Create an internal node. """
        leaf1 = Node("l1")
        leaf2 = Node("l2")
        node = Node("int", leaf1, leaf2)
        
        self.assertEqual(node.label, "int")
        self.assertEqual(len(node.children), 2)
        
class TestMutableTree(unittest.TestCase):
    def test_create(self):
        tree = MutableTree(Node("root"))
        self.assertEqual(tree.root.label, "root")
        
    def test_create_tree(self):
        """ Just make sure building a big tree causes no errors. """
        tree = MutableTree(
                    Node("root", 
                        Node("leaf1"),
                        Node("A", 
                            Node("leaf2"),
                            Node("leaf3")
                        ),
                        Node("B",
                            Node("leaf4"),
                            Node("C", 
                                Node("leaf5"),
                                Node("leaf6")
                            )
                        )
                    ))
    
    def test_string(self):
        """
        Tries to get the string representation of a tree. It's not critical 
        that the representation is correct, so we don't worry about that.
        
        """
        tree = MutableTree(
                    Node("root", 
                        Node("leaf1"),
                        Node("A", 
                            Node("leaf2"),
                            Node("leaf3")
                        ),
                        Node("B",
                            Node("leaf4"),
                            Node("C", 
                                Node("leaf5"),
                                Node("leaf6")
                            )
                        )
                    ))
        str(tree)

    def test_postorder(self):
        """ Check postorder returns the right list of nodes. """
        leaf1 = Node("leaf1")
        leaf2 = Node("leaf2")
        leaf4 = Node("leaf4")
        leaf5 = Node("leaf5")
        leaf6 = Node("leaf6")
        
        c_node = Node("C", leaf5, leaf6)
        b_node = Node("B", leaf4)
        a_node = Node("A", leaf2, c_node)
        
        root = Node("root", leaf1, a_node, b_node)
        
        tree = MutableTree(root)
        
        # Define the correct postorder manually
        correct_postorder = [leaf1, leaf2, leaf5, leaf6, c_node, a_node, 
                                leaf4, b_node, root]
        postorder = tree.postorder()
        
        # Check that these match
        self.assertEqual([id(n) for n in correct_postorder], \
                         [id(n) for n in postorder])
        
    def test_immutable(self):
        """
        Try converting a mutable tree to an immutable.
        
        """
        tree = MutableTree(
                    Node("root", 
                        Node("leaf1"),
                        Node("A", 
                            Node("leaf2"),
                            Node("leaf3")
                        ),
                        Node("B",
                            Node("leaf4"),
                            Node("C", 
                                Node("leaf5"),
                                Node("leaf6")
                            )
                        )
                    ))
        im = tree.immutable()
        
    def test_copy(self):
        """ Try copying a tree and check the structure is preserved. """
        tree = MutableTree(
                    Node("root", 
                        Node("leaf1"),
                        Node("A", 
                            Node("leaf2"),
                            Node("C", 
                                Node("leaf5"),
                                Node("leaf6")
                            ),
                        ),
                        Node("B",
                            Node("leaf4")
                        )
                    ))
        # Copy it
        new_tree = tree.copy()
        
        # Check none of the nodes has been preserved
        old_ids = [id(n) for n in tree.postorder()]
        for new_node in new_tree.postorder():
            self.assertNotIn(id(new_node), old_ids)
            
        # Check the two trees evaluate as equal
        self.assertEqual(tree, new_tree)
    
