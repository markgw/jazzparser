#!/usr/bin/env ../jazzshell
"""
Filter a sequence data file to remove any sequences that are not fully 
annotated and write the result back to the file.

"""
import sys, os
from optparse import OptionParser

from jazzparser.data.db_mirrors import SequenceIndex, save_sequences

def main():
    usage = "%prog [options] <in-file>"
    description = "Filter a sequence data file to remove any sequences "\
        "that are not fully annotated and write the result back to the file."
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify an input data file"
        sys.exit(1)
    in_filename = os.path.abspath(arguments[0])
    
    # Read in the data file
    seqs = SequenceIndex.from_file(in_filename)
    
    sequences = [seq for seq in seqs.sequences if seq.fully_annotated]
    save_sequences(in_filename, sequences)
    
    print >>sys.stderr, "Removed %d sequences" % (len(seqs.sequences)-len(sequences))

if __name__ == "__main__":
    main()
