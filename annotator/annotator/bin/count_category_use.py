import sys

from jazzparser.utils.tableprint import pprint_table
from django.db.models import Count
from apps.sequences.models import Chord
from optparse import OptionParser

def count_categories(options, arguments):
    # Make a Django query to get all the chord data
    query = Chord.objects.exclude(sequence__analysis_omitted=True)
    # Allow blank categories to be ignored
    if options.no_blanks:
        print >>sys.stderr, "Excluding unannotated chords"
        query = query.exclude(category="")
    categories = query.values('category').annotate(count=Count('id')).order_by('category')
    total = query.count()
    table_header = [['Category','Count','%']]
    table_data = []
    for data in categories:
        category = data['category'] and "%s" % data['category'] or "No category"
        percent = float(data['count']) / float(total) * 100.0
        table_data.append([category, data['count'], percent])
    # Sort the rows by the count
    table_data = reversed(sorted(table_data, key=lambda d: d[1]))
    # Now format the numbers
    table_data = [[row[0], "%s" % row[1], "%.02f" % row[2]] for row in table_data]
    # Add the header on the top
    table_data = table_header + table_data
    if options.csv:
        print "\n".join([",".join([v for v in row]) for row in table_data])
    else:
        pprint_table(sys.stdout, table_data, [True,False,False], "|")
        print "Total chords: %s" % total
    return 0
    
def main():
    parser = OptionParser()
    parser.add_option('-b', '--no-blanks', dest='no_blanks', action='store_true', help='Exclude unannotated categories from the counts')
    parser.add_option('-c', '--csv', dest='csv', action='store_true', help='Output as comma-separated values')
    options, arguments = parser.parse_args()
    sys.exit(count_categories(options, arguments))
    
if __name__ == "__main__":
    main()
