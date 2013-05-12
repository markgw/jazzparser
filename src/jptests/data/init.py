"""Unit tests for jazzparser.data module

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
from jazzparser.data import Chord, DerivationTrace, Fraction

class TestChord(unittest.TestCase):
    """
    Tests for the various ways of creating instances of Chord.
    
    """
    ALLOWED_NUMERALS = [
        ("C",  0,  "C" ),
        ("Db", 1,  "Db"),
        ("D",  2,  "D" ),
        ("Eb", 3,  "Eb"),
        ("E",  4,  "E" ),
        ("F",  5,  "F" ),
        ("F#", 6,  "Gb"),
        ("G",  7,  "G" ),
        ("G#", 8,  "Ab"),
        ("A",  9,  "A" ),
        ("Bb", 10, "Bb"),
        ("B",  11, "B" ),
    ]
    
    def test_from_numerals(self):
        """
        Try creating chords using all possbile numerals and check the numeral 
        and root get set correctly.
        
        """
        for numeral,root,trg_num in self.ALLOWED_NUMERALS:
            # Try creating a Chord with each numeral
            c = Chord(numeral)
            # Check it has the right numeral
            self.assertEqual(trg_num, c.root_numeral)
            # and the right root number
            self.assertEqual(root, c.root)
            
    def test_set_root(self):
        """
        Try setting the root or numeral after a chord is created and check 
        that both values get correctly set.
        
        """
        c = Chord(self.ALLOWED_NUMERALS[0][0])
        for numeral,root,trg_num in self.ALLOWED_NUMERALS:
            # Try setting the root and check root and numeral are correct
            c.root = root
            self.assertEqual(root, c.root)
            self.assertEqual(trg_num, c.root_numeral)
        for numeral,root,trg_num in self.ALLOWED_NUMERALS:
            # Try setting the numeral and check root and numeral are correct
            c.root_numeral = numeral
            self.assertEqual(root, c.root)
            self.assertEqual(trg_num, c.root_numeral)
    
    def test_init_type(self):
        """
        Try creating chords with a particular type and check (a) that they 
        successfully create a chord and (b) that the chord has the right type.
        
        """
        for ctype in Chord.TYPE_SYMBOLS.values():
            c = Chord("C", type=ctype)
            self.assertEqual(c.type, ctype)
            
    def test_interval(self):
        """
        Try getting the interval between two chords and check it comes out 
        as expected.
        
        """
        # Some randomly chosen tests
        tests = [
            (0, "C", "C", True),
            (2, "F", "G", False),
            (4, "D", "F#", False),
            (6, "B", "F", True),
            (8, "F", "Db", False),
            (10, "Ab", "F#", False)
        ]
        for interval,lower,upper,invertible in tests:
            c0 = Chord(lower)
            c1 = Chord(upper)
            self.assertEqual(interval, Chord.interval(c0,c1))
            # Try inverting the interval and check it's only the same in the 
            #  cases where the interval is its own inverse
            if invertible:
                self.assertEqual(interval, Chord.interval(c1,c0))
            else:
                self.assertNotEqual(interval, Chord.interval(c1,c0))
    
    def test_from_name(self):
        """
        from_name covers a lot of possible chord instances. Here we just test 
        a sample of textual chords and check the instance gets the right 
        attributes out of the name.
        It's by no means exhaustive!
        
        """
        tests = [
            # Name,      root, type,    additions, tetrad type
            ("C",        0,    "",      "",        ""),
            ("F#m7",     6,    "m7",    "",        "m7"),
            ("G7(9)",    7,    "7",     "9",       "7"),
            ("A(9)",     9,    "",      "9",       "7"),
            ("Dsus4",    2,    "sus4",  "",        "sus4"),
            ("Esus4,7",  4,   "sus4,7","",        "sus4,7"),
            ("Esus4(9)", 4,  "sus4",  "9",       "sus4,7"),
            ("Fm,M7(+11)", 5, "m,M7",  "+11",      "m,M7"),
        ]
        for name,root,ctype,additions,tetrad in tests:
            c = Chord.from_name(name)
            self.assertEqual(root, c.root)
            self.assertEqual(ctype, c.type)
            self.assertEqual(additions, c.additions)
            self.assertEqual(tetrad, c.tetrad_type)


class TestDerivationTraceHalfspan(unittest.TestCase):
    """
    A derivation trace is quite a simple data structure. We test that it 
    behaves correctly when used to store a trace of derivations in the 
    halfspan formalism.
    
    This is specific to the L{halfspan 
    formalism<jazzparser.formalisms.music_halfspan>}, the current and 
    only supported formalism at the time 
    of writing. If the formalism is deprecated these tests will need to 
    be rewritten for the new formalism and these tests should be removed.
    
    """
    def setUp(self):
        from jazzparser.formalisms.music_halfspan.rules import ApplicationRule
        from jazzparser.formalisms.music_halfspan.syntax import AtomicCategory, \
                            ComplexCategory, HalfCategory, Sign, Slash
        from jazzparser.formalisms.music_halfspan.semantics import \
                            DummyLogicalForm, Semantics
        from jazzparser.grammar import Grammar
        
        # Use the default grammar
        self.grammar = Grammar()
        
        # Get a rule to instantiate: forward application
        self.rule = self.grammar.rules_by_name['appf']
        # Create some categories we can store as if the rule applied to them
        # Create an atomic category
        self.cat0 = AtomicCategory(
                        HalfCategory("I"),
                        HalfCategory("I") )
        # Create a complex category that could be applied to the atomic one
        self.cat1 = ComplexCategory(
                        HalfCategory("V", function="D"),
                        Slash(True),
                        HalfCategory("I", function=["D","T"]) )
        # An atomic category, as if 0 was applied to 1
        self.cat2 = AtomicCategory(
                        HalfCategory("V", function="D"),
                        HalfCategory("I") )
        
        # A dummy semantics to use for all signs
        dummy_sem = Semantics(DummyLogicalForm())
        
        # Create signs from the categories
        self.sign0 = Sign(self.cat0, dummy_sem.copy())
        self.sign1 = Sign(self.cat1, dummy_sem.copy())
        self.sign2 = Sign(self.cat2, dummy_sem.copy())
    
    def test_create_lexical_trace(self):
        """
        Just creates a derivation trace in the simplest possible way, as if 
        it's a lexical production.
        
        """
        trace = DerivationTrace(self.sign0, word="IM7")
        
    def test_create_rule_trace(self):
        """
        First creates two lexical traces (as tested in 
        L{test_create_lexical_trace}) and then a trace for applying the 
        application rule to them. The rule is not actually applied, we 
        just pretend it was.
        
        """
        trace0 = DerivationTrace(self.sign0, word="IM7")
        trace1 = DerivationTrace(self.sign1, word="V7")
        # Pretend the rule was applied to the above signs
        trace2 = DerivationTrace(self.sign2, rule=self.rule, args=[trace1, trace0])
        
    def test_multiple_source_trace(self):
        """
        Creates two derivation traces like that created in 
        L{test_create_rule_trace} and combines them into a single trace.
        
        """
        trace0 = DerivationTrace(self.sign0, word="IM7")
        trace1 = DerivationTrace(self.sign1, word="V7")
        # Pretend the rule was applied to the above signs
        trace2 = DerivationTrace(self.sign2, rule=self.rule, args=[trace1, trace0])
        # This rule app is actually the same as trace2, but the DT shouldn't 
        #  care about that, as it's not clever enough
        trace2.add_rule(self.rule, [trace1, trace0])
        
    def test_combined_traces(self):
        """
        Does the same thing as L{test_multiple_source_trace}, but does it by 
        creating two DTs and adding the rules from one to the other.
        
        """
        trace0 = DerivationTrace(self.sign0, word="IM7")
        trace1 = DerivationTrace(self.sign1, word="V7")
        # Pretend the rule was applied to the above signs
        trace2 = DerivationTrace(self.sign2, rule=self.rule, args=[trace1, trace0])
        # This is actually the same as trace2
        trace2b = DerivationTrace(self.sign2, rule=self.rule, args=[trace1, trace0])
        trace2.add_rules_from_trace(trace2b)


class TestFraction(unittest.TestCase):
    """
    Tests for L{jazzparser.data.Fraction}.
    
    """
    def test_create_int(self):
        """ Simplest instantiation: int """
        f = Fraction(9)
        self.assertEqual(f, 9)
        
    def test_create_fraction(self):
        """ Simplest instantiation: fraction """
        f = Fraction(9, 10)
        
    def test_simplify(self):
        """
        Basic test of simplification of fractions.
        
        """
        f0 = Fraction(9, 10)
        f1 = Fraction(18, 20)
        self.assertEqual(f0, f1)
        f2 = Fraction(17, 20)
        self.assertNotEqual(f0, f2)
        
    def test_create_string(self):
        """
        Test creating a fraction from a string representation.
        
        """
        f0 = Fraction("1 1/4")
        self.assertEqual(f0, Fraction(5, 4))
        f1 = Fraction("5")
        self.assertEqual(f1, Fraction(5))
        f2 = Fraction("5/4")
        self.assertEqual(f2, Fraction(5, 4))
        for invalid in ["", "1.5", "1/1/1", "5 5", "4\\5", "a", "X"]:
            self.assertRaises(Fraction.ValueError, Fraction, invalid)
        
    def test_reparse_string(self):
        """
        Create some random fractions, get their string representation and check 
        the this can by used to correctly reinstantiate the fraction.
        
        """
        from random import randint
        for i in range(50):
            # Create a random fraction
            f0 = Fraction(randint(0,100), randint(1,100))
            f0_str = str(f0)
            self.assertEqual(f0, Fraction(f0_str))
            
    def test_zero_denominator(self):
        """
        Setting a Fraction's denominator to 0 should raise an error.
        
        """
        self.assertRaises(ZeroDivisionError, Fraction, 5, 0)
        f = Fraction(1)
        self.assertRaises(ZeroDivisionError, lambda x: f / x, 0)
        
    def test_add(self):
        """
        Try adding Fractions together.
        
        """
        f0 = Fraction(5)
        f1 = Fraction(6)
        self.assertEqual(f0+f1, 11)
        f2 = Fraction(7, 12) + f0
        self.assertEqual(f2, Fraction("5 7/12"))
        self.assertEqual(f2, Fraction(67, 12))
    
    def test_neg(self):
        """ Try negating Fractions """
        f0 = Fraction(5, 7)
        self.assertEqual(-f0, Fraction(-5, 7))
        f1 = Fraction("5 4/5")
        self.assertEqual(-f1, Fraction("-5 4/5"))
        
    def test_sub(self):
        """ Test subtraction """
        f0 = Fraction(5)
        f1 = Fraction(6)
        self.assertEqual(f0-f1, -1)
        f2 = Fraction(7, 12) - f0
        self.assertEqual(f2, Fraction("-4 5/12"))
        self.assertEqual(f2, Fraction(-53, 12))
        
    def test_mul(self):
        """ Test multiplication """
        f0 = Fraction(1,2) * Fraction(3)
        self.assertEqual(f0, Fraction(3,2))
        f1 = Fraction(5,7) * Fraction(3,9)
        self.assertEqual(f1, Fraction(15, 63))
        f2 = Fraction(-5,7) * Fraction(3,-9)
        self.assertEqual(f2, f1)
        
    def test_div(self):
        """ Test division """
        f0 = Fraction(1,2) / 3
        self.assertEqual(f0, Fraction(1,6))
        f0 = Fraction(1,2) / Fraction(3)
        self.assertEqual(f0, Fraction(1,6))
        f1 = Fraction(5,7) / Fraction(3,9)
        self.assertEqual(f1, Fraction(45, 21))
        f2 = Fraction(-5,7) / Fraction(3,-9)
        self.assertEqual(f2, f1)
        f3 = Fraction(5, 7) / 0.5
        self.assertEqual(f3, 10.0/7.0)
        
    def test_float(self):
        """ Conversion to float """
        from random import randint
        for i in range(50):
            n = randint(0, 100)
            d = randint(1, 100)
            self.assertEqual(float(Fraction(n,d)), float(n)/float(d))
    
    def test_long(self):
        """ Conversion to long """
        from random import randint
        for i in range(50):
            n = randint(0, 100)
            d = randint(1, 100)
            self.assertEqual(long(Fraction(n,d)), long(n)/long(d))
    
    def test_int(self):
        """ Conversion to int """
        from random import randint
        for i in range(50):
            n = randint(0, 100)
            d = randint(1, 100)
            self.assertEqual(int(Fraction(n,d)), n/d)
            
    def test_equal(self):
        """ Test that equal Fractions evaluate as equal """
        from random import randint
        for i in range(10):
            n = randint(0, 100)
            d = randint(1, 100)
            self.assertEqual(Fraction(n,d), Fraction(n,d))
        self.assertEqual(Fraction(50,4), Fraction("12 1/2"))
        self.assertEqual(Fraction(50,4), Fraction(25,2))
        self.assertEqual(Fraction(7,6), --Fraction(7,6))
        f = Fraction(7, 19)
        self.assertEqual(f, f/Fraction(6, 17)*Fraction(12, 34))


if __name__ == '__main__':
    unittest.main()
