#!/usr/bin/env ../jazzshell
import sys, os
from optparse import OptionParser

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.taggers.pretagged.tagger import TagsFile

def main():
    usage = "%prog [options] <in-file> <out-file>"
    description = "Reads a sequence index file and produces a tag sequence "\
        "file containing the gold standard tags for every sequence"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
        
    if len(arguments) < 2:
        print >>sys.stderr, "You must specify input and output data files"
        sys.exit(1)
    in_filename = os.path.abspath(arguments[0])
    out_filename = os.path.abspath(arguments[1])
    
    # Read in the data file
    seqs = SequenceIndex.from_file(in_filename)
    
    tags = {}
    for seq in seqs.sequences:
        # Convert each sequence to a list of tags
        tags[seq.id] = [c.category for c in seq]
    
    # Output the results to a file
    tagsfile = TagsFile(tags)
    tagsfile.to_file(out_filename)
    
    print >>sys.stderr, "Wrote tags data to %s" % out_filename

if __name__ == "__main__":
    main()
