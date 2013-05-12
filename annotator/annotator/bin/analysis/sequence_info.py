"""
Command line tools for viewing info about sequences that are in the database.
"""
import sys
from optparse import OptionParser

from apps.sequences.models import ChordSequence
    
def main():
    parser = OptionParser()
    parser.add_option("-l", "--length", dest="length", action="store_true", help="show the length of the sequence")
    parser.add_option("-f", "--fully-annotated", dest="fully_annotated", action="store_true", help="show whether alls chords have got a category")
    parser.add_option("-p", "--annotated", dest="percentage_annotated", action="store_true", help="show what percentage of the chords have a category")
    parser.add_option("-s", "--sequence", dest="sequence", action="store_true", help="print the sequence itself")
    options, arguments = parser.parse_args()
    
    if len(arguments) == 0:
        print >>sys.stderr, "Please specify a sequence ID"
        sys.exit(1)
        
    try:
        # Try getting a chord sequence for the given ID
        try:
            sequence = ChordSequence.objects.get(id=int(arguments[0]))
        except ChordSequence.DoesNotExist:
            raise SequenceInfoError, "there is no chord sequence with ID %s" % arguments[0]
        # Print the requested information
        print "Name: %s" % sequence.name
        if options.length:
            print "Length: %d chords" % sequence.length
        if options.fully_annotated:
            print "Fully annotated: %s" % sequence.fully_annotated
        if options.percentage_annotated:
            print "Proportion annotated: %.3f" % sequence.percentage_annotated
        if options.sequence:
            print "Chord sequence:\n%s" % " ".join(["%s" % chord for chord in sequence.iterator()])
    except SequenceInfoError, err:
        print >>sys.stderr, "Error retreiving info: %s" % err
        sys.exit(1)

class SequenceInfoError(Exception):
    pass

    
if __name__ == "__main__":
    main()
