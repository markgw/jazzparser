#!/usr/bin/env ../jazzshell
import sys, os.path
from optparse import OptionParser

from jazzparser.utils.web import refresh_the_jazz_page_cache
    
def main():
    usage = "%prog"
    description = "Rebuild the cache of The Jazz Page, used by getmidi "\
        "to get midi files from thejazzpage.de"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    print "Rebuilding cache of MIDI files from The Jazz Page"
    refresh_the_jazz_page_cache()
    
if __name__ == "__main__":
    main()
