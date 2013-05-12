#!/usr/bin/env ../../jazzshell
import sys, os.path
from optparse import OptionParser
    
from jazzparser.data.dependencies import malt_tab_to_dependency_graphs

def main():
    usage = "%prog [options] <malt-tab>"
    description = "Prints dependency graphs read from a Malt-TAB file"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    if not len(arguments):
        print "You must specify a filename"
        sys.exit(1)
    
    # Read in the file
    f = open(arguments[0], 'r')
    data = f.read()
    f.close()
    
    # Interpret dependency graphs
    graphs = malt_tab_to_dependency_graphs(data)
    
    print "\n\n".join(str(g) for g in graphs)
    
if __name__ == "__main__":
    main()
