#!/usr/bin/env ../jazzshell
import sys, os.path

from jazzparser.utils.tableprint import pprint_table
from jazzparser.data.db_mirrors import SequenceIndex

from optparse import OptionParser

def count_categories(options, arguments):
    # Read in the sequence data from the file
    filename = os.path.abspath(arguments[0])
    seqs = SequenceIndex.from_file(filename)
    
    category_counts = {}
    total = 0
    # Count up how many times each category is used
    for seq in seqs.sequences:
        for chord in seq.iterator():
            total += 1
            if chord.category not in category_counts:
                category_counts[chord.category] = 1
            else:
                category_counts[chord.category] += 1
    table_header = [['Category','Count','%']]
    table_data = []
    for cat,count in category_counts.items():
        category = cat or "No category"
        percent = float(count) / float(total) * 100.0
        table_data.append([category, count, percent])
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
    usage = "%prog [options] <in-file>"
    description = "Display information about the distribution of categories "\
        "in the sequences in the input file. This is similar to "\
        "count_category_use.py in the database scripts."
    parser.add_option('-c', '--csv', dest='csv', action='store_true', help='Output as comma-separated values')
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print "You must specify an input file"
        sys.exit(1)
    sys.exit(count_categories(options, arguments))
    
if __name__ == "__main__":
    main()
