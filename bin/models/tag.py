#!/usr/bin/env ../jazzshell
"""Runs just a tagger and outputs the categories it assigns to the input.

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

import sys, os, traceback, readline
from optparse import OptionParser
from itertools import count, imap

from jazzparser import settings
from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.options import ModuleOption, ModuleOptionError
from jazzparser.utils.loggers import create_plain_stderr_logger, create_logger
from jazzparser.utils.interface import input_iterator
from jazzparser.grammar import get_grammar
from jazzparser.taggers import TAGGERS
from jazzparser.taggers.loader import get_tagger
from jazzparser.data.input import command_line_input, ChordInput, is_bulk_type

def main():
    usage = "%prog [<options>]"
    description = "Runs a supertagger from the Jazz Parser to tag some input "\
        "but just outputs the results, rather than continuing to parse."
    optparser = OptionParser(usage=usage, description=description)
    
    # Tagger options
    optparser.add_option("-t", "--tagger", "--supertagger", dest="supertagger", action="store", help="run the parser using the named supertagger. Use '-t help' to see the list of available taggers. Default: %s" % settings.DEFAULT_SUPERTAGGER, default=settings.DEFAULT_SUPERTAGGER)
    optparser.add_option("--topt", "--tagger-options", dest="topts", action="append", help="specify options for the tagger. Type '--topt help', using '-u <name>' to select a tagger module, to get a list of options.")
    # Commonly-used misc
    optparser.add_option("-g", "--grammar", dest="grammar", action="store", help="use the named grammar instead of the default.")
    # File input options
    optparser.add_option("--file", "-f", dest="file", action="store", help="use a file to get parser input from. Use --filetype to specify the type of the file.")
    optparser.add_option("--filetype", "--ft", dest="filetype", action="store", help="select the file type for the input file (--file). Use '--filetype help' for a list of available types. Default: chords", default='chords')
    optparser.add_option("--file-options", "--fopt", dest="file_options", action="store", help="options for the input file (--file). Type '--fopt help', using '--ft <type>' to select file type, for a list of available options.")
    # Misc options
    optparser.add_option("-v", "--debug", dest="debug", action="store_true", help="output verbose debugging information.")
    optparser.add_option("-i", "--interactive", dest="interactive", action="store_true", help="instead of just outputing all tags in one go, wait for user input between each iteration of adaptive supertagging")
    # Logging options
    optparser.add_option("--logger", dest="logger", action="store", help="directory to put parser logging in. A filename based on an identifier for each individual input will be appended.")
    # Read in command line options and args
    options, clinput = parse_args_with_config(optparser)
    
    ########################### Option processing ####################
    if options.logger:
        # Directory
        parse_logger_dir = options.logger
        check_directory(parse_logger_dir)
    else:
        parse_logger_dir = None
    
    ######## Grammar ########
    # Read in the grammar
    grammar = get_grammar(options.grammar)
        
    ######## Supertagger ########
    # Load the supertagger requested
    if options.supertagger.lower() == "help":
        print "Available taggers are: %s" % ", ".join(TAGGERS)
        return 0
    try:
        tagger_cls = get_tagger(options.supertagger)
    except TaggerLoadError:
        logger.error("The tagger '%s' could not be loaded. Possible "\
            "taggers are: %s" % (options.supertagger, ", ".join(TAGGERS)))
        return 1
        
    # Get supertagger options before initializing the tagger
    if options.topts is not None:
        toptstr = options.topts
        if "help" in [s.strip().lower() for s in toptstr]:
            # Output this tagger's option help
            from jazzparser.utils.options import options_help_text
            print options_help_text(tagger_cls.TAGGER_OPTIONS, intro="Available options for selected tagger")
            return 0
        toptstr = ":".join(toptstr)
    else:
        toptstr = ""
    topts = ModuleOption.process_option_string(toptstr)
    # Check that the options are valid
    try:
        tagger_cls.check_options(topts)
    except ModuleOptionError, err:
        print "Problem with tagger options (--topt): %s" % err
        return 1
    
    ############################ Input processing #####################
    stdinput = False
    # Try getting a file from the command-line options
    input_data = command_line_input(filename=options.file, 
                                    filetype=options.filetype,
                                    options=options.file_options)
    # Record progress in this for helpful output
    if input_data is None:
        # No input file: process command line input
        input_string = " ".join(clinput)
        input_list = [input_string]
        name_getter = iter(["commandline"])
        # Take input from stdin if nothing else is given
        if len(input_string) == 0:
            stdinput = True
            # Use integers to identify each input
            name_getter = count()
            num_inputs = None
        else:
            num_inputs = 1
    else:
        # Input file was given
        if is_bulk_type(type(input_data)):
            # If this is a bulk filetype, we can just iterate over it
            input_list = input_data
            # Get the bulk input to supply names
            name_getter = iter(input_data.get_identifiers())
            num_inputs = len(input_data)
        else:
            # Otherwise, there's just one input
            input_list = [input_data]
            num_inputs = 1
            # Try getting a name for this
            if input_data.name is None:
                name = "unnamed"
            else:
                name = input_data.name
            name_getter = iter([name])
    
    if stdinput:
        input_getter = input_iterator(">> ")
        print "No input string given: accepting input from stdin. Hit Ctrl+d to exit"
        # Load the shell history if possible
        try:
            readline.read_history_file(settings.TAG_PROMPT_HISTORY_FILE)
        except IOError:
            # No history file found. No problem
            pass
    else:
        input_getter = iter(input_list)
    
    ############# Parameter output ################
    # Display the important parameter settings
    print >>sys.stderr, "=== The Jazz Parser tagger ==="
    print >>sys.stderr, "Supertagger:         %s" % options.supertagger
    print >>sys.stderr, "Supertagger options: %s" % toptstr
    print >>sys.stderr, "Grammar:             %s" % grammar.name
    print >>sys.stderr, "Input file:          %s" % options.file
    print >>sys.stderr, "Input filetype:      %s" % options.filetype
    print >>sys.stderr, "Input options:       %s" % (options.file_options or "")
    print >>sys.stderr, "==============================\n"
    
    ########################### Input loop ####################
    # Process each input one by one
    all_results = []
    jobs = []
    
    for input in input_getter:
        if input:
            # Get an identifier for this input
            input_identifier = name_getter.next()
            print "Processing input: %s (%s)" % (input, input_identifier)
            
            # Get a filename for a logger for this input
            if parse_logger_dir:
                parse_logger = os.path.join(parse_logger_dir, "%s.log" % \
                                                    slugify(input_identifier))
                print >>sys.stderr, "Logging parser progress to %s" % parse_logger
                logger = create_logger(filename=parse_logger)
            else:
                logger = create_plain_stderr_logger()
            
            # Catch any errors and continue to the next input, instead of giving up
            try:
                if isinstance(input, str):
                    input = input.rstrip("\n")
                    if len(input) == 0:
                        return
                    input = ChordInput.from_string(input)
                
                logger.info("Tagging sequence (%d timesteps)" % len(input))
                # Prepare a suitable tagger component
                tagger = tagger_cls(grammar, input, options=topts.copy(), logger=logger)
                
            except KeyboardInterrupt:
                print "Exiting on keyboard interrupt"
                break
            except:
                print "Error tagging %s" % input_identifier
                traceback.print_exc()
                print
            else:
                # Tagged successfully
                # Get tags from the tagger as the parser would
                print "Getting categories from tagger as if in adaptive supertagging"
                for offset in count():
                    signs = tagger.get_signs(offset=offset)
                    if not signs:
                        # Didn't get any more signs: give up now
                        print "No more signs"
                        break
                    
                    # Display the signs
                    print "Iteration %d:" % offset
                    for start,end,(sign,tag,prob) in signs:
                        print "  %d -> %d : %s : %s (%s, %s)" % \
                                (start, end, tag, sign, str(tag), prob)
                    
                    if options.interactive:
                        inline = raw_input("Get more signs? [Y/n] ")
                        if inline.lower() == "n":
                            break
                print
    
    if stdinput:
        print
        # Write the history out to a file
        readline.write_history_file(settings.TAG_PROMPT_HISTORY_FILE)

if __name__ == "__main__":
    main()
