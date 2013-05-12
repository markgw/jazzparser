#!/usr/bin/env ../jazzshell
"""
Reads in a parse results file, drops all but the top n results and writes 
it out to another directory.

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

import sys, os.path, gc
from jazzparser.data.parsing import ParseResults
from optparse import OptionParser
    
def main():
    usage = "%prog [options] <res-file1> [<res-file2> ...]"
    description = "Reads in a parse results file, drops all but the top n "\
        "results and writes it out to another directory"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-n", dest="n", action="store", type="int", help="number of results to keep. Default: 1", default=1)
    parser.add_option("-o", "--output-dir", dest="output_dir", action="store", help="directory to put the output files in. Default: same as inputs, with altered filenames")
    parser.add_option("-d", "--strip-derivations", dest="strip_derivations", action="store_true", help="remove derivation traces from the results")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print "Specify at least one parse results file"
        sys.exit(1)
    
    n = options.n
    
    if options.output_dir is not None:
        output_dir = os.path.abspath(options.output_dir)
        filename_suffix = ""
    else:
        output_dir = None
        filename_suffix = "-top-%d" % n
    print "Outputing to: %s\n" % output_dir
    
    for filename in arguments:
        # Run the garbage collector each time round to get rid of the old 
        #  objects. For some reason it doesn't get run often enough otherwise
        gc.collect()
        
        filebase = os.path.basename(filename)
        # Decide where the output's going for this file
        if output_dir is None:
            file_outdir = os.path.dirname(os.path.abspath(filename))
        else:
            file_outdir = output_dir
        file_outname = os.path.join(file_outdir, 
                                    "%s%s" % (filebase, filename_suffix))
        
        print "Reading in: %s" % filebase
        # Read in the parse results file
        pres = ParseResults.from_file(filename)
        pres.parses = pres.parses[:n]
        if options.strip_derivations and pres.signs:
            # Remove derivation traces, if they were stored in the first place
            for prob,res in pres.parses:
                res.derivation_trace = None
        pres.save(file_outname)
        # Allow this to be garbage collected now
        pres = None
    
if __name__ == "__main__":
    main()
