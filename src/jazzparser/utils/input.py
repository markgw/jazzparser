"""Utilities for chord input processing

Various general utilities for processing input to the parser. These are 
for processing string chord input and date back to the days when all the 
parser's input was in that form.

DbInput: this class has moved to L{jazzparser.data.input}, where it fits into 
a more general framework of input processing.

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

def assign_durations(string):
    """
    Computes the durations for each chord token in the string.
    Chords on their own get a duration of 1. Comma-separated sequences
    of chords get a duration of 1, split evenly between the members
    of the sequence.
    
    """
    from jazzparser.data import Fraction
    # Make sure the commas are separate tokens
    string = string.replace(",", " , ")
    string = string.replace(":", " : ")
    string = string.replace("|", "")
    tokens = string.split()
    # Group tokens into comma-separated sequences
    in_sequence = False
    units = []
    for token in tokens:
        if token == "," or token == ":":
            # The next token is in the same sequence as the last
            in_sequence = True
        elif in_sequence:
            # This token should be added to the previous token's sequence
            units[-1].append(token)
            in_sequence = False
        else:
            # Start of a new sequence
            units.append([token])
            
    # Now build the list of durations
    durations = []
    for unit in units:
        # Each sequence has a total length of 4 (assume 4 beats in bar)
        # Split this between its members.
        denominator = len(unit)
        members = [Fraction(4,denominator)] * denominator
        durations.extend(members)
    
    return durations

def strip_input(string):
    """
    Pre-processes the input string, removing any allowed meaningless 
    characters, and returns the resulting string.
    """
    from jazzparser import settings
    for ignored in settings.IGNORED_INPUT_STRINGS + [":",","]:
        string = string.replace(ignored," ")
    return string
