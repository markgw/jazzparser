#!/usr/bin/env ../jazzshell
"""
Takes a sequence data file, partitions it into the number of partitions 
given and prints out the indices of the sequences the appear in the 
requested partition.
"""
import sys, os
from optparse import OptionParser

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.utils.data import partition

def main():
    usage = "%prog <in-file> <part>/<parts>"
    description = "Takes a sequence data file, partitions it into the "\
        "number of partitions given and prints out the indices of the "\
        "sequences the appear in the requested partition. Specify the "\
        "partition number (from 0) and total number of partitions in the "\
        "form <partition-num>/<total-parts>."
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify an input data file"
        sys.exit(1)
    elif len(arguments) == 1:
        print >>sys.stderr, "You must give a partition specifier: <part>/<parts>"
    filename = os.path.abspath(arguments[0])
    part, parts = arguments[1].split("/")
    part, parts = int(part), int(parts)
    
    # Read in the data file
    seqs = SequenceIndex.from_file(filename)
    
    # Partition the sequences
    indices = range(len(seqs))
    # Use the partition function to ensure this partitioning is consistent
    #  with all other places the sequences get partitioned
    all_parts = partition(indices, parts)
    print " ".join(["%d" % i for i in all_parts[part]])
    
if __name__ == "__main__":
    main()
