#!/usr/bin/env ../jazzshell
"""
Trains one of the supertagger models from sequence data.
Only applicable to some types of models (see TRAINABLE_MODELS).

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

from jazzparser.utils.base import load_class
from jazzparser.grammar import Grammar
from jazzparser.taggers import TAGGERS
from jazzparser.taggers.models import ModelTagger
from jazzparser.taggers.loader import get_tagger
from jazzparser.utils.data import holdout_partition
from jazzparser.utils.options import ModuleOption, options_help_text
from jazzparser.utils.config import parse_args_with_config
from jazzparser.data.input import command_line_input, get_input_type_names
from jazzparser.utils.loggers import create_logger

"""
Only certain types of models can be trained using this script. They 
are listed here so that we can check we only try to train them.
If you create a new tagger, it's best to give it a model that uses 
the TaggerModel interface if possible. You can then add it to this 
list and train it using this script.

"""
TRAINABLE_MODELS = [
    'baseline1',
    'baseline2',
    'baseline3',
    'ngram',
    'chordclass',
    'ngram-multi',
    'candc',
]

def main():
    usage = "%prog [options] <model-type> <model_name> <in-file>"
    description = "Trains a supertagging model using the given "\
        "input data. Specify a model type (baseline1, etc) and a name to "\
        "identify it. The data file may be a stored SequenceIndex file, or "\
        "any other type of bulk data file. "\
        "This can only be used with the follow types of models: %s" % ", ".join(TRAINABLE_MODELS)
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-p', '--partitions', dest="partitions", action="store", type="int", help="train a number of partitions of the given data. Trains a model on the complement of each partition, so it can be tested on the partition. The models will be named <NAME>n, where <NAME> is the model name and n the partition number.")
    parser.add_option('--opts', dest="training_opts", action="store", help="options to pass to the model trainer. Type '--opts help' for a list of options for a particular model type.")
    # File input options
    parser.add_option("--filetype", "--ft", dest="filetype", action="store", help="select the file type for the input file. Same filetypes as jazzparser", default='bulk-db')
    parser.add_option("--file-options", "--fopt", dest="file_options", action="store", help="options for the input file. Type '--fopt help', using '--ft <type>' to select file type, for a list of available options.")
    # Logging output
    parser.add_option('--log', dest="log", action="store", help="file to output training logs to. Specify a base filename; <modelname>.log will be added to the end")
    options, arguments = parse_args_with_config(parser)
    
    grammar = Grammar()
    
    # Get the model type first: we might not need the other args
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify a model type, a model name and an input data file as arguments"
    model_type = arguments[0]
    
    if model_type not in TRAINABLE_MODELS:
        print >>sys.stderr, "'%s' is not a valid model type. Available taggers are: %s" % \
            (model_type, ", ".join(TRAINABLE_MODELS))
        sys.exit(1)
    if model_type not in TAGGERS:
        print >>sys.stderr, "'%s' isn't a registered model type. Check that "\
            "the name in TRAINABLE_MODELS is correct" % model_type
        sys.exit(1)
    
    tagger_cls = get_tagger(model_type)
    if not issubclass(tagger_cls, ModelTagger):
        print >>sys.stderr, "'%s' tagger cannot be trained with this script. Only model taggers can be." % (tagger_cls.__name__)
        sys.exit(1)
    model_cls = tagger_cls.MODEL_CLASS
    
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
    
    # Get the rest of the args
    if len(arguments) < 3:
        print >>sys.stderr, "You must specify a model type, a model name and an input data file as arguments"
        sys.exit(1)
    filename = os.path.abspath(arguments[2])
    model_name = arguments[1]

    # Load the sequence data
    # Only allow bulk types
    input_data = command_line_input(filename=filename, 
                                    filetype=options.filetype, 
                                    options=options.file_options,
                                    allowed_types=get_input_type_names(single=False, bulk=True))
    
    if options.partitions is not None and options.partitions > 1:
        parts = input_data.get_partitions(options.partitions)[1]
        models = [(tagger_cls.partition_model_name(model_name,num),seqs) for \
                                                num,seqs in enumerate(parts)]
    else:
        models = [(model_name,input_data)]
    
    for part_name,seqs in models:
        # Instantiate a fresh model with this name
        model = model_cls(part_name, options=training_opts)
        if options.log is not None:
            # Prepare a logger
            logfile = "%s%s.log" % (options.log, part_name)
            print "Logging output to file %s" % logfile
            logger = create_logger(filename=logfile)
        else:
            logger = None
            
        # Train the model with the loaded data
        model.train(seqs, logger=logger)
        model.save()
        print "Trained model %s" % (part_name)
    
if __name__ == "__main__":
    main()
