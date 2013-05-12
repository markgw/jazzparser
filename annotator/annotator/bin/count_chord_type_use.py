"""
Prints a count of the 
"""
import sys

from django.db.models import Count
from apps.sequences.models import Chord, ChordType
from optparse import OptionParser

from jazzparser.tableprint import pprint_table

def count_chords(options, arguments):
    table = [["Chord type", "Count"]]
    for ctype in ChordType.objects.all():
        table.append(["%s" % ctype, "%s" % ctype.chord_set.count()])
    
    # Justification of columns
    justs = [False, True]
    # Print out the table
    print
    pprint_table(sys.stdout, table, justs, "|")
    print "Total chords: %s" % Chord.objects.count()
    return 0
    
def main():
    parser = OptionParser()
    options, arguments = parser.parse_args()
    sys.exit(count_chords(options, arguments))
    
if __name__ == "__main__":
    main()
