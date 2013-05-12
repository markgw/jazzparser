"""Unit tests for jazzparser.grammar module

The most important thing here is to make sure that the default grammar 
can be loaded and gets the right set of attributes that we'll need 
to use elsewhere.

It's quite difficult to test some of the functionality thoroughly, so 
I'm not going into a lot of depth on testing other things.

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

import unittest, warnings
from jazzparser.grammar import Grammar, get_grammar, MorphItem
from jptests import prepare_db_input

class TestGrammar(unittest.TestCase):
    SET_ATTRIBUTES = [
        'formalism',
        'grammar_file',
        'families',
        'inactive_families',
        'morphs',
        'morph_items',
        'modality_tree',
        'rules',
        'unary_rules',
        'binary_rules',
        'rules_by_name',
        'lexical_rules',
        'pos_tags',
    ]
    
    def setUp(self):
        """
        Load some chord sequences as db mirrors that we can use as 
        example input.
        
        There's quite a bit in here that could fail, but we can't get 
        round that. We need some data to test with.
        
        """
        inputs = prepare_db_input()
        self.dbinput = inputs[2]
    
    def test_load_default(self):
        """
        Just loads the default grammar to see if there are any errors 
        raised in the process.
        
        """
        # Instantiating Grammar with no args loads the default grammar
        Grammar()
        
    def test_load_cached(self):
        """
        Loads a grammar using L{jazzparser.grammar.get_grammar} and then checks 
        that if we load another we get the same instance.
        
        """
        g1 = get_grammar()
        g2 = get_grammar()
        self.assertIs(g1, g2)
        
    def test_public_attrs(self):
        """
        Checks that the public attributes of Grammar get set when the 
        default grammar is loaded.
        
        """
        g = Grammar()
        for attr in self.SET_ATTRIBUTES:
            self.assertIsNotNone(getattr(g, attr))
    
    def test_get_signs_for_word(self):
        """
        Tries getting a sign from the grammar from an example of 
        chord input.
        
        @see: L{jazzparser.grammar.Grammar.get_signs_for_word}
        
        """
        g = Grammar()
        # Try a few words
        for word in self.dbinput.chords[:10]:
            # This should be a list of signs
            signs = g.get_signs_for_word(word)
        
    def test_get_sign_for_word_by_tag(self):
        """
        @see: L{jazzparser.grammar.Grammar.get_sign_for_word_by_tag}
        
        """
        g = Grammar()
        # Get the list of allowed tags
        tags = g.pos_tags
        # Try a few words
        for chord in self.dbinput.chords[:10]:
            # Try a few tags for each
            for tag in tags[:6]:
                # Should get a sign or None
                sign = g.get_sign_for_word_by_tag(chord, tag)

    def test_tag_to_function(self):
        """
        Try getting a function for every tag and check it's in the 
        set of allowed functions.
        
        """
        g = Grammar()
        for tag in g.pos_tags:
            fun = g.tag_to_function(tag)
            if fun is None:
                warnings.warn("Tag %s has no function given by the "\
                    "grammar" % tag)
            else:
                self.assertIn(fun, ['T','D','S','Pass'])
    
    def test_equivalence_map(self):
        """
        Try reading something out of the equivalence map and check the map 
        works as expected.
        
        We expect the default grammar to have an equivalence map, so test 
        on this basis. It could happen in the future that it has no equivalence 
        map, which is perfectly legal. In this case, this test will need to 
        be updated so that it gets a grammar with a map, or just removed.
        
        """
        g = Grammar()
        if len(g.equiv_map) == 0:
            raise ValueError, "cannot test equivalence map because it's empty "\
                "in the default grammar"
        # Pick a key from the map
        key = g.equiv_map.keys()[0]
        # Get an equivalent morph item and root interval
        equiv = g.equiv_map[key]
        self.assertIsInstance(equiv.root, int)
        self.assertIsInstance(equiv.target, MorphItem)
