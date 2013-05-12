#!/usr/bin/env ../jazzshell
"""
Trains one of the backoff builder models from sequence data.

This is a clone of the models/train.py script for tagger models.

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

import sys, math, os
from optparse import OptionParser

from jazzparser.taggers.models import ModelTagger
from jazzparser.utils.data import holdout_partition
from jazzparser.utils.options import ModuleOption, options_help_text
from jazzparser.utils.config import parse_args_with_config
from jazzparser.backoff.loader import get_backoff_builder
from jazzparser.data.input import command_line_input

def main():
    usage = "%prog [options] <model-type> <model_name> <in-file>"
    description = "Trains a backoff builder model using the given "\
        "input data. Specify a model type (ngram, etc) and a name to "\
        "identify it. The data file should be a stored SequenceIndex file."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-p', '--partitions', dest="partitions", action="store", type="int", help="train a number of partitions of the given data. Trains a model on the complement of each partition, so it can be tested on the partition. The models will be named <NAME>n, where <NAME> is the model name and n the partition number.")
    parser.add_option('--opts', dest="training_opts", action="store", help="options to pass to the model trainer. Type '--opts help' for a list of options for a particular model type.")
    # File input options
    parser.add_option("--filetype", "--ft", dest="filetype", action="store", help="select the file type for the input file. Same filetypes as jazzparser", default='bulk-db')
    parser.add_option("--file-options", "--fopt", dest="file_options", action="store", help="options for the input file. Type '--fopt help', using '--ft <type>' to select file type, for a list of available options.")
    options, arguments = parse_args_with_config(parser)
    
    if len(arguments) < 3:
        print >>sys.stderr, "You must specify a model type, a model name and an input data file as arguments"
        sys.exit(1)
    filename = os.path.abspath(arguments[2])
    model_type = arguments[0]
    model_name = arguments[1]
    
    builder_cls = get_backoff_builder(model_type)
    model_cls = builder_cls.MODEL_CLASS
    
    # Load the sequence data from a dbinput file
    input_data = command_line_input(filename=filename, 
                                    filetype=options.filetype, 
                                    options=options.file_options,
                                    allowed_types=['bulk-db', 'bulk-db-annotated'])
    
    # Handle any training options that were given on the command line
    if options.training_opts is None:
        training_opts = {}
    elif options.training_opts.lower() == "help":
        print options_help_text(model_cls.TRAINING_OPTIONS, intro="Training options for %s" % model_cls.__name__)
        sys.exit(0)
    else:
        training_opts = ModuleOption.process_option_dict(
                            ModuleOption.process_option_string(options.training_opts), 
                            model_cls.TRAINING_OPTIONS)
        
    if options.partitions is not None:
        parts = holdout_partition(input_data, options.partitions)
        models = [(builder_cls.partition_model_name(model_name,num),seqs) for \
                        num,seqs in enumerate(parts)]
    else:
        models = [(model_name,input_data)]
    
    for part_name,seqs in models:
        # Instantiate a fresh model with this name
        model = model_cls(part_name, options=training_opts)
        # Train it with the loaded data
        model.train(seqs)
        model.save()
        print "Trained model %s" % (part_name)
    
if __name__ == "__main__":
    main()
