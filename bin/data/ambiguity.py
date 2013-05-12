#!/usr/bin/env ../jazzshell
import sys, os.path
from numpy import std

from jazzparser.utils.tableprint import pprint_table
from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.grammar import get_grammar

from optparse import OptionParser

# Exclude these chord classes from the stats
EXCLUDE_CLASSES = ["Xaug"]

def main():
    parser = OptionParser()
    usage = "%prog [options] [<seq-db-file>]"
    description = "Measure the degree of ambiguity (average cats per chord) "\
        "for a grammar over a particular dataset"
    parser.add_option('-g', '--grammar', dest='grammar', action='store', help='Speficy a grammar by name')
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print "No sequence index file given: grammar stats only"
        seq_file = None
    else:
        seq_file = arguments[0]
    # Load the grammar
    grammar = get_grammar(options.grammar)
    
    # Some stats about ambiguity in the grammar
    table = []
    class_cats = []
    for class_name,chord_class in grammar.chord_classes.items():
        if class_name not in EXCLUDE_CLASSES:
            cats = grammar.get_signs_for_word(str(chord_class.words[0]))
            table.append([str(class_name), str(len(cats))])
            class_cats.append(len(cats))
    
    table.append(["Mean", "%.2f" % (float(sum(class_cats))/len(class_cats))])
    table.append(["Std dev", "%.2f" % (std(class_cats))])
    print "Cats for each chord class:"
    pprint_table(sys.stdout, table, justs=[True, True])
    
    # Ambiguity stats on the dataset
    if seq_file is not None:
        seqs = SequenceIndex.from_file(arguments[0])
        
        counts = []
        for seq in seqs:
            for chord in seq:
                cats = grammar.get_signs_for_word(chord)
                counts.append(len(cats))
        
        table = []
        table.append(["Chords", str(len(counts))])
        table.append(["Cats per chord", "%.2f" % (float(sum(counts)) / len(counts))])
        table.append(["Std dev", "%.2f" % (std(counts))])
        
        print
        pprint_table(sys.stdout, table, justs=[True, True])
    
if __name__ == "__main__":
    main()
