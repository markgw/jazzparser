#!/usr/bin/env ../jazzshell
"""
Train models for my implementation of Raphael and Stoddard's algorithm 
for chord labelling.

Trains models using chord sequences from midi files.

@todo: document training data input format

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

import sys, os
from datetime import datetime
from optparse import OptionParser

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.utils.data import holdout_partition
from jazzparser.utils.options import ModuleOption, options_help_text
from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.loggers import create_logger
from jazzparser.misc.raphsto import MODEL_TYPES, constants
from jazzparser.misc.raphsto.train import RaphstoBaumWelchTrainer
from jazzparser.misc.raphsto.midi import InputSourceFile

def main():
    usage = "%prog [options] <model_name> <input-file>"
    description = "Trains a model for the RaphSto chord labelling "\
        "algorithm on a file that contains a list of midi files with "\
        "training options"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-p', '--partitions', dest="partitions", action="store", type="int", help="train a number of partitions of the given data. Trains a model on the complement of each partition, so it can be tested on the partition. The models will be named <NAME>n, where <NAME> is the model name and n the partition number.")
    parser.add_option('--opts', dest="opts", action="store", help="options to pass to the model trainer. Type '--opts help' for a list of options for a particular model type.")
    parser.add_option('--proc', '--processes', dest="processes", action="store", type="int", help="number of parallel processes to spawn for the training. Use -1 to spawn one per training sequence (after splitting: see split_length)", default=1)
    parser.add_option('--max-length', dest="max_length", action="store", type="int", help="limits the length of the training midi sequences in chunks")
    parser.add_option('--split-length', dest="split_length", action="store", type="int", help="limits the length of the training midi sequences in chunks, but instead of throwing away everything after the first N chunks, splits it off as if it were starting a new sequence. This is good for multiprocessing, since many short sequences can be multitasked, whilst few long ones cannot")
    parser.add_option('--min-length', dest="min_length", action="store", type="int", help="ignores any sequences under this number of chunks. This is useful with --split-length, which can leave very short sequences from the end of a split sequence")
    parser.add_option('--progress-out', dest="progress_out", action="store", help="output logging info to a file instead of the command line")
    parser.add_option('--init-model', dest="init_model", action="store", help="initialize the model using parameters from an already trained model")
    parser.add_option('--init-ctrans', dest="init_ctrans", action="store", help="initialize the chord transition distribution using these parameters. Comma-separated list of params given as C0->C1-P, where C0 and C1 are chords (I, II, etc) and P is a float probability")
    parser.add_option('--chord-set', dest="chord_set", action="store", help="use a chord set other than the default. Use value 'help' to see a list. Has no effect in combination with --init-model, since the old model's chord set will be used")
    parser.add_option('-m', '--model-type', dest="model_type", action="store", help="select a model type: one of %s (default: standard)" % ", ".join(mt for mt in MODEL_TYPES.keys()), default="standard")
    options, arguments = parse_args_with_config(parser)
    
    if options.opts is not None and options.opts == "help":
        print options_help_text(RaphstoBaumWelchTrainer.OPTIONS, intro="Training options for Raphael and Stoddard HMMs")
        sys.exit(0)
    opts = ModuleOption.process_option_string(options.opts)
    
    if len(arguments) < 2:
        print >>sys.stderr, "You must specify a model name and an input data file as arguments"
        sys.exit(1)
    filename = os.path.abspath(arguments[1])
    model_name = arguments[0]
    
    print >>sys.stderr, "Raphsto training beginning at %s" % datetime.now().isoformat(' ')
    # Create a logger to output the progress of the training to stdout or a file
    if options.progress_out is not None:
        stdout = False
        logfile = options.progress_out
        print >>sys.stderr, "Outputing logging info to %s" % logfile
    else:
        stdout = True
        logfile = None
        print >>sys.stderr, "Outputing logging to stdout"
    logger = create_logger(name="raphsto_train", filename=logfile, stdout=stdout)
    logger.info("Raphael and Stoddard HMM model training")
        
    if options.model_type not in MODEL_TYPES:
        print >>sys.stderr, "Model type must be one of: %s" % ", ".join(mt for mt in MODEL_TYPES)
        sys.exit(1)
    model_cls = MODEL_TYPES[options.model_type]
    
    if options.chord_set == "help":
        print "Available chord sets: %s" % ", ".join(constants.CHORD_SETS.keys())
        sys.exit(0)
    elif options.chord_set is not None:
        # Check this chord set exists
        if options.chord_set not in constants.CHORD_SETS:
            print >>sys.stderr, "Chord set '%s' does not exist" % options.chord_set
            sys.exit(1)
        else:
            logger.info("Using chord set '%s'" % options.chord_set)
    
    
    # Read in the training data
    midis = InputSourceFile(filename)
    handlers = midis.get_handlers()
    logger.info("Reading in %d midi files..." % len(midis.inputs))
    training_data = []
    for i,mh in enumerate(handlers):
        logger.info("%s: %s" % (i,midis.inputs[i][0]))
        emissions = mh.get_emission_stream()[0]
        if options.max_length is not None and len(emissions) > options.max_length:
            logger.info("Truncating file %d to %d chunks (was %d)" % \
                                    (i,options.max_length,len(emissions)))
            emissions = emissions[:options.max_length]
        if options.split_length is not None:
            logger.info("Splitting sequence %d into sequence no longer "\
                                "than %d chunks" % (i,options.split_length))
            # Split up the sequence if it's too long
            while len(emissions) > options.split_length:
                training_data.append(emissions[:options.split_length])
                emissions = emissions[options.split_length:]
        training_data.append(emissions)
    
    if options.min_length is not None:
        # Make sure there are no sequences under the minimum length
        # Just throw away any that are
        before_chuck = len(training_data)
        training_data = [seq for seq in training_data if len(seq) >= options.min_length]
        if len(training_data) != before_chuck:
            logger.info("Threw away %d short sequences (below %d chunks)" % \
                    ((before_chuck-len(training_data)), options.min_length))
    
    logger.info("Training on %d sequences. Lengths: %s" % \
                    (len(training_data), 
                     ", ".join(str(len(seq)) for seq in training_data)))
    
    if options.partitions is not None:
        parts = holdout_partition(training_data, options.partitions)
        models = [("%s%d" % (model_name,num),data) for num,data in enumerate(parts)]
    else:
        models = [(model_name,training_data)]
        
    # Number of processes to use
    if options.processes == -1:
        # Special value: means number of training sequences (one process per sequence)
        processes = len(training_data)
    else:
        processes = options.processes
    
    for part_name,data in models:
        # Instantiate a fresh model with this name
        logger.info("Training model '%s' on %d midis" % (part_name, len(data)))
        if options.init_model is not None:
            logger.info("Initializing using parameters from model '%s'" % \
                options.init_model)
            # Load an already trained model as initialization
            model = model_cls.initialize_existing_model(options.init_model, \
                model_name=part_name)
        else:
            # TODO: make these probs an option
            ctype_params = (0.5, 0.3, 0.2)
            logger.info("Initializing to naive chord types using parameters: "\
                "%s, %s, %s" % ctype_params)
            init_kwargs = { 'model_name' : part_name }
            if options.chord_set is not None:
                # Specify a chord set for the model
                init_kwargs['chord_set'] = options.chord_set
            model = model_cls.initialize_chord_types(ctype_params, **init_kwargs)
            
            # Initialize the chord transition probabilities if given
            if options.init_ctrans is not None:
                logger.info("Initializing chord transition distribution to %s" \
                    % options.init_ctrans)
                model.set_chord_transition_probabilities(options.init_ctrans)
        # Retrain it with the loaded data
        trainer = model_cls.get_trainer()(model, options=opts)
        trainer.train(data, logger=logger, processes=processes, save_intermediate=True)
    print >>sys.stderr, "Training terminating at %s" % datetime.now().isoformat(' ')
    
if __name__ == "__main__":
    main()
