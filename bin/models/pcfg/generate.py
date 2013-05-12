#!/usr/bin/env ../../jazzshell
"""Generate chord sequences from a PCFG model.

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

import sys, logging
from optparse import OptionParser

from jazzparser.grammar import get_grammar
from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.loggers import create_plain_stderr_logger

def main():
    usage = "%prog <model-name>"
    description = "Generate chord sequences from a PCFG model"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-g", "--grammar", dest="grammar", action="store", \
                        help="use the named grammar instead of the default.")
    parser.add_option("-d", "--debug", dest="debug", action="store_true", \
                        help="output debugging information during generation")
    options, arguments = parse_args_with_config(parser)
    
    if options.debug:
        logger = create_plain_stderr_logger(log_level=logging.DEBUG)
    else:
        logger = create_plain_stderr_logger(log_level=logging.WARN)
    
    if len(arguments) < 1:
        print "Specify a model name"
        sys.exit(1)
    model_name = arguments[0]
    
    grammar = get_grammar(options.grammar)
    PcfgModel = grammar.formalism.PcfgModel
    # Load the trained model
    model = PcfgModel.load_model(model_name)
    
    sequence = model.generate(logger=logger)
    if sequence is None:
        print "Model did not generate a sequence"
    else:
        print sequence
    
if __name__ == "__main__":
    main()
