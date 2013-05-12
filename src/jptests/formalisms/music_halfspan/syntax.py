"""Unit tests for jazzparser.formalisms.music_halfspan.syntax.

This doesn't include tests for the behaviour of the syntactic types under 
rule applications or even the interfaces of the categories. At the moment, 
this just tests building categories from string representations. This 
does mean that we can add more tests now that rely on this method of building 
categories.

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

from jazzparser.formalisms.music_halfspan.syntax import syntax_from_string, \
            AtomicCategory, ComplexCategory

class TestStringBuilder(unittest.TestCase):
    """
    Tests for building categories using C{syntax_from_string}.
    
    """
    def test_half_atomic(self):
        cat = syntax_from_string("I^T")
        self.assertIsInstance(cat, AtomicCategory)
        
        cat = syntax_from_string("II^D")
        self.assertIsInstance(cat, AtomicCategory)
        
        cat = syntax_from_string("bV^S")
        self.assertIsInstance(cat, AtomicCategory)
    
    def test_full_atomic(self):
        cat = syntax_from_string("I^T-II^T")
        self.assertIsInstance(cat, AtomicCategory)
        
        cat = syntax_from_string("II^D - V^T")
        self.assertIsInstance(cat, AtomicCategory)
        
        cat = syntax_from_string("VII^S - I^T")
        self.assertIsInstance(cat, AtomicCategory)
        
    def test_complex(self):
        cat = syntax_from_string("V^D / I^T")
        self.assertIsInstance(cat, ComplexCategory)

        cat = syntax_from_string("II^D / I^TD")
        self.assertIsInstance(cat, ComplexCategory)

        cat = syntax_from_string(r"bVI^T \ I^S")
        self.assertIsInstance(cat, ComplexCategory)
    
    def test_complex_modality(self):
        cat = syntax_from_string(r"V^D /{c} I^TD")
        self.assertIsInstance(cat, ComplexCategory)
