"""Unit tests for jazzparser.utils.nltk.ngram.baumwelch

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
from jazzparser.utils.nltk.ngram import DictionaryHmmModel
from jazzparser.utils.nltk.ngram.baumwelch import BaumWelchTrainer
from nltk.probability import DictionaryConditionalProbDist, DictionaryProbDist

class TestTrain(unittest.TestCase):
    def setUp(self):
        """
        Prepare some training data.
        
        """
        self.TRAINING_DATA = [
            [0, 5, 5, 7, 6, 7, 8, 5, 2, 0, 3, 1, 2, 2, 2, 9, 9, 8, 0, 8, 9, 9, 1, 3, 2, 2, 1],
            [3, 3, 1, 2, 1, 1, 0, 1, 9, 7, 8, 7, 7, 9, 0],
            [7, 8, 6, 9, 8, 9, 9, 1, 3, 0, 1, 3, 0, 1, 1, 0, 5, 7, 5, 4, 5, 7, 7]
        ]
        self.TEST_DATA = [0, 1, 2, 3, 4, 3, 5, 6, 7, 8, 8, 9, 7, 7, 0, 0, 1]
        
        ems = list(range(10))
        states = ['H', 'M', 'L']
        # Construct some initial distributions
        # Emission
        hprobs = {
            0:0.0, 1:0.0, 2:0.0, 3:0.0, 4:0.0, 5:0.0, 6:0.1, 7:0.3, 
            8:0.3, 9:0.3 }
        mprobs = {
            0:0.0, 1:0.0, 2:0.0, 3:0.1, 4:0.3, 5:0.3, 6:0.3, 7:0.0, 
            8:0.0, 9:0.0 }
        lprobs = {
            0:0.2, 1:0.2, 2:0.2, 3:0.2, 4:0.2, 5:0.0, 6:0.0, 7:0.0,
            8:0.0, 9:0.0 }
        conddist = {
            'H' : DictionaryProbDist(hprobs),
            'M' : DictionaryProbDist(mprobs),
            'L' : DictionaryProbDist(lprobs),
        }
        emdist = DictionaryConditionalProbDist(conddist)
        # And transition
        conddist = {}
        for first in states+[None]:
            probs = dict([(second, 1.0/3) for second in states+[None]])
            dist = DictionaryProbDist(probs)
            conddist[(first,)] = dist
        transdist = DictionaryConditionalProbDist(conddist)
        
        # Initialize an ngram model with these distributions
        self.model = DictionaryHmmModel(transdist, emdist, states, ems)
    
    def test_init_model(self):
        """
        Check that the initialized model is doing something sensible.
        
        """
        # We don't check these, just that they're not generating errors: 
        #  that would really confuse the rest of it
        self.model.emission_probability(2, 'H')
        self.model.emission_probability(6, 'H')
        self.model.transition_probability('H','L')
        self.model.transition_probability('H','H')
    
    def test_init_decode(self):
        """
        Try running the viterbi decoder using the initial model.
        
        """
        self.model.viterbi_decode(self.TEST_DATA)
        
    def test_baum_welch(self):
        """
        Runs the Baum Welch trainer using the training data.
        
        """
        options = BaumWelchTrainer.process_option_dict({})
        trainer = BaumWelchTrainer(self.model, options)
        # Train the model with Baum Welch
        trainer.train(self.TRAINING_DATA)
        model = trainer.model
        # Try decoding using the trained model to check it still works
        model.viterbi_decode(self.TEST_DATA)
    
    def test_baum_welch_mp(self):
        """
        Does the same as L{test_baum_welch}, but uses multiprocessing.
        
        """
        options = BaumWelchTrainer.process_option_dict({'trainprocs':-1})
        trainer = BaumWelchTrainer(self.model, options)
        # Train the model with Baum Welch
        trainer.train(self.TRAINING_DATA)
