"""
Script to build the explicit tree that is implicit in a chord 
sequence in the database
"""
import sys
from optparse import OptionParser

from apps.sequences.models import ChordSequence
from jazzparser.data.trees import build_tree_for_sequence, TreeBuildError, \
                        tree_to_nltk
    
def main():
    parser = OptionParser()
    parser.add_option("-s", "--debug-stack", dest="debug_stack", action="store_true", help="print out the stack before each input is processed")
    parser.add_option("-d", "--draw", dest="draw", action="store_true", help="use NLTK to draw the tree for the sequence")
    options, arguments = parser.parse_args()
    
    if len(arguments) == 0:
        print >>sys.stderr, "You need to specify a sequence ID to parse"
        sys.exit(1)
        
    try:
        # Try getting a chord sequence for the given ID
        try:
            sequence = ChordSequence.objects.get(id=int(arguments[0]))
            if sequence.analysis_omitted:
                print >>sys.stderr, "Ignoring %s, since it's marked as unannotated" % sequence.name.encode('ascii','ignore')
                return
        except ChordSequence.DoesNotExist:
            raise TreeBuildError, "there is no chord sequence with ID %s" % arguments[0]
            
        # Build the explicit tree
        print "Building tree for '%s'" % sequence.string_name
        # Use the sequence's mirror
        sequence = sequence.mirror
        tree = build_tree_for_sequence(sequence, debug_stack=options.debug_stack)
        # Output the linear textual form of the tree
        print tree
        if options.draw:
            # Display the tree using NLTK
            ntree = tree_to_nltk(tree)
            ntree.draw()
    except TreeBuildError, err:
        print >>sys.stderr, "Error parsing: %s" % err
        sys.exit(1)
    
if __name__ == "__main__":
    main()
