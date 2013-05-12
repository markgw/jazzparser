import sys, itertools
from optparse import OptionParser

from apps.sequences.models import ChordSequence, Chord
    
def main():
    description = "Find all uses of particular categories"
    parser = OptionParser(description=description)
    options, arguments = parser.parse_args()
    
    if len(arguments) == 0:
        print >>sys.stderr, "Please specify a category"
        sys.exit(1)
    cat_name = arguments[0]
        
    chords = Chord.objects.filter(category=cat_name)
    print "Found %d occurences" % chords.count()
    counts = [(seq.string_name, len(list(chords))) for (seq, chords) in itertools.groupby(chords, lambda c:c.sequence)]
    for sequence,count in reversed(sorted(counts, key=lambda x:x[1])):
        print "%s : %d" % (sequence, count)
    
if __name__ == "__main__":
    main()
