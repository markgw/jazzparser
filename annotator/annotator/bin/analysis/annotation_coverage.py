import sys

from itertools import groupby

from jazzparser.utils.tableprint import pprint_table
from django.db.models import Count
from apps.sequences.models import Chord, ChordSequence
from optparse import OptionParser

def coverage(options, arguments):
    print "Computing statistics about annotation coverage"
    # Check how many sequences are unannotated
    unannotated = ChordSequence.objects.filter(analysis_omitted=True)
    annotated = ChordSequence.objects.filter(analysis_omitted=False)
    num_unan = unannotated.count()
    num_an = annotated.count()
    prop_unan = float(num_unan)/float(num_unan+num_an) * 100.0
    print "   Sequences with no annotation: %d (%.2f%%)" % (num_unan, prop_unan)
    print "   Sequences with annotation: %d" % (num_an)
    print "Ignoring unannotated sequences from now on"
    # Make a Django query to get all the chord data
    chords = Chord.objects.exclude(sequence__analysis_omitted=True)
    # Show some statistics about the whole bag of chords
    total_chords = chords.count()
    print "   Total chords: %d" % chords.count()
    blank_chords = chords.filter(category="").count()
    prop_blank = float(blank_chords) / float(total_chords) * 100.0
    print "   Unannotated chords: %d (%.2f%%)" % (blank_chords, prop_blank)
    # Show some statistics about the sequences
    seq_annotation = [s.number_annotated for s in annotated]
    unan_chords = groupby(sorted([total-annot for annot,total in seq_annotation]))
    fully_an = len(list(unan_chords.next()[1]))
    prop_fully_an = float(fully_an) / float(num_an) * 100.0
    print "   Fully annotated sequences: %d (%.2f%%)" % (fully_an, prop_fully_an)
    print "   Sequences with x chords unannotated:"
    # Skip the first one (0)
    for key,group in unan_chords:
        print "     %s : %d" % (format(key, " >3d"), len(list(group)))
    return 0
    
def main():
    parser = OptionParser()
    options, arguments = parser.parse_args()
    sys.exit(coverage(options, arguments))
    
if __name__ == "__main__":
    main()
