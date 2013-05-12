#!/usr/bin/env ../../jazzshell
import sys, os

from optparse import OptionParser
from midi import write_midifile
from jazzparser.data.corpora.temperley import DataSequence
from jazzparser.data.corpora import get_corpus_file
    
def main():
    usage = "%prog [options] <corpus-filename> <out-filename>"
    description = "Produces a MIDI file from one of the files of the "\
        "Kostka-Payne corpus compiled by David Temperley. "\
        "<corpus-filename> may be either a path to the file or the "\
        "name of a file in the corpus (which is stored within the project)."
    parser = OptionParser(description=description, usage=usage)
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print >>sys.stderr, "You must specify an input filename"
        sys.exit(1)
    elif len(arguments) < 2:
        print >>sys.stderr, "You must specify an output midifile name"
        sys.exit(1)
        
    filename = arguments[0]
    outname = arguments[1]
    
    # Read in the input file
    seq = DataSequence.from_file(filename)
    
    # Produce a midi stream from the data sequence
    mid = seq.to_midi()
    
    # Output the midi file
    write_midifile(mid, outname)

if __name__ == "__main__":
    main()
