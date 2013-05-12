"""Annotator consistency evaluation data structures.

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

import pickle
from . import SequenceIndex

class ConsistencyData(object):
    """
    Data structure to store multiple annotations of the same chord sequences 
    to evaluate annotator consistency.
    
    Currently only supports pairs of annotations for each sequence. If 
    more than two alternatives need to be compared, this will have to be 
    extended.
    
    """
    def __init__(self, sequences, pairs, sequence_index=False):
        if sequence_index:
            # We've been given a fully-formed sequence index
            self.sequences = sequences
        else:
            self.sequences = SequenceIndex(sequences)
        self.pairs = pairs
    
    def __len__(self):
        return len(self.pairs)
        
    def __getitem__(self, index):
        id1, id2 = self.pairs[index]
        return (self.sequences.sequence_by_id(id1),
                self.sequences.sequence_by_id(id2))
    
    @staticmethod
    def from_file(filename):
        with open(filename, 'r') as file:
            # Read in the pickled data
            unpick = pickle.Unpickler(file)
            data = unpick.load()
        si, pairs = data
        return ConsistencyData(si, pairs, sequence_index=True)
    
    def save(self, filename):
        with open(filename, 'w') as file:
            pickler = pickle.Pickler(file)
            pickler.dump((self.sequences, self.pairs))
