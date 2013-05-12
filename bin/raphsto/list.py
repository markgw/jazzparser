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
from jazzparser.misc.raphsto import RaphstoHmm, MODEL_TYPES

def main():
    usage = "%prog [options] <model-name>"
    description = "Outputs a list of trained models"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-t', '--type', dest="type", action="store", help="model type ('help' to list model types)")
    options, arguments = parser.parse_args()
    
    if options.type is not None:
        if options.type not in MODEL_TYPES:
            if options.type.lower() != "help":
                print "No model type '%s'. Available model types:"
            print "\n".join(MODEL_TYPES.keys())
            sys.exit(0)
        else:
            cls = MODEL_TYPES[options.type]
    else:
        cls = RaphstoHmm
    models = cls.list_models()
    if len(models):
        print "\n".join(models)
    
if __name__ == "__main__":
    main()
