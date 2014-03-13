#!/usr/bin/env ../jazzshell
import sys, os.path

from jazzparser.data.db_mirrors import SequenceIndex, annotation_to_lexicon_name
from jazzparser.data.midi import SequenceMidiAlignment
from jazzparser.utils.tableprint import pprint_table

from optparse import OptionParser
    
def main():
    usage = "%prog [options] <seq-file>"
    description = "Outputs the details of all chord sequences from a "\
        "sequence index file to stdout. This is for getting a "\
        "(relatively) human-readable form of the data"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("--categories", "-c", dest="categories", action="store_true", help="include category annotations")
    parser.add_option("--coordinations", "-o", dest="coordinations", action="store_true", help="include coordination annotations")
    parser.add_option("--meta", "-m", dest="meta", action="store_true", help="output sequence meta data")
    parser.add_option("--no-map", "-n", dest="no_map", action="store_true", help="don't apply a mapping from the names in the corpus to those used in the paper")
    parser.add_option("--all", "-a", dest="all", action="store_true", help="output everything")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print "You must specify a sequence file"
        sys.exit(1)
       
    # Get the chord sequence
    seqs = SequenceIndex.from_file(arguments[0])
    
    # Show the song name
    for seq in seqs:
        print "Chords for '%s'" % seq.string_name
        
        if options.meta or options.all:
            print "Main key:    %s" % seq.key
            print "Bar length:  %d" % seq.bar_length
        
        # Put together a table of chords plus annotations (if requested)
        data = [[ str(chord) for chord in seq ], 
                [ str(chord.duration) for chord in seq ]]
        if options.categories or options.all:
            if options.no_map:
                # Don't apply any mapping to the category names
                data.append([ chord.category for chord in seq ])
            else:
                # Map the names to those used in the paper/thesis
                data.append([ annotation_to_lexicon_name(chord.category) for chord in seq ])
        if options.coordinations or options.all:
            coords = []
            for chord in seq:
                ti = chord.treeinfo
                if ti.coord_resolved and ti.coord_unresolved:
                    coords.append(")(")
                elif ti.coord_resolved:
                    coords.append(")")
                elif ti.coord_unresolved:
                    coords.append("(")
                else:
                    coords.append("")
            data.append(coords)
        pprint_table(sys.stdout, data, default_just=True)
        print
    
if __name__ == "__main__":
    main()
