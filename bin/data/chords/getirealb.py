#!/usr/bin/env ../../jazzshell
"""
Downloads iRealB chord sequences by scraping them from a webpage

"""
import sys, os
from optparse import OptionParser

from jazzparser.utils.web import get_irealb

def main():
    usage = "%prog [options]"
    description = "Downloads iRealB chord sequences by scraping them "\
                    "from a webpage"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-s", "--skip", dest="skip", default=0, type="int", 
                        help="Skip this number of irealb:// URLs before using "\
                            "one to get sequences")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print >>sys.stderr, "Specify the URL of a page to get sequences from"
        sys.exit(1)
    
    chords = get_irealb(arguments[0], skip=options.skip)

if __name__ == "__main__":
    main()
