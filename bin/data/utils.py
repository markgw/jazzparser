#!/usr/bin/env ../jazzshell
"""
Utilities for examining chord sequence data files.
With no arguments, just tries reading in the file to check it works.
"""
import sys, os
from optparse import OptionParser

from jazzparser.data.db_mirrors import SequenceIndex

def main():
    usage = "%prog <in-file> <command>"
    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--commands", dest="commands", action="store_true", help="show a list of available commands")
    options, arguments = parser.parse_args()
    
    commands = {
        'ids' : "output a space-separated list of the ids of all sequences",
        'count' : "output the total number of sequences",
        'help' : "show this help",
    }
    
    if options.commands:
        print "Available commands:\n%s" % \
            "\n".join(["%s  %s" % (format(cmd, " >10s"), help) for cmd,help in commands.items()])
        sys.exit(0)
        
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify an input data file"
        sys.exit(1)
    filename = os.path.abspath(arguments[0])
    
    # Read in the data file
    seqs = SequenceIndex.from_file(filename)
    
    if len(arguments) > 1:
        command = arguments[1].lower()
        if command not in commands:
            print >>sys.stderr, "%s is not a valid command. Use -c for a list of available commands."
        elif command == "ids":
            # Output a list of the ids of sequences
            print " ".join(["%s" % id for id in seqs.ids])
        elif command == "count":
            print len(seqs)
        else:
            print >>sys.stderr, "Oops, I've not defined this command"
    else:
        print "Successfully read in sequences"
    
if __name__ == "__main__":
    main()
