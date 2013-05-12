#!/usr/bin/env ../../jazzshell
"""Delete a PCFG model

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

import sys, os, logging
from optparse import OptionParser

from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.data import holdout_partition
from jazzparser.grammar import get_grammar

def main():
    usage = "%prog [<options>] <model-name>"
    description = "Delete a PCFG model"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-p", "--partitions", dest="partitions", action="store", type="int", \
                    help="Number of partitions the model is divided into")
    parser.add_option("-g", "--grammar", dest="grammar", action="store", help="use the named grammar instead of the default.")
    options, arguments = parse_args_with_config(parser)
    
    # Load a grammar
    grammar = get_grammar(options.grammar)
    # Get the pcfg model class for the formalism
    PcfgModel = grammar.formalism.PcfgModel
        
    if len(arguments) == 0:
        print >>sys.stderr, "Specify a model name"
        models = PcfgModel.list_models()
        print >>sys.stderr, "Available models: %s" % ", ".join(models)
        sys.exit(1)
    model_name = arguments[0]
    print "Model base name:", model_name
    
    if options.partitions is not None:
        parts = [(i, "%s%d" % (model_name, i)) for i in range(options.partitions)]
    else:
        parts = [(None, model_name)]

    # First check all the models exist
    for parti,part_model in parts:
        if part_model not in PcfgModel.list_models():
            print "The model '%s' does not exist" % part_model
            sys.exit(1)
    
    # Now delete them one by one
    for parti,part_model in parts:
        # Load the model
        model = PcfgModel.load_model(part_model)
        model.delete()
        print "Removed model: %s" % part_model
    
if __name__ == "__main__":
    main()
