#!/usr/bin/python
import sys, os
from optparse import OptionParser

def main():
    parser = OptionParser()
    parser.add_option("-r", "--real", dest="real", action="store_true", help="do the replacement. By default, just outputs what it would do (for dry-run testing)")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 3:
        print >>sys.stderr, "You must specify a file to operate on, a "\
            "file containing authors to replace and a new author text"
        sys.exit(1)
    
    # Read in the full file
    file = open(arguments[0], 'r')
    input = file.read()
    file.close()
    
    f = open(arguments[1], 'r')
    old_authors = f.readlines()
    f.close()
    old_authors = [s.strip("\n") for s in old_authors]
    old_authors = [s for s in old_authors if len(s)]
    
    new_author = " ".join(arguments[2:])
    
    # Look for the license
    author_intro = "\n__author__ = \""
    start = input.find(author_intro)
    if start == -1:
        print >>sys.stderr, "No author found in %s" % arguments[0]
        sys.exit(1)
    author_start = start + len(author_intro)
    # Find matching quote
    author_end = input.find("\"", author_start)
    got_author = input[author_start:author_end]
    
    # Check this matches the author we expect to see
    if got_author not in old_authors:
        print >>sys.stderr, "Not replacing author \"%s\"" % got_author
        sys.exit(1)
        
    if options.real:
        input = input[:author_start] + new_author + input[author_end:]
        file = open(arguments[0], 'w')
        file.write(input)
        file.close()
    else:
        print "Would replace author in %s" % arguments[0]
    
if __name__ == "__main__":
    main()
