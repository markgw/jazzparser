#!/usr/bin/env ../../jazzshell
"""
This doesn't do much at the moment, but I'll probably want to add 
more to it.

"""
import sys, os

from optparse import OptionParser
from jazzparser.data.corpora import get_corpus_file, list_corpus_files
from jazzparser.data.corpora.temperley import DataSequence

def main():
    usage = "%prog [options] [filename]"
    description = "Inspect files from the Kostka-Payne corpus, which "\
        "is stored within this project."
    parser = OptionParser(description=description, usage=usage)
    parser.add_option("-l", "--list", dest="list", action="store_true", help="list all available files in the corpus")
    parser.add_option("-n", "--notes", dest="notes", action="store_true", help="count the number of notes in the given file")
    options, arguments = parser.parse_args()
    
    seq = None
    def _get_file():
        if len(arguments) < 1:
            print >>sys.stderr, "You must specify a corpus file"
            sys.exit(1)
        return DataSequence.from_file(arguments[0])
    
    if options.list:
        print "\n".join([os.sep.join(filename) for filename in list_corpus_files('kp')])
        
    if options.notes:
        if seq is None:
            seq = _get_file()
        notes = seq.get_events_by_type('TPCNote')
        print "%d" % len(notes)

if __name__ == "__main__":
    main()
