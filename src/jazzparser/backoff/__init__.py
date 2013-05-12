"""Modelling without parsing

This module is for baseline models that do not use grammars to model 
the syntax of music, but model the tonal-space semantics directly. 
We do not expect this to be a good approach, but are implementing it 
for comparison, so we can see how much is added by use of the human 
knowledge and higher-level structure in the grammar, using a parsing 
approach.

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

from .loader import get_backoff_builder

BUILDERS = {
    'ngram' : ('ngram','HmmPathBuilder'),
    'midingram' : ('ngram','MidiHmmPathBuilder'),
}
