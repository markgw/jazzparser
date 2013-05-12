"""A tagger that returns all available tag for every word.

A trivial full tagger. Assigns all possible tags to every word. 
No statistics, no nothing.

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

from jazzparser import settings
from jazzparser.utils.input import assign_durations, strip_input
from jazzparser.taggers import Tagger, process_chord_input
from jazzparser.data import Fraction
from jazzparser.utils.options import ModuleOption

class FullTagger(Tagger):
    """
    The input to this should just be a string. It will assign all 
    possible categories to each word. All signs will have equal 
    probability.
    """
    COMPATIBLE_FORMALISMS = [
        'music_roman',
        'music_keyspan',
        'music_halfspan',
    ]
    TAGGER_OPTIONS = []
    INPUT_TYPES = ['db', 'chords']
    
    def __init__(self, *args, **kwargs):
        super(FullTagger, self).__init__(*args, **kwargs)
        process_chord_input(self)
    
    def get_signs_for_word(self, index, offset=0):
        if offset > 0:
            return []
        else:
            features = {
                'duration' : self.durations[index],
                'time' : self.times[index],
            }
            all_signs = self.grammar.get_signs_for_word(self.input[index], extra_features=features)
            return [(sign, sign.tag, 1.0/len(all_signs)) for sign in all_signs]
            
    def get_word(self, index):
        return self.input[index]
