#!/usr/bin/env ../jazzshell
import sys, os.path

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.utils.tableprint import pprint_table

from optparse import OptionParser
    
def main():
    usage = "%prog [options] <in-file> [<index1> [<index2> ...]]"
    description = "Print the names of sequences in a sequence input "\
            "file. Optionally specify indices of sequences. If no index "\
            "is given, displays all sequences."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("--sa", "-a", "--sort-alpha", "--alpha", dest="alphabetical", action="store_true", help="order sequences alphabetically by name")
    parser.add_option("--sl", "--sort-length", dest="sort_length", action="store_true", help="order sequences by length")
    parser.add_option("-i", "--index", dest="index", action="store_true", help="also display the indices in the sequence file of each sequence, in the column before the ids")
    parser.add_option("-l", "--lengths", dest="lengths", action="store_true", help="output lengths of the sequences")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print "You must specify an input file"
        sys.exit(1)
    seqs = SequenceIndex.from_file(arguments[0])
    
    indices = [int(ind) for ind in arguments[1:]]
    if len(indices) == 0:
        sequences = seqs.sequences
    else:
        sequences = [seqs.sequence_by_index(index) for index in indices]
        
    if options.alphabetical:
        # Sort by string_name
        sequences.sort(key=lambda s:s.string_name)
    elif options.sort_length:
        # Sort by sequence length
        sequences.sort(key=lambda s:len(s))
        
    header = ["Song name", "Id"]
    justs = [True, False]
    if options.lengths:
        header.append("Length")
        justs.append(False)
    if options.index:
        header.append("Index")
        justs.append(False)
    rows = [header]
    
    for seq in sequences:
        row = [seq.string_name, str(seq.id)]
        if options.lengths:
            row.append(str(len(seq)))
        if options.index:
            row.append(str(seqs.index_for_id(seq.id)))
        rows.append(row)
    pprint_table(sys.stdout, rows, justs=justs)
    
if __name__ == "__main__":
    main()
