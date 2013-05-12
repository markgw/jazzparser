#!/usr/bin/env ../jazzshell
import sys
from optparse import OptionParser

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.data.db_mirrors.output import output_sequence_index
    
def main():
    usage = "%prog [options] <seq-file>"
    description = "Outputs some statistics about a chord sequence corpus file"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print "You must specify a sequence file"
        sys.exit(1)
        
    # Get the chord sequence
    seqindex = SequenceIndex.from_file(arguments[0])
    print "Sequences:   %d" % len(seqindex)
    
    # Get the sequence lengths
    lengths = [len(seq) for seq in seqindex]
    
    # Count up chords
    print "Chords:      %d" % sum(lengths)
    print "Min length:  %d" % min(lengths)
    print "Max length:  %d" % max(lengths)
    print "Mean length: %f" % (float(sum(lengths)) / len(lengths))
    
if __name__ == "__main__":
    main()
