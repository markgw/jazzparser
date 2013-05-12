"""Data structures for chord labeler.

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

from jazzparser.utils.chords import int_to_note_name

class ChordLabel(object):
    """
    Representation of a chord label. Simple wrapper around what could really 
    just be represented as a small tuple. Using this class allows us to make 
    it clearer what the fields represent and provide easy access to conversions 
    (e.g. string representation).
    
    C{key} may be None if you wish to store a chord label without a key value.
    
    """
    def __init__(self, root, label, key, model_label=None):
        self.root = root % 12
        self.label = label
        self.key = key
        self.model_label = model_label
        
        if self.key is not None:
            self.key = self.key % 12
    
    def __eq__(self, other):
        return type(self) == type(other) and \
               self.root == other.root and \
               self.label == other.label and \
               self.key == other.key
    
    def __str__(self):
        if self.key is not None:
            return "%s%s/%s" % (int_to_note_name[self.root], \
                                self.label, 
                                int_to_note_name[self.key])
        else:
            return "%s%s" % (int_to_note_name[self.root], self.label)
    
    def __repr__(self):
        return str(self)
