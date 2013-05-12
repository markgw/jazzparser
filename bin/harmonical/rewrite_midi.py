#!/usr/bin/env ../jazzshell
"""
Reads a MIDI file into the L{midi} library's internal representation 
and writes it out again. This exists only as a test for the L{midi} 
library, to make sure that what gets written out sounds the same 
as what went in.

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

import sys
from optparse import OptionParser
from midi import read_midifile, write_midifile

def main():
    usage = "%prog [options] <in-file>"
    description = "Test for the midi library. Reads in a midi file and "\
        "writes it out again. Also can be useful for making sure a midi "\
        "file is in a suitable format for us to read it."
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    if len(arguments) == 0:
        print "No input MIDI file given"
        sys.exit(1)
    if len(arguments) == 1:
        print "Output filename required"
        sys.exit(1)
    infile = arguments[0]
    outfile = arguments[1]
    
    # Load the midi file
    midi = read_midifile(infile)
    write_midifile(midi, outfile)

if __name__ == "__main__":
    main()
