#!/usr/bin/env ../jazzshell
"""
Outputs information about a trained model.

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

import sys
from optparse import OptionParser
from jazzparser.misc.raphsto import RaphstoHmm

def main():
    usage = "%prog [options] <model-name>"
    description = "Outputs or stores custom description for a trained Raphsto model"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-s', '--store', dest="store", action="store_true", help="store a new description from stdin")
    parser.add_option('--silent', dest="silent", action="store_true", help="don't output anything (overridden by --store)")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print >>sys.stderr, "You must specify a model name as the first argument"
        sys.exit(1)
    model_name = arguments[0]
    
    # Load the model
    model = RaphstoHmm.load_model(model_name)
    
    if options.store:
        if not options.silent:
            print >>sys.stderr, "Reading new description from stderr"
        # Read from stdin
        desc = "".join(ln for ln in sys.stdin)
        # Use this as the model description
        model.description = desc
        model.save()
    else:
        # Output the description
        if len(model.description):
            print model.description,
    
if __name__ == "__main__":
    main()
