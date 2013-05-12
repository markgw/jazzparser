#!/usr/bin/env ../../jazzshell
"""
Downloads the Vanilla Book by scraping it from the web

"""
import sys, os, string
from optparse import OptionParser

from jazzparser.utils.web import get_vanilla_book

def main():
    usage = "%prog [options]"
    description = "Downloads the Vanilla Book from "\
        "http://www.ralphpatt.com/Song.html"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    book = get_vanilla_book()

if __name__ == "__main__":
    main()
