#!/usr/bin/env ../jazzshell
"""
Trim a drum intro off the start of a midi file.

"""
import sys, os
from optparse import OptionParser
from midi import read_midifile, write_midifile
from jazzparser.utils.midi import trim_intro

def main():
    usage = "%prog [options] <input> <output>"
    description = "Trims a drum intro and silence from the start of a "\
                "midi file, so that it begins with a non-drum note. Use "\
                "'-' for output to output to stdout."
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify an input midi file"
        sys.exit(1)
    if len(arguments) == 1:
        print >>sys.stderr, "You must specify an output midi file"
        sys.exit(1)
        
    mid = read_midifile(arguments[0])
    mid = trim_intro(mid)
    
    if arguments[1] == "-":
        write_midifile(mid, sys.stdout)
    else:
        write_midifile(mid, arguments[1])

if __name__ == "__main__":
    main()
