"""A completely null tagger that always fails to assign any tags.

This tagger should not be used in practice. It is useful for tests where 
you don't want the parser to succeed, but just check that the scripts work.

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
from jazzparser.taggers import Tagger
from jazzparser.data import Fraction
from jazzparser.utils.options import ModuleOption

class FailTagger(Tagger):
    """
    The input doesn't matter. No tags will ever be returned.
    
    """
    COMPATIBLE_FORMALISMS = [
        'music_roman',
        'music_keyspan',
        'music_halfspan',
    ]
    TAGGER_OPTIONS = []
    INPUT_TYPES = ['db', 'chords','segmidi','null']
    
    def __init__(self, *args, **kwargs):
        super(FailTagger, self).__init__(*args, **kwargs)
    
    def get_signs(self, offset=0):
        return []
            
    def get_word(self, index):
        return self.input[index]
