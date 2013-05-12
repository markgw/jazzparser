#!/usr/bin/env ../jazzshell
"""
Split up a sequence data file into a number of partitions and output 
them to separate files.

"""
import sys, os
from optparse import OptionParser

from jazzparser.data.db_mirrors import SequenceIndex, save_sequences
from jazzparser.utils.data import partition, holdout_partition

DEFAULT_PARTITIONS = 10

def main():
    usage = "%prog [options] <in-file>"
    parser = OptionParser(usage=usage)
    parser.add_option("-p", "--partitions", dest="partitions", action="store", type="int", default=DEFAULT_PARTITIONS, help="the number of partitions to use (default: %d)" % DEFAULT_PARTITIONS)
    parser.add_option("--ids", dest="ids", action="store_true", help="don't output any files - just print out a list of the ids of the sequences in each partition")
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify an input data file"
        sys.exit(1)
    filename = os.path.abspath(arguments[0])
    
    # Read in the data file
    seqs = SequenceIndex.from_file(filename)
    
    part_pattern = "%s.part%%d" % filename
    heldout_pattern = "%s.heldout_part%%d" % filename
    # Divide the data up into partitions, with their complements
    parts = zip(partition(seqs.sequences, options.partitions), holdout_partition(seqs.sequences, options.partitions))
    # Save each partition and its complement
    for i,(part,heldout) in enumerate(parts):
        if options.ids:
            # Just print out a list of the ids in the partition
            print " ".join(["%d" % s.id for s in part])
        else:
            save_sequences(part_pattern % i, part)
            save_sequences(heldout_pattern % i, heldout)
            print >>sys.stderr, "Wrote partition %d to %s and %s" % (i,part_pattern % i,heldout_pattern % i)

if __name__ == "__main__":
    main()
