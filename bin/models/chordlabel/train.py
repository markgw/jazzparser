#!/usr/bin/env ../../jazzshell
"""
Trains a chord labeling model from sequence data.

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
from jazzparser.utils.data import holdout_partition
from jazzparser.utils.options import ModuleOption, options_help_text
from jazzparser.utils.config import parse_args_with_config
from jazzparser.data.input import command_line_input, get_input_type_names, \
                        MidiTaggerTrainingBulkInput
from jazzparser.utils.loggers import create_logger

from jazzparser.misc.chordlabel import HPChordLabeler

def main():
    usage = "%prog [options] <model_name> <in-file>"
    description = "Trains a chord labeling model using the given "\
        "input data. The data file may be a stored SequenceIndex file, or "\
        "any other type of bulk data file."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-p', '--partitions', dest="partitions", action="store", type="int", help="train a number of partitions of the given data. Trains a model on the complement of each partition, so it can be tested on the partition. The models will be named <NAME>n, where <NAME> is the model name and n the partition number.")
    parser.add_option('--opts', dest="training_opts", action="append", help="options to pass to the model trainer. Type '--opts help' for a list of options for a particular model type.")
    # File input options
    parser.add_option("--filetype", "--ft", dest="filetype", action="store", help="select the file type for the input file. Same filetypes as jazzparser", default='bulk-db')
    parser.add_option("--file-options", "--fopt", dest="file_options", action="store", help="options for the input file. Type '--fopt help', using '--ft <type>' to select file type, for a list of available options.")
    # Logging output
    parser.add_option('--log', dest="log", action="store", help="file to output training logs to. Specify a base filename; <modelname>.log will be added to the end")
    options, arguments = parse_args_with_config(parser)
    
    grammar = Grammar()
    
    # Handle any training options that were given on the command line
    if options.training_opts is None:
        training_opts = {}
    elif "help" in [opt.lower() for opt in options.training_opts]:
        print options_help_text(HPChordLabeler.TRAINING_OPTIONS, intro="Training options:")
        sys.exit(0)
    else:
        training_opts = ModuleOption.process_option_string(options.training_opts)
        
    if len(arguments) < 2:
        print >>sys.stderr, "You must specify a model name and an input data file as arguments"
        sys.exit(1)
    filename = os.path.abspath(arguments[1])
    model_name = arguments[0]
    
    # Load the sequence data
    # Only allow bulk types
    input_data = command_line_input(filename=filename, 
                                    filetype=options.filetype, 
                                    options=options.file_options,
                                    allowed_types=get_input_type_names(single=False, bulk=True))
    
    # Only partition the chord data, not the MIDI data
    if options.partitions is not None and not \
            (isinstance(input_data, MidiTaggerTrainingBulkInput) and \
             input_data.chords is not None):
        print >>sys.stderr, "Can only partition chord data and no chord data "\
            "was supplied"
        sys.exit(1)
    
    if options.partitions:
        # The input includes chord training data
        parts = input_data.chords.get_partitions(options.partitions)[1]
        models = [("%s%d" % (model_name,num),chord_data) \
            for num,chord_data in enumerate(parts)]
    else:
        models = [(model_name,None)]
    
    for part_name,chord_data in models:
        if options.log is not None:
            # Prepare a logger
            logfile = "%s%s.log" % (options.log, part_name)
            print "Logging output to file %s" % logfile
            logger = create_logger(filename=logfile)
        else:
            logger = None
        
        # Create a fresh model with this name
        model = HPChordLabeler.train(input_data, part_name, 
                                     logger=logger, 
                                     options=training_opts,
                                     chord_data=chord_data)
        print "Trained model %s" % (part_name)

if __name__ == "__main__":
    main()
