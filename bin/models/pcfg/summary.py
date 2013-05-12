#!/usr/bin/env ../../jazzshell
"""Prints out a summary of model counts.

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

import sys, math, os, shutil, logging
from optparse import OptionParser

from jazzparser.grammar import get_grammar

def main():
    usage = "%prog <model-name> [options]"
    description = "Outputs a summary of a named model (counts, etc)"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-g", "--grammar", dest="grammar", action="store", \
                        help="use the named grammar instead of the default.")
    options, arguments = parser.parse_args()
    
    grammar = get_grammar(options.grammar)
    PcfgModel = grammar.formalism.PcfgModel
    
    if len(arguments) == 0:
        print >>sys.stderr, "Specify a model name"
        models = PcfgModel.list_models()
        print >>sys.stderr, "Available models: %s" % ", ".join(models)
        sys.exit(1)
    model_name = arguments[0]
    # Load the trained model
    model = PcfgModel.load_model(model_name)
    
    print model.description()
    
if __name__ == "__main__":
    main()
