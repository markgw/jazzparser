"""Unit tests for jazzparser.formalisms.music_halfspan.harmstruct.

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

import unittest, os
from jazzparser import settings

from jazzparser.formalisms.music_halfspan.harmstruct import semantics_to_dependency_trees
from jazzparser.formalisms.music_halfspan.semantics import semantics_from_string

class TestTreeBuilder(unittest.TestCase):
    """
    Tests for building trees from semantics using 
    C{semantics_to_dependency_trees}.
    
    """
    def test_coordinate(self):
        # Build a semantics of a single point
        sem = semantics_from_string("[<3,1>]")
        # Build a tree for this
        trees = semantics_to_dependency_trees(sem)
        # Should be only one tree
        self.assertEqual(len(trees), 1)
        # Should just contain the root node corresponding to the point
        self.assertEqual(len(trees[0]), 1)
        
    def test_coordinates(self):
        # Build a semantics of two points
        sem = semantics_from_string("[<3,1>, <2,2>]")
        # Build a tree for this
        trees = semantics_to_dependency_trees(sem)
        # Should be two trees
        self.assertEqual(len(trees), 2)
        # Should just contain the root node each corresponding to the points
        self.assertEqual(len(trees[0]), 1)
        self.assertEqual(len(trees[1]), 1)
        
    def test_predicates(self):
        # Build a semantics of a leftonto/rightonto with resolution
        sem = semantics_from_string("[leftonto(<0,0>)]")
        # Build a tree for this
        trees = semantics_to_dependency_trees(sem)
        # Should have two nodes, leaf should be leftonto
        self.assertEqual(len(trees[0]), 2)
        self.assertEqual(trees[0][0].label, "leftonto")
        
        sem = semantics_from_string("[rightonto(<0,0>)]")
        trees = semantics_to_dependency_trees(sem)
        # Should have two nodes, leaf should be rightonto
        self.assertEqual(len(trees[0]), 2)
        self.assertEqual(trees[0][0].label, "rightonto")
        
        # Try multiple applications
        sem = semantics_from_string("[leftonto(leftonto(leftonto(<0,0>)))]")
        trees = semantics_to_dependency_trees(sem)
        # Should have 4 nodes
        self.assertEqual(len(trees[0]), 4)
    
    def test_coordination(self):
        # Build a semantics of a coordination
        sem = semantics_from_string(r"[((\$x.leftonto($x)) & (\$y.leftonto($y)) leftonto(<0,0>))]")
        trees = semantics_to_dependency_trees(sem)
        # Should look like this:
        # <(0,0)/(0,0)>(leftonto(leftonto leftonto))
        self.assertEqual(len(trees), 1)
        tree = trees[0]
        self.assertEqual(tree.root.label, (0,0))
        self.assertEqual(tree[0].label, "leftonto")
        self.assertEqual(tree[0][0].label, "leftonto")
        self.assertEqual(tree[0][1].label, "leftonto")
    
    def test_call_me_irresponsible(self):
        # Call Me Irresponsible cadence
        sem = semantics_from_string(r"[<0,0>, "\
                    r"(((\$y.(((\$x.leftonto(leftonto(leftonto(leftonto(leftonto($x)))))) "\
                        r"& (\$x.leftonto(leftonto($x)))) leftonto($y))) "\
                        r"& (\$x.leftonto(leftonto($x)))) <0,0>)]")
        trees = semantics_to_dependency_trees(sem)
        self.assertEqual(len(trees), 2)
        # One node in first tree
        self.assertEqual(len(trees[0]), 1)
        # Second tree is the hard one!
        # Should look like this:
        # <(0,0)/(0,0)>
        #   (leftonto(
        #      leftonto(leftonto(leftonto(leftonto(leftonto)))) 
        #      leftonto(leftonto)) 
        #    leftonto(leftonto))
        # Check some things about the structure
        tree = trees[1].root
        # First split (just after root)
        self.assertEqual(len(tree), 2)
        # Other split
        self.assertEqual(len(tree[0]), 2)
        # Others should not split
        self.assertEqual(len(tree[0][0]), 1)
        self.assertEqual(len(tree[0][0][0]), 1)
        self.assertEqual(len(tree[0][0][0][0]), 1)
        self.assertEqual(len(tree[0][0][0][0][0]), 1)
        # This is the lowest leaf
        self.assertTrue(tree[0][0][0][0][0][0].is_leaf())
