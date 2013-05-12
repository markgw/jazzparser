"""Base classes for segmidi taggers.

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
from jazzparser.taggers.models import ModelTagger
from jazzparser.utils.options import ModuleOption

class SegmidiTagger(ModelTagger):
    """
    Base class for segmented MIDI taggers.
    
    Inherits from L{jazzparser.taggers.models.ModelTagger}, so subclasses 
    should implement the abstract methods of this.
    
    """
    COMPATIBLE_FORMALISMS = [
        'music_halfspan',
    ]
    INPUT_TYPES = ['segmidi']
    
    def __init__(self, *args, **kwargs):
        super(SegmidiTagger, self).__init__(*args, **kwargs)
    
    def get_signs(self, offset=0):
        raise NotImplementedError, "called base SegmidiTagger's get_signs()"
            
    def get_word(self, index):
        return "<midi segment %d>" % index
        
    def get_string_input(self):
        return [str(i) for i in range(self.input_length)]
