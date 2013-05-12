#!/usr/bin/env ../../jazzshell
"""Training of PCFG models.

This script used to be the sole way of manipulating and testing PCFG models, 
but much of this functionality has now been moved elsewhere.

Use this script to train models.

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

from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.data import holdout_partition
from jazzparser.utils.loggers import create_logger
from jazzparser.utils.options import ModuleOption, options_help_text
from jazzparser.grammar import get_grammar
from jazzparser.data.db_mirrors import SequenceIndex

def main():
    usage = "%prog [<options>] <model-name> <training-input>"
    description = "Training of PCFG models."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-p", "--partitions", dest="partitions", action="store", type="int", \
        help="Number of partitions to divide the data into. "\
            "For train, divides the input file, trains a model on each "\
            "partition's complement and appends partition number to "\
            "the model names. For del, appends partition numbers to model "\
            "names and deletes all the models. Recache does similarly. "\
            "Has no effect for parse.")
    parser.add_option('--opts', dest="training_opts", action="store", help="options to pass to the model trainer. Type '--opts help' for a list of options")
    parser.add_option("--debug", dest="debug", action="store_true", help="Output verbose logging information to stderr")
    parser.add_option("-g", "--grammar", dest="grammar", action="store", help="use the named grammar instead of the default.")
    options, arguments = parse_args_with_config(parser)
    
    if options.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARN
    # Create a logger for training
    logger = create_logger(log_level = log_level,
                  name = "training",
                  stderr = True)
    
    # Load a grammar
    grammar = get_grammar(options.grammar)
    # Get the pcfg model class for the formalism
    PcfgModel = grammar.formalism.PcfgModel
        
    # Parse the option string
    if options.training_opts is None:
        opts = {}
    elif options.training_opts.lower() == "help":
        print options_help_text(PcfgModel.TRAINING_OPTIONS, 
                                            intro="Training options for PCFGs")
        sys.exit(0)
    else:
        opts = ModuleOption.process_option_dict(
                    ModuleOption.process_option_string(options.training_opts),
                    PcfgModel.TRAINING_OPTIONS)
    
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
    
    if len(arguments) < 2:
        print >>sys.stderr, "Specify an input file to read sequence data from"
        sys.exit(1)
    # Read in the training data from the given file
    seqs = SequenceIndex.from_file(arguments[1])
    
    if options.partitions is not None:
        # Prepare each training partition
        datasets = holdout_partition(seqs.sequences, options.partitions)
    else:
        datasets = [seqs.sequences]
        
    for dataset,(parti,part_model) in zip(datasets,parts):
        # Train the named model on the sequence data
        model = PcfgModel.train(part_model, dataset, opts, grammar=grammar, 
                                logger=logger)
        model.save()
        print "Trained model", part_model
    
if __name__ == "__main__":
    main()
