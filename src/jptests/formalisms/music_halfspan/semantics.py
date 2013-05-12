"""Unit tests for jazzparser.formalisms.music_halfspan.semantics.

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

from jazzparser.formalisms.music_halfspan.semantics import Semantics, \
            EnharmonicCoordinate, List, semantics_from_string, ListCat, \
            Variable, FunctionApplication, Leftonto, Rightonto, \
            LambdaAbstraction, Coordination, apply, compose, \
            list_lf_to_coordinates

class TestStringBuilder(unittest.TestCase):
    """
    Tests for building LFs using C{semantics_from_string}.
    
    """
    def test_coordinate(self):
        sem = semantics_from_string("<3,4>")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, EnharmonicCoordinate)
        # Check the coordinate was correctly interpreted
        self.assertEqual(sem.lf.harmonic_coord, (3,4))
        
    def test_list(self):
        sem = semantics_from_string("[<1,2>]")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, List)
        # Check the list was correctly interpreted
        self.assertEqual(len(sem.lf), 1)
        # And the coordinate in it
        self.assertIsInstance(sem.lf[0], EnharmonicCoordinate)
        self.assertEqual((sem.lf[0].x,sem.lf[0].y), (1,2))
        
        # Multi-element list
        sem = semantics_from_string("[<1,2>,<3,4>]")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, List)

    def test_cat(self):
        sem = semantics_from_string("[<1,2>]+[<3,4>]")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, ListCat)
        # Check the cat was correctly interpreted
        self.assertEqual(len(sem.lf), 2)
        
    def test_variable(self):
        sem = semantics_from_string("$var13")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, Variable)
        # Check the variable was correctly interpreted
        self.assertEqual(sem.lf.name, "var")
        self.assertEqual(sem.lf.index, 13)
        
        # Try one without a number
        sem = semantics_from_string("$var")
        # Check the variable was correctly interpreted
        self.assertEqual(sem.lf.name, "var")
        self.assertEqual(sem.lf.index, 0)
        
        # And a single-character
        sem = semantics_from_string("$X")
        # Check the variable was correctly interpreted
        self.assertEqual(sem.lf.name, "X")
        self.assertEqual(sem.lf.index, 0)
        
    def test_predicates(self):
        sem = semantics_from_string("leftonto($X)")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, FunctionApplication)
        self.assertIsInstance(sem.lf.functor, Leftonto)
        
        sem = semantics_from_string("rightonto($X)")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, FunctionApplication)
        self.assertIsInstance(sem.lf.functor, Rightonto)

    def test_lambda_abstraction(self):
        sem = semantics_from_string("\\$X.$X")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, LambdaAbstraction)
        # Check the variable was correctly interpreted
        self.assertIsInstance(sem.lf.variable, Variable)
        # Check the expression was correctly interpreted
        self.assertIsInstance(sem.lf.expression, Variable)
        
        # Something different
        sem = semantics_from_string("\\$X.<1,2>")
        self.assertIsInstance(sem.lf.expression, EnharmonicCoordinate)
        
        # Try a multi-variable abstraction
        sem = semantics_from_string("\\$X,$Y.$X")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, LambdaAbstraction)
        # Check the first variable was correctly interpreted
        self.assertIsInstance(sem.lf.variable, Variable)
        # Check the second abstraction is right too
        self.assertIsInstance(sem.lf.expression, LambdaAbstraction)
        self.assertIsInstance(sem.lf.expression.variable, Variable)
        
    def test_function_application(self):
        sem = semantics_from_string("($X $X)")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, FunctionApplication)
        # Check the variable was correctly interpreted
        self.assertIsInstance(sem.lf.functor, Variable)
        # Check the expression was correctly interpreted
        self.assertIsInstance(sem.lf.argument, Variable)
        
        sem = semantics_from_string("($X <1,2>)")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, FunctionApplication)
        # Check the variable was correctly interpreted
        self.assertIsInstance(sem.lf.functor, Variable)
        # Check the expression was correctly interpreted
        self.assertIsInstance(sem.lf.argument, EnharmonicCoordinate)
        
        sem = semantics_from_string("(($X <1,2>) <3,4>)")
        # Check this returned the right type
        self.assertIsInstance(sem.lf, FunctionApplication)
        # Check the variable was correctly interpreted
        self.assertIsInstance(sem.lf.functor, FunctionApplication)
        # Check the expression was correctly interpreted
        self.assertIsInstance(sem.lf.argument, EnharmonicCoordinate)
        
    def test_coordination(self):
        # Create a simple coordination
        sem = semantics_from_string(r"(\$x.leftonto($x)) & (\$x.leftonto($x))")
        self.assertIsInstance(sem.lf, Coordination)
        self.assertEqual(len(sem.lf), 2)
        
        # Creat a three-way coordination (in fact it will be nested)
        sem = semantics_from_string(r"(\$x.leftonto($x)) & (\$x.rightonto($x)) & (\$x.leftonto($x))")
        self.assertIsInstance(sem.lf, Coordination)
        # This is actually length 2, because it's nested
        # It would beta-reduce to length 3
        self.assertEqual(len(sem.lf), 2)
        self.assertIsInstance(sem.lf[1], Coordination)
        self.assertEqual(len(sem.lf[1]), 2)
    
    def test_general(self):
        # Try doing some mixtures of things
        # Just make sure the parsing of these doesn't generate any errors
        sem0 = semantics_from_string("[<1,2>,<3,4>]+[<1,2>]")
        sem1 = semantics_from_string("\\$x. ($x <1,2>)")
        sem2 = semantics_from_string("\\$x. leftonto($x)")
        sem3 = semantics_from_string("\\$x. leftonto(($x <1,2>))")
        sem4 = semantics_from_string("[\\$x. leftonto(($x [<1,2>]))]")
    
    def test_now(self):
        # Build a now predicate and check there are no errors
        sem0 = semantics_from_string(r"now@1($x)")
        sem0.beta_reduce()
        
        sem1 = semantics_from_string(r"\$x.now@1(leftonto($x))")
        sem1.beta_reduce()
        
        sem2 = semantics_from_string(r"now@10((\$x.leftonto($x)) & (\$x.leftonto(leftonto($x))))")
        sem2.beta_reduce()

class TestPredicates(unittest.TestCase):
    """
    Tests for creating and reducing the predicates.
    
    """
    def test_leftonto(self):
        # Check the leftonto gets carried to the first item of the list
        sem = semantics_from_string("leftonto([<1,2>])")
        sem.beta_reduce()
        self.assertIsInstance(sem.lf, List)
        self.assertIsInstance(sem.lf[0], FunctionApplication)
        self.assertIsInstance(sem.lf[0].functor, Leftonto)
        
        # Check the same thing with a multi-element list
        sem = semantics_from_string("leftonto([<1,2>,<3,4>])")
        sem.beta_reduce()
        self.assertIsInstance(sem.lf, List)
        self.assertIsInstance(sem.lf[0], FunctionApplication)
        self.assertIsInstance(sem.lf[0].functor, Leftonto)
        
        # Now with multiple predicates
        sem = semantics_from_string("leftonto(leftonto([<1,2>]))")
        sem.beta_reduce()
        self.assertIsInstance(sem.lf, List)
        self.assertIsInstance(sem.lf[0], FunctionApplication)
        self.assertIsInstance(sem.lf[0].functor, Leftonto)
        self.assertIsInstance(sem.lf[0].argument, FunctionApplication)
        self.assertIsInstance(sem.lf[0].argument.functor, Leftonto)
        
        # Check rightonto works as well
        sem = semantics_from_string("rightonto([<1,2>,<3,4>])")
        sem.beta_reduce()
        self.assertIsInstance(sem.lf, List)
        self.assertIsInstance(sem.lf[0], FunctionApplication)
        self.assertIsInstance(sem.lf[0].functor, Rightonto)
    
    def test_function_application(self):
        # Check that \x.x works as it should: this should reduce to just a coord
        sem0 = semantics_from_string(r"(\$x.$x <1,2>)")
        sem0.beta_reduce()
        sem1 = semantics_from_string("<1,2>")
        self.assertEqual(sem0, sem1)
        
        # Try a trivial abstraction that throws away its argument
        sem0 = semantics_from_string(r"(\$x.<1,2> $y)")
        sem0.beta_reduce()
        sem1 = semantics_from_string("<1,2>")
        self.assertEqual(sem0, sem1)
        
        # Try a multiple abstraction applied to all its args
        sem0 = semantics_from_string(r"((\$x,$y.$x <1,2>) <3,4>)")
        sem0.beta_reduce()
        sem1 = semantics_from_string("<1,2>")
        self.assertEqual(sem0, sem1)

class TestCoordination(unittest.TestCase):
    """
    Tests for use of semantic coordination.
    
    """
    def test_flatten(self):
        """
        Check the flattening of coordinations during beta-reduction is working
        
        """
        # A 3-way coordination
        sem0 = semantics_from_string(r"(\$x.leftonto($x)) & (\$x.rightonto($x)) & (\$x.leftonto($x))")
        # We've already checked that this comes out nested as expected
        # Now check it flattens during beta-reduction
        sem0.beta_reduce()
        self.assertIsInstance(sem0.lf, Coordination)
        self.assertEqual(len(sem0.lf), 3)
        
        # Try the exact same thing, but with brackets to make it combine the 
        #  other way initially
        sem1 = semantics_from_string(r"((\$x.leftonto($x)) & (\$x.rightonto($x))) & (\$x.leftonto($x))")
        sem1.beta_reduce()
        self.assertIsInstance(sem1.lf, Coordination)
        self.assertEqual(len(sem1.lf), 3)
        # This should produce the same thing as before
        self.assertEqual(sem0, sem1)
        
        # This doesn't make sense, but Coordination shouldn't complain
        sem0 = semantics_from_string(r"<1,2> & ((\$x.rightonto($x)) & (\$x.leftonto($x))) & <3,4> & <5,6>")
        sem1 = semantics_from_string(r"<1,2> & (\$x.rightonto($x)) & (\$x.leftonto($x)) & <3,4> & <5,6>")
        sem0.beta_reduce()
        sem1.beta_reduce()
        self.assertEqual(sem0, sem1)

class TestSemantics(unittest.TestCase):
    """
    General tests for the semantics module.
    
    """
    def test_paper_example(self):
        """
        Generates the example that we used in the paper (from Alice in 
        Wonderland) as if it's coming from the combinators. Checks that 
        the right overall LF comes out.
        
        This is pretty insane, but a great test that the semantics is 
        behaving correctly in the contexts in which we'll be using it.
        
        """
        sem = semantics_from_string
        
        # Lexical
        sem_0_1 = sem(r"[<0,0>]")
        sem_1_2 = sem(r"\$x.$x")
        # Bapply
        sem_0_2 = apply(sem_1_2, sem_0_1)
        self.assertTrue(sem_0_2.alpha_equivalent(sem(r"[<0,0>]")))
        
        # Lexical
        sem_2_3 = sem(r"\$x.leftonto($x)")
        sem_3_4 = sem(r"\$x.leftonto($x)")
        # Fcomp
        sem_2_4 = compose(sem_2_3, sem_3_4)
        self.assertTrue(sem_2_4.alpha_equivalent(
                sem(r"\$x.leftonto(leftonto($x))")))
        
        # Lexical
        sem_4_5 = sem(r"\$x.leftonto($x)")
        # Fcomp
        sem_2_5 = compose(sem_2_4, sem_4_5)
        self.assertTrue(sem_2_5.alpha_equivalent(
                sem(r"\$x.leftonto(leftonto(leftonto($x)))")))
        
        # Lexical
        sem_5_6 = sem(r"\$x.leftonto($x)")
        # Fcomp
        sem_2_6 = compose(sem_2_5, sem_5_6)
        self.assertTrue(sem_2_6.alpha_equivalent(
                sem(r"\$x.leftonto(leftonto(leftonto(leftonto($x))))")))

        # Lexical
        sem_6_7 = sem(r"\$x.leftonto($x)")
        # Fcomp
        sem_2_7 = compose(sem_2_6, sem_6_7)
        self.assertTrue(sem_2_7.alpha_equivalent(
                sem(r"\$x.leftonto(leftonto(leftonto(leftonto(leftonto($x)))))")))

        # Lexical
        sem_7_8 = sem(r"\$x.leftonto($x)")
        sem_8_9 = sem(r"\$x.$x")
        # Fcomp
        sem_7_9 = compose(sem_7_8, sem_8_9)
        self.assertTrue(sem_7_9.alpha_equivalent(
                sem(r"\$x.leftonto($x)")))
        
        # Lexical
        sem_9_10 = sem(r"\$x.leftonto($x)")
        # Fcomp
        sem_7_10 = compose(sem_7_9, sem_9_10)
        self.assertTrue(sem_7_10.alpha_equivalent(
                sem(r"\$x.leftonto(leftonto($x))")))
        
        # Coord
        sem_2_10 = Semantics(Coordination([sem_2_7.lf, sem_7_10.lf]))
        sem_2_10.beta_reduce()
        semtest = sem(r"(\$x.leftonto(leftonto(leftonto(leftonto(leftonto($x)))))) "\
                        "& (\$x.leftonto(leftonto($x)))")
        semtest.beta_reduce()
        self.assertTrue(sem_2_10.alpha_equivalent(semtest))
        
        # Lexical
        sem_10_11 = sem(r"\$x.leftonto($x)")
        # Fcomp
        sem_2_11 = compose(sem_2_10, sem_10_11)
        semtest = sem(r"\$y.("\
                        "((\$x.leftonto(leftonto(leftonto(leftonto(leftonto($x)))))) "\
                         "& (\$x.leftonto(leftonto($x)))) leftonto($y))")
        semtest.beta_reduce()
        self.assertTrue(sem_2_11.alpha_equivalent(semtest))
        
        # Skip a couple of lexical LFs
        sem_11_13 = sem(r"\$x.leftonto(leftonto($x))")
        # Coord
        sem_2_13 = Semantics(Coordination([sem_2_11.lf, sem_11_13.lf]))
        sem_2_13.beta_reduce()
        semtest = sem(r"(\$y.("\
                        "((\$x.leftonto(leftonto(leftonto(leftonto(leftonto($x)))))) "\
                         "& (\$x.leftonto(leftonto($x)))) leftonto($y))) "\
                        "& (\$x.leftonto(leftonto($x)))")
        semtest.beta_reduce()
        self.assertTrue(sem_2_13.alpha_equivalent(semtest))
        
        # Lexical
        sem_13_14 = sem(r"[<0,0>]")
        # Fapply
        sem_2_14 = apply(sem_2_13, sem_13_14)
        semtest = sem(r"((\$y.("\
                        "((\$x.leftonto(leftonto(leftonto(leftonto(leftonto($x)))))) "\
                         "& (\$x.leftonto(leftonto($x)))) leftonto($y))) "\
                        "& (\$x.leftonto(leftonto($x))) [<0,0>])")
        semtest.beta_reduce()
        self.assertTrue(sem_2_14.alpha_equivalent(semtest))
        
        # Finally, development
        sem_0_14 = Semantics(ListCat([sem_0_2.lf, sem_2_14.lf]))
        sem_0_14.beta_reduce()
        semtest = sem(r"[<0,0>, "\
                        "((\$y.("\
                        "((\$x.leftonto(leftonto(leftonto(leftonto(leftonto($x)))))) "\
                         "& (\$x.leftonto(leftonto($x)))) leftonto($y))) "\
                        "& (\$x.leftonto(leftonto($x))) <0,0>)]")
        semtest.beta_reduce()
        self.assertTrue(sem_0_14.alpha_equivalent(semtest))

class TestLfToCoordinates(unittest.TestCase):
    """
    Tests for producing a tonal space path from a logical form.
    
    """
    def setUp(self):
        """
        Builds a load of logical forms and gives their expected tonal space 
        paths.
        
        """
        self.longMessage = True
        sem = semantics_from_string
        
        # Some very simple tests on cadences
        self.basic = [
            (sem(r"[leftonto(leftonto(<0,0>))]"),
                [(2,0),(1,0),(0,0)]),
            (sem(r"[leftonto(leftonto(leftonto(<0,0>)))]"),
                [(3,0),(2,0),(1,0),(0,0)]),
            (sem(r"[rightonto(rightonto(<0,0>))]"),
                [(2,2),(3,2),(4,2)]),
            (sem(r"[<0,0>,<0,1>]"),
                [(0,0),(0,1)]),
            (sem(r"[<4,-1>,<4,0>]"),
                [(0,0),(0,1)]),
        ]
        # Some tests of cadences being combined by development
        self.develop = [
            (sem(r"[<0,0>,leftonto(leftonto(<0,0>))]"),
                [(0,0),(2,0),(1,0),(0,0)]),
            (sem(r"[<0,0>,leftonto(leftonto(leftonto(<0,0>)))]"),
                [(0,0),(-1,1),(-2,1),(-3,1),(-4,1)]),
            (sem(r"[<0,0>,leftonto(leftonto(leftonto(<0,0>)))]"),
                [(0,0),(-1,1),(-2,1),(-3,1),(-4,1)]),
            (sem(r"[<-4,-2>,leftonto(leftonto(leftonto(<0,0>)))]"),
                [(0,0),(-1,1),(-2,1),(-3,1),(-4,1)]),
            (sem(r"[<0,0>, leftonto(leftonto(leftonto(<0,0>))), "\
                    "leftonto(leftonto(leftonto(<0,0>)))]"),
                [(0,0),(-1,1),(-2,1),(-3,1),(-4,1),(-5,2),(-6,2),(-7,2),(-8,2)]),
            (sem(r"[<1,2>,leftonto(leftonto(leftonto(<0,0>)))]"),
                [(1, 2), (-1, 1), (-2, 1), (-3, 1), (-4, 1)]),
        ]
        # Some test on coordinated cadences
        self.coordination = [
            (sem(r"[((\$x.leftonto($x)) & (\$x.leftonto($x)) <0,0>)]"),
                [(1,0),(1,0),(0,0)]),
            (sem(r"[((\$x.rightonto($x)) & (\$x.leftonto($x)) <0,0>)]"),
                [(3,2),(5,2),(4,2)]),
            (sem(r"[((\$x.leftonto($x)) & (\$x.leftonto(leftonto(leftonto($x)))) <0,0>)]"),
                [(1,0),(3,0),(2,0),(1,0),(0,0)]),
            (sem(r"[((\$x.leftonto($x)) & (\$x.leftonto(leftonto(leftonto(leftonto($x))))) <0,0>)]"),
                [(1,0),(4,0),(3,0),(2,0),(1,0),(0,0)]),
        ]
        # And some with nesting
        self.nested_coordination = [
            (sem(r"[((\$x.leftonto($x)) & (\$x.leftonto((((\$y.leftonto($y)) & (\$y.leftonto(leftonto($y)))) $x))) <0,0>)]"),
                [(1,0),(2,0),(1,0),(2,0),(1,0),(0,0)]),
            # Call Me Irresponsible
            (sem(r"[<0,0>, (((\$y.(((\$x.leftonto(leftonto(leftonto(leftonto(leftonto($x)))))) & (\$x.leftonto(leftonto($x)))) leftonto($y))) & (\$x.leftonto(leftonto($x)))) <0,0>)]"),
                [(0,0),(-2,-1),(-3,-1),(-4,-1),(-5,-1),(-6,-1),(-5,-1),(-6,-1),(-7,-1),(-6,-1),(-7,-1),(-8,-1)]),
        ]
        
    def assertExpected(self, output, correct, sems):
        self.assertEqual(output, correct, msg="Expected output: %s. Got: %s. LF was %s" \
                % (correct, output, sems))
    
    def test_basic(self):
        for semantics,correct in self.basic:
            output,times = zip(*list_lf_to_coordinates(semantics.lf))
            self.assertExpected(list(output), correct, semantics)
    
    def test_develop(self):
        for semantics,correct in self.develop:
            output,times = zip(*list_lf_to_coordinates(semantics.lf))
            self.assertExpected(list(output), correct, semantics)
        
    def test_coordination(self):
        for semantics,correct in self.coordination:
            output,times = zip(*list_lf_to_coordinates(semantics.lf))
            self.assertExpected(list(output), correct, semantics)
    
    def test_nested_coordination(self):
        for semantics,correct in self.nested_coordination:
            output,times = zip(*list_lf_to_coordinates(semantics.lf))
            self.assertExpected(list(output), correct, semantics)

class TestEnharmonicCoordinate(unittest.TestCase):
    """
    Tests for certain bits of 
    L{jazzparser.formalisms.music_halfspan.semantics.EnharmonicCoordinate}.
    
    """
    def test_nearest(self):
        """
        This is a particularly difficult bit of EnharmonicCoordinate's 
        behaviour to get right, so it's worth testing a good few examples to 
        make sure it's behaving right.
        
        """
        self.longMessage = False
        
        # Define some test pairs and the expected result
        TESTS = [
            # Tuples: base coord, coord to be shifted, expected result
            # Some that shouldn't be shifted
            ((0,0),   (0,0),   (0,0)),
            ((0,0),   (2,0),   (2,0)),
            ((0,0),   (-2,0),  (-2,0)),
            ((0,0),   (1,1),   (1,1)),
            # Some that should
            ((0,0),   (2,2),   (-2,0)),
            ((0,0),   (-2,-2), (2,0)),
        ]
        
        for base,candidate,correct in TESTS:
            # Build enharmonic coords
            base_crd = EnharmonicCoordinate.from_harmonic_coord(base)
            candidate_crd = EnharmonicCoordinate.from_harmonic_coord(candidate)
            # Try running nearest on these
            result_crd = base_crd.nearest(candidate_crd)
            result = result_crd.harmonic_coord
            # Check it came out right
            self.assertEqual(result, correct, msg="nearest instance of %s "\
                "[%s] to %s should have been %s, got %s" % \
                (candidate,
                 candidate_crd.zero_coord,
                 base,
                 correct,
                 result))
        
