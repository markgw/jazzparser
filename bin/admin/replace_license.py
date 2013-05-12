#!/usr/bin/python
import sys, os
from optparse import OptionParser

LIC_START = "============================== License ========================================\n"
LIC_END = "\n============================ End license ======================================"

def main():
    parser = OptionParser()
    parser.add_option("-r", "--real", dest="real", action="store_true", help="do the replacement. By default, just outputs what it would do (for dry-run testing)")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 2:
        print >>sys.stderr, "You must specify a file to operate on and a file "\
            "with the new license content"
        sys.exit(1)
    
    # Read in the full file
    file = open(arguments[0], 'r')
    input = file.read()
    file.close()
    
    # Read in the new license
    f = open(arguments[1], 'r')
    new_lic = f.read()
    f.close()
    
    # Look for the license
    start = input.find(LIC_START)
    if start == -1:
        print >>sys.stderr, "No license found in %s" % arguments[0]
        sys.exit(1)
    start += len(LIC_START)
        
    # Look for the end of it
    end = input.find(LIC_END)
    if end == -1:
        print >>sys.stderr, "Found license start, but no end in %s" % arguments[0]
        sys.exit(1)
    
    if options.real:
        input = input[:start] + new_lic + input[end:]
        file = open(arguments[0], 'w')
        file.write(input)
        file.close()
    else:
        print "Would replace license in %s" % arguments[0]
    
if __name__ == "__main__":
    main()
