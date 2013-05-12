#!/usr/bin/env ../jazzshell
import sys, os.path

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.data.midi import SequenceMidiAlignment

from midi import read_midifile, write_midifile
from optparse import OptionParser
    
def main():
    usage = "%prog [options] <seq-file> <index>"
    description = "Outputs the details of a chord sequence from a "\
        "sequence index file to stdout."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("--categories", "-c", dest="categories", action="store_true", help="include category annotations")
    parser.add_option("--coordinations", "-o", dest="coordinations", action="store_true", help="include coordination annotations")
    parser.add_option("--meta", "-m", dest="meta", action="store_true", help="output sequence meta data")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 2:
        print "You must specify a sequence file and index"
        sys.exit(1)
        
    index = int(arguments[1])
    # Get the chord sequence
    seq = SequenceIndex.from_file(arguments[0]).sequence_by_index(index)
    
    # Show the song name
    print "Chords for '%s'" % seq.string_name
    
    if options.meta:
        print "Main key:    %s" % seq.key
        print "Bar length:  %d" % seq.bar_length
        print "Notes:\n%s\n\n" % seq.notes
    
    for i,chord in enumerate(seq.iterator()):
        output = "%d\t%s\t%d" % (i,chord,chord.duration)
        if options.categories:
            output += "\t%s" % chord.category
        if options.coordinations:
            ti = chord.treeinfo
            if ti.coord_resolved and ti.coord_unresolved:
                output += "\t)("
            elif ti.coord_resolved:
                output += "\t)"
            elif ti.coord_unresolved:
                output += "\t("
        print output
    
if __name__ == "__main__":
    main()
