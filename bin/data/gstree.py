#!/usr/bin/env ../jazzshell
import sys, os.path

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.data.trees import build_tree_for_sequence, TreeBuildError, \
                        tree_to_nltk

from optparse import OptionParser
    
def main():
    usage = "%prog [options] <seq-file> <index>"
    description = "Displays a tree for the annotated derivation of a chord "\
        "sequence in the gold standard"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    if len(arguments) < 2:
        print "You must specify a sequence file and index"
        sys.exit(1)
        
    index = int(arguments[1])
    # Get the chord sequence
    sequence = SequenceIndex.from_file(arguments[0]).sequence_by_index(index)
    
    try:
        # Show the song name
        print "Tree for '%s'" % sequence.string_name
        tree = build_tree_for_sequence(sequence)
        # Output the linear textual form of the tree
        print tree
        # Display the tree using NLTK
        ntree = tree_to_nltk(tree)
        ntree.draw()
    except TreeBuildError, err:
        print >>sys.stderr, "Error parsing: %s" % err
        sys.exit(1)
    
if __name__ == "__main__":
    main()
