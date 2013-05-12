"""Predefined chord vocabs for the chord labeling model.

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

"""
Chord vocabularies defined for MIREX 2011 tasks.

See http://www.music-ir.org/mirex/wiki/2010:Audio_Chord_Estimation.

"""

MIREX_DYAD = {
    'maj' : [0, 4, 7],
    'min' : [0, 3, 7]
}

MIREX_TRIAD = {
    'maj' : [0, 4, 7],
    'min' : [0, 3, 7],
    'aug' : [0, 4, 8],
    'dim' : [0, 3, 6],
    'sus2' : [0, 2, 7],
    'sus4' : [0, 5, 7]
}

MIREX_TETRAD = {
    'maj'      : [0, 4, 7],
    'min'      : [0, 3, 7],
    'aug'      : [0, 4, 8],
    'dim'      : [0, 3, 6],
    'sus2'     : [0, 2, 7],
    'sus4'     : [0, 5, 7],
	'maj7'     : [0, 4, 7, 11],
	'7'        : [0, 4, 7, 10],
	'maj(9)'   : [0, 4, 7, 2],
	'aug(7)'   : [0, 4, 8, 11],
	'min(7)'   : [0, 3, 7, 11],
	'min7'     : [0, 3, 7, 10],
	'min(9)'   : [0, 3, 7, 2],
	'dim(7)'   : [0, 3, 6, 11],
	'hdim7'    : [0, 3, 6, 10],
	'sus4(7)'  : [0, 5, 7, 11],
	'sus4(b7)' : [0, 5, 7, 10],
	'dim7'     : [0, 3, 6, 9]
}

TRIAD = {
    'maj' : [0, 4, 7],
    'min' : [0, 3, 7],
    'aug' : [0, 4, 8],
    'dim' : [0, 3, 6],
    'sus4' : [0, 5, 7]
}

TETRAD = {
    'maj'      : [0, 4, 7],
    'min'      : [0, 3, 7],
    'aug'      : [0, 4, 8],
    'dim'      : [0, 3, 6],
    'sus4'     : [0, 5, 7],
	'maj7'     : [0, 4, 7, 11],
	'7'        : [0, 4, 7, 10],
	'min7'     : [0, 3, 7, 10],
	'hdim7'    : [0, 3, 6, 10],
	'dim7'     : [0, 3, 6, 9]
}


"""
Mappings from the chord labels in the chord corpus to each of the above 
chord vocabularies.

"""

MIREX_DYAD_CORPUS_MAPPING = [
    # (corpus, here)
    ("", "maj"),
    ("m", "min"),
    ("M7", "maj"),
    ("o7", "min"),
    ("%7", "min"),
    ("aug", "maj"),
    ("m,b5", "min"),
    ("b5", "maj"),
    ("m,M7", "min"),
    ("7", "maj"),
    ("m7", "min"),
    ("aug7", "maj"),
    ("b5,7", "maj"),
    ("sus4", "maj"),
    ("sus4,7", "maj"),
    ("aug,M7", "maj"),
    ("b5,M7", "maj"),
    ("#5,m7", "maj")
]

MIREX_TRIAD_CORPUS_MAPPING = [
    ("", "maj"),
    ("m", "min"),
    ("M7", "maj"),
    ("o7", "dim"),
    ("%7", "dim"),
    ("aug", "aug"),
    ("m,b5", "dim"),
    ("b5", "maj"),
    ("m,M7", "min"),
    ("7", "maj"),
    ("m7", "min"),
    ("aug7", "aug"),
    ("b5,7", "maj"),
    ("sus4", "sus4"),
    ("sus4,7", "sus4"),
    ("aug,M7", "aug"),
    ("b5,M7", "maj"),
    ("#5,m7", "aug"),
    # We need something to map to sus2
    ("", "sus2"),
]

MIREX_TETRAD_CORPUS_MAPPING = [
    ("", "maj"),
    ("m", "min"),
    ("M7", "maj7"),
    ("o7", "dim7"),
    ("%7", "hdim7"),
    ("aug", "aug"),
    ("m,b5", "dim"),
    ("b5", "maj"),
    ("m,M7", "min(7)"),
    ("7", "7"),
    ("m7", "min7"),
    ("aug7", "aug"),
    ("b5,7", "7"),
    ("sus4", "sus4"),
    ("sus4,7", "sus4(b7)"),
    ("aug,M7", "aug"),
    ("b5,M7", "dim(7)"),
    ("#5,m7", "aug(7)"),
    # We also need something to map to the remaining MIREX chords
    ("", "sus2"),
    ("M7", "maj(9)"),
    ("m7", "min(9)"),
    ("sus4", "sus4(7)")
]

TRIAD_CORPUS_MAPPING = [
    ("", "maj"),
    ("m", "min"),
    ("M7", "maj"),
    ("o7", "dim"),
    ("%7", "dim"),
    ("aug", "aug"),
    ("m,b5", "dim"),
    ("b5", "maj"),
    ("m,M7", "min"),
    ("7", "maj"),
    ("m7", "min"),
    ("aug7", "aug"),
    ("b5,7", "maj"),
    ("sus4", "sus4"),
    ("sus4,7", "sus4"),
    ("aug,M7", "aug"),
    ("b5,M7", "maj"),
    ("#5,m7", "aug"),
]

TETRAD_CORPUS_MAPPING = [
    ("", "maj"),
    ("m", "min"),
    ("M7", "maj7"),
    ("o7", "dim7"),
    ("%7", "hdim7"),
    ("aug", "aug"),
    ("m,b5", "dim"),
    ("b5", "maj"),
    ("m,M7", "min"),
    ("7", "7"),
    ("m7", "min7"),
    ("aug7", "aug"),
    ("b5,7", "7"),
    ("sus4", "sus4"),
    ("sus4,7", "sus4"),
    ("aug,M7", "aug"),
    ("b5,M7", "dim"),
    ("#5,m7", "aug"),
]


######################## Utilities and index #############################

def get_mapping(mapping, reverse=False):
    """
    Gets a dict of the given list mapping, optionally reversing it. Where a 
    mapping is not unique, the first instance is used.
    
    """
    if reverse:
        mapping = [(y,x) for (x,y) in mapping]
    
    dic = {}
    for (source,target) in mapping:
        if source not in dic:
            dic[source] = target
    
    return dic
    
CHORD_VOCABS = {
    'mirex-dyad' : (MIREX_DYAD, MIREX_DYAD_CORPUS_MAPPING),
    'mirex-triad' : (MIREX_TRIAD, MIREX_TRIAD_CORPUS_MAPPING),
    'mirex-tetrad' : (MIREX_TETRAD, MIREX_TETRAD_CORPUS_MAPPING),
    'triad' : (TRIAD, TRIAD_CORPUS_MAPPING),
    'tetrad' : (TETRAD, TETRAD_CORPUS_MAPPING),
}
