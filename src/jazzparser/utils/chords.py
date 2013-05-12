"""Chord processing utilities.

A library of utility functions used throughout the Jazz Parser relating 
to chord processing in the input.

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

import xml.dom.minidom
import re, copy
import logging

# Get the logger from the logging system
logger = logging.getLogger("main_logger")


# Conversions between Lilypond notes and their numeric representation
ly_note_to_int = {"c" : 0, "C" : 0,\
               "d" : 2, "D" : 2,\
               "e" : 4, "E" : 4,\
               "f" : 5, "F" : 5,\
               "g" : 7, "G" : 7,\
               "a" : 9, "A" : 9,\
               "b" : 11, "B" : 11,\
               "r" : None }

ly_note_to_base_int = {"c" : 0, "C" : 0,\
               "d" : 1, "D" : 1,\
               "e" : 2, "E" : 2,\
               "f" : 3, "F" : 3,\
               "g" : 4, "G" : 4,\
               "a" : 5, "A" : 5,\
               "b" : 6, "B" : 6,\
               "r" : None }

int_to_ly_note = { 0 : "c",\
                   1 : "cis",\
                   2 : "d",\
                   3 : "dis",\
                   4 : "e",\
                   5 : "f",\
                   6 : "fis",\
                   7 : "g",\
                   8 : "gis",\
                   9 : "a",\
                   10: "ais",\
                   11: "b",\
                   None: "r"}

int_to_note_name = { 0 : "C", \
                     1 : "Db", \
                     2 : "D", \
                     3 : "Eb", \
                     4 : "E", \
                     5 : "F", \
                     6 : "Gb", \
                     7 : "G", \
                     8 : "Ab", \
                     9 : "A", \
                     10: "Bb", \
                     11: "B" }

ROMAN_NUMERALS = { 0  : "I",
                  1  : "bII",
                  2  : "II",
                  3  : "bIII",
                  4  : "III",
                  5  : "IV",
                  6  : "#IV",
                  7  : "V",
                  8  : "bVI",
                  9  : "VI",
                  10 : "bVII",
                  11 : "VII" }


def chord_numeral_to_int(chord_numeral, strict=False):
    """
    Given a chord numeral (e.g. "I" or "bVII"), returns the integer
    that corresponds to this chord root.
    Returns None if input is either a chord variable ("X", "Y") or 
    itself None.
    If strict is set, doesn't allow variable names.
    
    """
    if strict:
        numerals =  { "I"   : 0,
                      "II"  : 2,
                      "III" : 4,
                      "IV"  : 5,
                      "V"   : 7,
                      "VI"  : 9,
                      "VII" : 11, }
        root_pattern = re.compile(r'^([b|\#]?)(I{1,3}|I?V|VI{0,2})$')
    else:
        # Map roman numerals to numbers
        numerals =  { "I"   : 0,
                      "II"  : 2,
                      "III" : 4,
                      "IV"  : 5,
                      "V"   : 7,
                      "VI"  : 9,
                      "VII" : 11,
                      "X"   : None,
                      "Y"   : None,
                      "Z"   : None,
                      None  : None }
        # Use a regular expression to split the chord root into a 
        #  its accidental and numeral.
        root_pattern = re.compile(r'^([b|\#]?)(I{1,3}|I?V|VI{0,2}|X|Y|Z)$')

    # Map accidentals to a numeric adjustment
    accidentals = { "#" : 1, "" : 0, "b" : -1 }
    
    result = root_pattern.search(chord_numeral)
    if result is None:
        raise ChordError, "The string '%s' cannot be parsed as a chord" % chord_numeral
    result = result.groups()
    accidental = result[0]
    numeral = result[1]
    
    # Map the root name to a number
    if numeral not in numerals:
        raise ChordError, "Chord numeral \"%s\" was not recognised." % numeral
    chord_num = numerals[numeral]
    # Adjust this number according to the accidental
    if chord_num is not None:
        if accidental not in accidentals:
            raise ChordError, "Accidental \"%s\" was not recognised." \
                % accidental
        chord_num += accidentals[accidental]
    return chord_num
    
def pitch_class_to_int(chord_numeral):
    """ Like L{chord_numeral_to_int}, but for pitch class labels. """
    pcs =  { "C"   : 0,
             "D"  : 2,
             "E" : 4,
             "F"  : 5,
             "G"   : 7,
             "A"  : 9,
             "B" : 11, }
    root_pattern = re.compile(r'^([A-G])(b*|\#*)$')
    
    result = root_pattern.search(chord_numeral)
    if result is None:
        raise ChordError, "The string '%s' cannot be parsed as a chord" % \
            chord_numeral
    pc_str,accidental_str = result.groups()
    
    pc = pcs[pc_str]
    # Adjust this number according to the accidentals
    if accidental_str:
        if accidental_str[0] == "#":
            pc += len(accidental_str)
        elif accidental_str[0] == "b":
            pc -= len(accidental_str)
    return pc % 12

def int_to_chord_numeral(chord_int):
    """
    Given an internal integer representation of a chord root (i.e. a
    note of the scale), returns the roman numeral as a string. This
    will always use the same convention for #s and bs, so may not be 
    the same as the numeral that generated the note number.
    
    The input numbers 0-11 correspond to I-VII in the scale. The input
    need to be in this range. Outside it, numbers will be mapped into
    this range by "% 12".
    
    Returns "X" if input is None.
    
    """
    if chord_int is None:
        return "X"
    # Take number mod 12, in case it's not in correct range
    return ROMAN_NUMERALS[chord_int % 12]

def int_to_pitch_class(chord_int):
    """
    Like L{int_to_chord_numeral}, but outputs a pitch class name instead of 
    roman numeral. Returns "X" if input is None.
    
    """
    if chord_int is None:
        return "X"
    else:
        # Take number mod 12, in case it's not in correct range
        return int_to_note_name[chord_int % 12]

def generalise_chord_name(chord_name):
    """
    The grammar generalises over chord names, using X to mean "any 
    roman numeral chord root". When a chord name comes as input to 
    the parser, say "IIm", we look up not "IIm", but "Xm".
    
    Given any chord name, this function returns the generalised 
    chord name to look up in the grammar. 
    """
    from jazzparser.data import Chord
    # Try building a chord from the chord name
    chord = Chord.from_name(chord_name)
    # Only interested in the tetrad type
    return "X%s" % chord.tetrad_type

def interval_observation_from_chord_string_pair(chord1, chord2, type_mapping=None):
    """
    Given two strings representing chords, produces a string representing 
    a chord observation of the form x-t, where x is the interval between 
    the chords (numeric) and t is the type of the first chord.
    """
    from jazzparser.data import Chord
    chord1 = Chord.from_name(chord1)
    if chord2 is None:
        interval = ""
    else:
        chord2 = Chord.from_name(chord2)
        interval = "%d" % Chord.interval(chord1,chord2)
    # Apply a mapping to the chord type if one was given
    if type_mapping is not None:
        ctype = type_mapping[chord1.type]
    else:
        ctype = chord1.type
    return "%s-%s" % (interval, ctype)

class ChordError(Exception):
    """
    Raised when there's a problem recognising or processing a chord.
    """
    pass
