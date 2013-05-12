#!/usr/bin/env ../jazzshell
"""
Reads in chord sequence data in our internal format and outputs a 
file of C&C supertagger training data.

"""
import sys, os
from optparse import OptionParser

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.taggers.candc.utils import sequence_to_candc_chord_super

def main():
    usage = "%prog [options] <in-file> <out-file>"
    parser = OptionParser(usage=usage)
    options, arguments = parser.parse_args()
        
    if len(arguments) < 2:
        print >>sys.stderr, "You must specify input and output data files"
        sys.exit(1)
    in_filename = os.path.abspath(arguments[0])
    out_filename = os.path.abspath(arguments[1])
    
    # Read in the data file
    seqs = SequenceIndex.from_file(in_filename)
    
    output = []
    for seq in seqs.sequences:
        # Convert each sequence to C&C supertagger training data
        output.append(sequence_to_candc_chord_super(seq))
    
    # Output the results to a file
    outfile = open(out_filename, 'w')
    outfile.write("".join(output))
    outfile.close()
    
    print >>sys.stderr, "Wrote C&C supertagger training data to %s" % out_filename

if __name__ == "__main__":
    main()
