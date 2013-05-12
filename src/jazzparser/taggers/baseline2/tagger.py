"""Second, very simple baseline tagger model.

Tagging model 'baseline2' is another very simple tagging model that tags 
using just the unigram probabilities on the basis of observed chord 
intervals (no types).

It is the model presented as 'model 4' in the Stupid Baselines talk.

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
__author__ = "Mark Granroth-Wilding <mark@granroth-wilding.co.uk>" 

import pickle
from jazzparser.taggers.models import ModelTagger, ModelLoadError, TaggerModel
from jazzparser.taggers import process_chord_input
from jazzparser.utils.probabilities import batch_sizes
from jazzparser.data import Chord
from jazzparser.utils.base import group_pairs

def observation_from_chord_pair(crd1, crd2):
    if crd1 is None or crd2 is None:
        return "0"
    return "%d" % Chord.interval(Chord.from_name(str(crd1)), Chord.from_name(str(crd2)))

class Baseline2Model(TaggerModel):
    """
    A class to encapsulate the model data for the tagger.
    """
    MODEL_TYPE = "baseline2"
    
    def __init__(self, model_name, *args, **kwargs):
        super(Baseline2Model, self).__init__(model_name, *args, **kwargs)
        self.category_chord_count = {}
        self.category_count = {}
        self.chord_count = {}
    
    def _add_category_chord_count(self, category, chord):
        """
        Adds a count of the joint observation of the category and the 
        chord and of the category and the chord themselves.
        """
        # Count the cat-chord combo
        cat_chords = self.category_chord_count.setdefault(category, {})
        if chord in cat_chords:
            cat_chords[chord] += 1
        else:
            cat_chords[chord] = 1
        # Count the cat occurrence
        if category in self.category_count:
            self.category_count[category] += 1
        else:
            self.category_count[category] = 1
        # Count the chord occurrence
        if chord in self.chord_count:
            self.chord_count[chord] += 1
        else:
            self.chord_count[chord] = 1
        
    def train(self, sequences, grammar=None, logger=None):
        seqs = 0
        chords = 0
        # Each sequence in the given corpus
        for seq in sequences:
            seqs += 1
            # Each chord in the sequence
            for c1,c2 in group_pairs(seq.iterator(), none_final=True):
                chords += 1
                self._add_category_chord_count(c1.category, observation_from_chord_pair(c1, c2))
        # Add a bit of training info to the descriptive text
        self.model_description = """\
Unigram probability model, observing only root intervals

Training sequences: %(seqs)d
Training samples: %(samples)d""" % {
                'seqs' : seqs,
                'samples' : chords
            }
        
    def get_prob_cat_given_chord_pair(self, cat, chord1, chord2):
        obs = observation_from_chord_pair(chord1, chord2)
        chord_count = self.chord_count.get(obs, 0)
        if chord_count == 0:
            # Unseen data: give all seen cats equal probability
            if cat in self.category_count:
                return 1.0 / len(self.category_count)
            else:
                # Haven't seen the category before: don't smooth
                return 0.0
        count = self.category_chord_count.get(cat, {}).get(obs, 0)
        return float(count) / chord_count

class Baseline2Tagger(ModelTagger):
    """
    The second of the simple baseline tagger models. This models unigram 
    probabilities of tags, given only the intervals between chords.
    
    """
    MODEL_CLASS = Baseline2Model
    INPUT_TYPES = ['db', 'chords']
    
    def __init__(self, grammar, input, options={}, *args, **kwargs):
        super(Baseline2Tagger, self).__init__(grammar, input, options, *args, **kwargs)
        process_chord_input(self)
        
        #### Tag the input sequence ####
        self._tagged_data = []
        self._batch_ranges = []
        # Group the input into pairs
        inpairs = group_pairs(self.input, none_final=True)
        # Get all the possible signs from the grammar
        for index,pair in enumerate(inpairs):
            features = {
                'duration' : self.durations[index],
                'time' : self.times[index],
            }
            word_signs = []
            # Now assign a probability to each tag, given the observation
            for tag in self.model.category_count.keys():
                sign = self.grammar.get_sign_for_word_by_tag(self.input[index], tag, extra_features=features)
                if sign is not None:
                    probability = self.model.get_prob_cat_given_chord_pair(tag, *pair)
                    word_signs.append((sign, tag, probability))
            word_signs = list(reversed(sorted([(sign, tag, prob) for sign,tag,prob in word_signs], key=lambda x:x[2])))
            self._tagged_data.append(word_signs)
            
            # Work out the sizes of the batches to return these in
            batches = batch_sizes([p for __,__,p in word_signs], self.batch_ratio)
            # Transform these into a form that's easier to use for getting the signs
            so_far = 0
            batch_ranges = []
            for batch in batches:
                batch_ranges.append((so_far,so_far+batch))
                so_far += batch
            self._batch_ranges.append(batch_ranges)

    def get_signs_for_word(self, index, offset=0):
        if self.best_only:
            # Only ever return one sign
            if offset == 0 and len(self._tagged_data[index]) > 0:
                return [self._tagged_data[index][0]]
            else:
                return None
        ranges = self._batch_ranges[index]
        if offset >= len(ranges):
            # No more batches left
            return None
        start,end = ranges[offset]
        return self._tagged_data[index][start:end]
        
    def get_word(self, index):
        return self.input[index]
