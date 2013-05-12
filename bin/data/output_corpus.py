#!/usr/bin/env ../jazzshell
import sys
from optparse import OptionParser

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.data.db_mirrors.output import output_sequence_index
    
def main():
    usage = "%prog [options] <seq-file> <out-file>"
    description = "Outputs a full corpus from a sequence index file to a text "\
        "file that can more easily be read by other people. If <out-file> is "\
        "omitted, data is output to stdout"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print "You must specify a sequence file"
        sys.exit(1)
        
    # Get the chord sequence
    seqindex = SequenceIndex.from_file(arguments[0])
    if len(arguments) > 1:
        # Open a file to write to
        outfile = open(arguments[1], 'w')
    else:
        # Output to stdout
        outfile = sys.stdout
    
    try:
        output_sequence_index(seqindex, outfile)
    finally:
        outfile.close()
    
if __name__ == "__main__":
    main()
