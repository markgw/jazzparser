#!/usr/bin/env ../jazzshell
import sys, os.path

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.data.parsing import keys_for_sequence
from optparse import OptionParser
    
def main():
    usage = "%prog [options] <seq-file> <index>"
    description = "Outputs the key associated with each chord of a sequence "\
        "from an annotated corpus"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    if len(arguments) < 2:
        print "You must specify a sequence file and index"
        sys.exit(1)
        
    index = int(arguments[1])
    # Get the chord sequence
    seq = SequenceIndex.from_file(arguments[0]).sequence_by_index(index)
    
    print keys_for_sequence(seq)
    
if __name__ == "__main__":
    main()
