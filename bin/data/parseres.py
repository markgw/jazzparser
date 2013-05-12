#!/usr/bin/env ../jazzshell
"""Script to read in a parse results file and output info about it.

"""
"""
============================== License ========================================
 Copyright (C) 2008, 2010-12 University of Edinburgh, Mark Granroth-Wilding
 
 This file is part of The Jazz Parser.
 
 The Jazz Parser is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 The Jazz Parser is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 
 You should have received a copy of the GNU General Public License
 along with The Jazz Parser.  If not, see <http://www.gnu.org/licenses/>.

============================ End license ======================================

"""
__author__ = "Mark Granroth-Wilding <mark.granroth-wilding@ed.ac.uk>" 

import sys, os.path, logging

from jazzparser.data.parsing import ParseResults

from optparse import OptionParser
    
def main():
    usage = "%prog [options] <seq-file>"
    description = "Parses a sequence from a sequence index file using the "\
        "annotations stored in the same file."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-r", "--results", dest="results", action="store_true", help="output the results list")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print "Specify a parse results file"
        sys.exit(1)
    
    pres = ParseResults.from_file(arguments[0])
    
    if hasattr(pres, "signs") and pres.signs:
        print "Results stored as signs"
    else:
        print "Results stored as logical forms only"
        
    if pres.gold_parse is None:
        print "No gold parse stored"
    else:
        print "Gold parse available"
    
    if pres.gold_sequence is None:
        print "No gold sequence stored"
    else:
        print "Gold sequence available"
    
    if options.results:
        print
        for i,(prob,res) in enumerate(pres.parses):
            print "Result %d, probability %s" % (i,prob)
            print res
    
if __name__ == "__main__":
    main()
