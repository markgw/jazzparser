"""Unit tests for jazzparser.formalisms.music_halfspan.rules.

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

from jazzparser.formalisms.music_halfspan.syntax import sign_from_string
from jazzparser.formalisms.music_halfspan.rules import ApplicationRule
from jazzparser.grammar import get_grammar

class TestApplication(unittest.TestCase):
    """
    Tests for the application rule.
    
    """
    def setUp(self):
        # Load a grammar
        self.grammar = get_grammar()
        self.fapply = self.grammar.rules_by_name['appf']
        self.bapply = self.grammar.rules_by_name['appb']
    
    def test_fapply_success(self):
        # An application that should succeed
        sign0 = sign_from_string(r"V^D / I^DT : \$x.leftonto($x)")
        sign1 = sign_from_string(r"I^T : [<0,0>]")
        results = self.fapply.apply_rule([sign0, sign1])
        # Check this gave the expected result
        correct = sign_from_string(r"V^D - I^T : [leftonto(<0,0>)]")
        self.assertIsNotNone(results, 
            msg="rule application failed: %s on %s and %s" % (self.fapply, sign0, sign1))
        self.assertEqual(results[0], correct)
        
    def test_fapply_failure(self):
        # An application that should fail
        sign0 = sign_from_string(r"V^D \ I^DT : \$x.leftonto($x)")
        sign1 = sign_from_string(r"I^T : [<0,0>]")
        results = self.fapply.apply_rule([sign0, sign1])
        # Check this failed as expected
        self.assertEqual(results, None)

    def test_fapply_success(self):
        # An application that should succeed
        sign0 = sign_from_string(r"III^T : [<0,1>]")
        sign1 = sign_from_string(r"IV^T \ III^T : \$x.$x")
        results = self.bapply.apply_rule([sign0, sign1])
        # Check this gave the expected result
        correct = sign_from_string(r"III^T - IV^T : [<0,1>]")
        self.assertIsNotNone(results, 
            msg="rule application failed: %s on %s and %s" % (self.bapply, sign0, sign1))
        self.assertEqual(results[0], correct)
        
    def test_fapply_failure(self):
        # An application that should fail
        sign0 = sign_from_string(r"V^D / I^DT : \$x.leftonto($x)")
        sign1 = sign_from_string(r"I^T : [<0,0>]")
        results = self.bapply.apply_rule([sign0, sign1])
        # Check this failed as expected
        self.assertEqual(results, None)


class TestComposition(unittest.TestCase):
    """
    Tests for the composition rule.
    
    @todo: Write these tests. I'm bored of writing dull tests right now.
    
    """
    
class TestDevelopment(unittest.TestCase):
    """
    Tests for the development rule.
    
    """
    def setUp(self):
        # Load a grammar
        self.grammar = get_grammar()
        self.devel = self.grammar.rules_by_name['dev']
    
    def test_apply_success(self):
        # An application that should succeed
        sign0 = sign_from_string(r"bVII^D - III^T : [leftonto(<1,2>), <3,4>]")
        sign1 = sign_from_string(r"I^T : [<0,0>]")
        results = self.devel.apply_rule([sign0, sign1])
        # Check this gave the expected result
        correct = sign_from_string(r"bVII^D - I^T : [leftonto(<1,2>), <3,4>, <0,0>]")
        self.assertIsNotNone(results, 
            msg="rule application failed: %s on %s and %s" % (self.devel, sign0, sign1))
        self.assertEqual(results[0], correct)
    
    def test_fapply_failure(self):
        # An application that should fail
        sign0 = sign_from_string(r"V^D / I^DT : \$x.leftonto($x)")
        sign1 = sign_from_string(r"I^T : [<0,0>]")
        results = self.devel.apply_rule([sign0, sign1])
        # Check this failed as expected
        self.assertEqual(results, None)

class TestCoordination(unittest.TestCase):
    """
    Tests for the coordination rule.
    
    """
    def setUp(self):
        # Load a grammar
        self.grammar = get_grammar()
        self.coord = self.grammar.rules_by_name['coord']
    
    def test_apply_success(self):
        # An application that should succeed
        sign0 = sign_from_string(r"bVII^D /{c} III^TD : \$x.leftonto(leftonto($x))")
        sign1 = sign_from_string(r"IV^D /{c} III^T : \$y.leftonto($y)")
        results = self.coord.apply_rule([sign0, sign1])
        # Check this gave the expected result
        correct = sign_from_string(r"bVII^D /{c} III^T : (\$x.leftonto(leftonto($x))) & (\$y.leftonto($y))")
        self.assertIsNotNone(results, 
            msg="rule application failed: %s on %s and %s" % (self.coord, sign0, sign1))
        self.assertEqual(results[0], correct)
    
    def test_fapply_failure(self):
        # An application that should fail
        sign0 = sign_from_string(r"V^D / I^DT : \$x.leftonto($x)")
        sign1 = sign_from_string(r"I^T : [<0,0>]")
        results = self.coord.apply_rule([sign0, sign1])
        # Check this failed as expected
        self.assertEqual(results, None)


