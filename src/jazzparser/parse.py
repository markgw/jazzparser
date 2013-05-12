"""Main command-line interface to the Jazz Parser.

Takes input from the command line or a file and parses it. Allows 
specification of formalism, parser and tagger modules.
See usage info for more details.

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

# Make sure the necessary directories are on the path
import sys, os
codedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
libdir = os.path.abspath(os.path.join(codedir, "..", "lib"))
if codedir not in sys.path:
    sys.path.append(codedir)
if libdir not in sys.path:
    sys.path.append(libdir)

from jazzparser.utils.tableprint import pprint_table, print_latex_table, \
                            format_table
from jazzparser.grammar import get_grammar, get_grammar_names
from jazzparser.data import Fraction, Chord
from jazzparser.data.input import DbInput, ChordInput, get_input_type, \
                            is_bulk_type, get_input_type_names, \
                            command_line_input, SegmentedMidiInput, \
                            DbBulkInput, SegmentedMidiBulkInput
from jazzparser.taggers.loader import get_tagger, get_default_tagger, \
                                TaggerLoadError
from jazzparser.utils.base import ExecutionTimer, group_pairs, check_directory, \
                            exception_tuple
from jazzparser.utils.latex import filter_latex
from jazzparser.utils.options import ModuleOption, ModuleOptionError
from jazzparser.utils.loggers import init_logging, create_plain_stderr_logger, \
                            create_logger
from jazzparser.utils.tonalspace import coordinates_to_roman_names, add_z_coordinates
from jazzparser.utils.strings import slugify
from jazzparser.utils.data import partition
from jazzparser.utils.interface import input_iterator
from jazzparser.utils.system import set_proc_title
from jazzparser.parsers.loader import get_default_parser, get_parser, ParserLoadError
from jazzparser.formalisms import FORMALISMS
from jazzparser.utils.config import parse_args_with_config
from jazzparser.harmonical.tones import render_path_to_file as render_path_to_wave_file
from jazzparser.harmonical.midi.chords import render_path_to_file as render_path_to_midi_file
from jazzparser.harmonical.files import save_wave_data
from jazzparser.backoff.loader import get_backoff_builder, BackoffLoadError
from jazzparser.data.parsing import ParseResults

import copy
import logging, traceback
from optparse import OptionParser, OptionGroup
from itertools import count, imap
from multiprocessing import Pool

try:
    import readline
except ImportError:
    readline_loaded = False
else:
    readline_loaded = True

from jazzparser import settings

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

def main():
    set_proc_title("jazzparser")
    ########################################################
    usage = "jazzparser [<options>]"
    description = "The main parser interface for the Jazz Parser"
    ## Process the input options
    optparser = OptionParser(usage=usage, description=description)
    ###
    # File input options
    group = OptionGroup(optparser, "Input", "Input type and location")
    optparser.add_option_group(group)
    group.add_option("--file", "-f", dest="file", action="store", help="use a file to get parser input from. Use --filetype to specify the type of the file.")
    group.add_option("--filetype", "--ft", dest="filetype", action="store", help="select the file type for the input file (--file). Use '--filetype help' for a list of available types. Default: chords", default='chords')
    group.add_option("--file-options", "--fopt", dest="file_options", action="store", help="options for the input file (--file). Type '--fopt help', using '--ft <type>' to select file type, for a list of available options.")
    group.add_option("--index", "--indices", dest="input_index", action="store", help="select individual inputs to process. Specify as a comma-separated list of indices. All inputs are loaded as usual, but only the ith input is processed, for each i in the list")
    group.add_option("--only-load", dest="only_load", action="store_true", help="don't do anything with the inputs, just load and list them. Handy for checking the inputs load and getting their indices")
    group.add_option("--partitions", dest="partitions", action="store", type="int", help="divide the input data into this number of partitions and use a different set of models for each. For any parser, tagger and backoff that takes a 'model' argument, the partition number will be appended to the given value")
    group.add_option("--seq-parts", "--sequence-partitions", dest="sequence_partitions", action="store", help="use a chord sequence index to partition the inputs. Input type (bulk) must support association of the inputs with chord sequences by id. Sequences in the given sequence index file are partitioned n ways (--partitions) and the inputs are processed according to their associated sequence.")
    group.add_option("--continue", "--skip-done", dest="skip_done", action="store_true", help="skip any inputs for which a readable results file already exists. This is useful for continuing a bulk job that was stopped in the middle")
    ###
    group = OptionGroup(optparser, "Parser", "Parser, supertagger and backoff parser")
    optparser.add_option_group(group)
    group.add_option("-d", "--derivations", dest="derivations", action="store_true", help="keep derivation logs during parse.")
    group.add_option("-g", "--grammar", dest="grammar", action="store", help="use the named grammar instead of the default.")
    # Parser options
    group.add_option("-p", "--parser", dest="parser", action="store", help="use the named parser algorithm instead of the default. Use '-p help' to see the list of available parsers. Default: %s" % settings.DEFAULT_PARSER, default=settings.DEFAULT_PARSER)
    group.add_option("--popt", "--parser-options", dest="popts", action="append", help="specify options for the parser. Type '--popt help', using '--parser <name>' to select a parser module, to get a list of options.")
    # Tagger options
    group.add_option("-t", "--tagger", "--supertagger", dest="supertagger", action="store", help="run the parser using the named supertagger. Use '-t help' to see the list of available taggers. Default: %s" % settings.DEFAULT_SUPERTAGGER, default=settings.DEFAULT_SUPERTAGGER)
    group.add_option("--topt", "--tagger-options", dest="topts", action="append", help="specify options for the tagger. Type '--topt help', using '-u <name>' to select a tagger module, to get a list of options.")
    # Backoff options
    group.add_option("-b", "--backoff", "--noparse", dest="backoff", action="store", help="use the named backoff model as a backoff if the parser produces no results")
    group.add_option("--bopt", "--backoff-options", "--backoff-options", "--npo", dest="backoff_opts", action="append", help="specify options for the  backoff model. Type '--npo help', using '--backoff <name>' to select a backoff modules, to get a list of options.")
    ###
    # Multiprocessing options
    group = OptionGroup(optparser, "Multiprocessing")
    optparser.add_option_group(group)
    group.add_option("--processes", dest="processes", action="store", type="int", help="number of processes to create to perform parses in parallel. Default: 1, i.e. no process pool. Use -1 to create a process for every input", default=1)
    ###
    # Output options
    group = OptionGroup(optparser, "Output")
    optparser.add_option_group(group)
    group.add_option("--output", dest="output", action="store", help="directory name to output parse results to. A filename specific to the individual input will be appended to this")
    group.add_option("--topn", dest="topn", action="store", type="int", help="limit the number of final results to store in the output file to the top n by probability. By default, stores all")
    group.add_option("--output-opts", "--oopts", dest="output_opts", action="store", help="options that affect the output formatting. Use '--output-opts help' for a list of options.")
    group.add_option("-a", "--atomic-results", dest="atoms_only", action="store_true", help="only include atomic categories in the results.")
    group.add_option("-l", "--latex", dest="latex", action="store_true", help="output all results as Latex source. Used to produce a whole Latex document, but doesn't any more")
    group.add_option("--all-times", dest="all_times", action="store_true", help="display all timing information on semantics in output.")
    group.add_option("-v", "--debug", dest="debug", action="store_true", help="output verbose debugging information.")
    group.add_option("--time", dest="time", action="store_true", help="time how long the parse takes and output with the results.")
    group.add_option("--no-results", dest="no_results", action="store_true", help="don't print out the parse results at the end. Obviously you'll want to make sure they're going to a file (--output). This is useful for bulk parse jobs, where the results produce a lot of unnecessary output")
    group.add_option("--no-progress", dest="no_progress", action="store_true", help="don't output the summary of completed sequences after each one finishes")
    ###
    # Output analysis and harmonical
    group = OptionGroup(optparser, "Output processing", "Output analysis and harmonical")
    optparser.add_option_group(group)
    group.add_option("--harmonical", dest="harmonical", action="store", help="use the harmonical to play the chords justly intoned according to the top result and output to a wave file.")
    group.add_option("--enharmonical", dest="enharmonical", action="store", help="use the harmonical to play the chords in equal temperament and output to a wave file.")
    group.add_option("--midi", dest="midi", action="store_true", help="generate MIDI files from the harmonical, instead of wave files.")
    group.add_option("--tempo", dest="tempo", action="store", type=int, help="tempo to use for the generated music (see --harmonical/--enharmonical). Default: 120", default=120)
    group.add_option("--lh-analysis", dest="lh_analysis", action="store_true", help="output the Longuet-Higgins space interpretation of the semantics for each result.")
    group.add_option("--lh-coordinates", dest="lh_coord", action="store_true", help="like lh-analysis, but displays the coordinates of the points instead of their names.")
    ###
    # Logging options
    group = OptionGroup(optparser, "Logging")
    optparser.add_option_group(group)
    group.add_option("--long-progress", dest="long_progress", action="store_true", help="print a summary of the chart so far after each chord/word has been processed.")
    group.add_option("--progress", "--short-progress", dest="short_progress", action="store_true", help="print a small amount of information out during parsing to indicate progress.")
    group.add_option("--logger", dest="logger", action="store", help="directory to put parser logging in. A filename based on an identifier for each individual input will be appended.")
    ###
    # Shell options
    group = OptionGroup(optparser, "Shell", "Interactive shell for inspecting results and parser state")
    optparser.add_option_group(group)
    group.add_option("-i", "--interactive", dest="interactive", action="store_true", help="enter interactive mode after parsing.")
    group.add_option("--error", dest="error_shell", action="store_true", help="catch any errors, report them and then enter the interactive shell. This also catches keyboard interrupts, so you can use it to halt parsing and enter the shell.")
    
    # Read in command line options and args
    options, clinput = parse_args_with_config(optparser)

    ########################### Option processing ####################
    
    # Get log level option first, so we can start using the logger
    if options.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    # Set up a logger
    init_logging(log_level)
    
    if options.latex:
        settings.OPTIONS.OUTPUT_LATEX = True
    
    if options.logger:
        # Directory
        parse_logger_dir = options.logger
        check_directory(parse_logger_dir)
    else:
        parse_logger_dir = None
    
    ######## Grammar ########
    # Check the grammar actually exists
    grammar_names = get_grammar_names()
    if options.grammar is not None and options.grammar not in grammar_names:
        # This is not a valid grammar name
        logger.error("The grammar '%s' does not exist. Possible "\
            "grammars are: %s." % (options.grammar, ", ".join(grammar_names)))
        return 1
    grammar = get_grammar(options.grammar)
        
    ######## Parser ########
    # Load the requested parser
    from jazzparser.parsers import PARSERS
    if options.parser.lower() == "help":
        print "Available parsers are: %s" % ", ".join(PARSERS)
        return 0
    try:
        parser_cls = get_parser(options.parser)
    except ParserLoadError:
        logger.error("The parser '%s' could not be loaded. Possible "\
            "parsers are: %s" % (options.parser, ", ".join(PARSERS)))
        return 1
        
    # Get parser options
    if options.popts is not None:
        poptstr = options.popts
        if "help" in [s.strip().lower() for s in poptstr]:
            # Output this tagger's option help
            from jazzparser.utils.options import options_help_text
            print options_help_text(parser_cls.PARSER_OPTIONS, intro="Available options for selected parser")
            return 0
        poptstr = ":".join(poptstr)
    else:
        poptstr = ""
    popts = ModuleOption.process_option_string(poptstr)
    # Check that the options are valid
    try:
        parser_cls.check_options(popts)
    except ModuleOptionError, err:
        logger.error("Problem with parser options (--popt): %s" % err)
        return 1
        
    ######## Supertagger ########
    # Now load the supertagger requested
    from jazzparser.taggers import TAGGERS
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
        logger.error("Problem with tagger options (--topt): %s" % err)
        return 1
    
    ######## Backoff ########
    # Load the requested backoff model, if any
    if options.backoff is not None:
        from jazzparser.backoff import BUILDERS
        if options.backoff.lower() == "help":
            print "Available backoff model types are: %s" % ", ".join(BUILDERS)
            return 0
        try:
            backoff = get_backoff_builder(options.backoff)
        except BackoffLoadError:
            logger.error("The backoff model '%s' could not be loaded. Possible "\
                "models are: %s" % (options.backoff, ", ".join(BUILDERS)))
            return 1
    else:
        backoff = None
        
    # Get backoff options for initializing the backoff model
    if options.backoff_opts is not None:
        npoptstr = options.backoff_opts
        if "help" in [s.strip().lower() for s in npoptstr]:
            # Output this tagger's option help
            from jazzparser.utils.options import options_help_text
            print options_help_text(backoff.BUILDER_OPTIONS, intro="Available options for selected backoff module")
            return 0
        npoptstr = ":".join(npoptstr)
    else:
        npoptstr = ""
    npopts = ModuleOption.process_option_string(npoptstr)
    # Check that the options are valid
    if backoff is not None:
        try:
            backoff.check_options(npopts)
        except ModuleOptionError, err:
            logger.error("Problem with backoff options (--backoff-options): %s" % err)
            return 1
    
    ######## Other misc options ########
    # Time the process and output timing info if requested
    time_parse = options.time
    
    # Display all time information on semantics in output
    settings.OPTIONS.OUTPUT_ALL_TIMES = options.all_times
    
    # Set output options according to the command line spec
    grammar.formalism.cl_output_options(options.output_opts)
    
    # Prepare output directory
    if options.output is None:
        output_dir = None
    else:
        # Check the output directory exists before starting
        output_dir = os.path.abspath(options.output)
        check_directory(output_dir, is_dir=True)
    
    if options.partitions and options.partitions > 1:
        partitions = options.partitions
    else:
        partitions = 1
    
    ############################ Input processing #####################
    stdinput = False
    # Try getting a file from the command-line options
    input_data = command_line_input(filename=options.file, 
                                    filetype=options.filetype,
                                    options=options.file_options)
    # Record progress in this for helpful output
    global completed_parses
    partition_numbers = None
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
            # Let the progress record be filled as we go
            completed_parses = {}
        else:
            num_inputs = 1
            completed_parses = {"commandline":False}
    else:
        # Input file was given
        if is_bulk_type(type(input_data)):
            # If this is a bulk filetype, we can just iterate over it
            input_list = input_data
            # Get the bulk input to supply names
            name_getter = iter(input_data.get_identifiers())
            num_inputs = len(input_data)
            # Fill the progress record with names and mark as incomplete
            completed_parses = dict([(name,False) \
                                    for name in input_data.get_identifiers()])
            if partitions > 1:
                if options.sequence_partitions is not None:
                    # Split the inputs up into partitions on the basis of 
                    #  an even partitioning of chord sequences
                    # This can only be done with 
                    if not isinstance(input_data, SegmentedMidiBulkInput):
                        logger.error("option --sequence-partitions is only "\
                            "valid with bulk midi input data")
                        return 1
                    chord_seqs = DbBulkInput.from_file(options.sequence_partitions)
                    # Partition the chord sequences: we only need indices
                    seq_indices = enumerate(partition(
                                [i for i in range(len(chord_seqs))], partitions))
                    seq_partitions = dict(
                        sum([[(index,part_num) for index in part] for 
                                (part_num,part) in seq_indices], []) )
                    # Associate a partition num with each midi input
                    partition_numbers = [
                        seq_partitions[midi.sequence_index] for midi in input_data]
                else:
                    # Prepare a list of partition numbers to append to model names
                    partition_numbers = sum([
                        [partnum for i in part] for (partnum,part) in \
                         enumerate(partition(range(num_inputs), partitions))], [])
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
            completed_parses = {name:False}
    
    select_indices = None
    if options.input_index is not None:
        indices = []
        try:
            for selector in options.input_index.split(","):
                if "-" in selector:
                    # This is a range
                    start,end = selector.split("-")
                    start,end = int(start),int(end)
                    indices.extend(range(start, end+1))
                else:
                    indices.append(int(selector))
        except ValueError:
            logger.error("Could not parse index values: %s" % options.input_index)
            return 1
        if len(indices):
            select_indices = indices
    
    if stdinput:
        input_getter = input_iterator("Enter chord sequence:\n# ")
        print "No input string given: accepting input from stdin. Hit Ctrl+d to exit"
        # Load the shell history if possible
        if readline_loaded:
            try:
                readline.read_history_file(settings.INPUT_PROMPT_HISTORY_FILE)
            except (IOError):
                # No history file found or readline not available. No problem
                pass
    else:
        input_getter = iter(input_list)
    
    if partitions > 1 and partition_numbers is None:
        # We can only partition certain types of input
        logger.error("Got partitions=%d, but can only partition bulk input "\
                    "data" % (partitions))
        return 1
    
    ############################ Process pool options ##############
    if options.processes == 0 or options.processes < -1:
        # Doesn't make sense
        logger.error("Cannot create %d processes!" % options.processes)
        sys.exit(1)
    
    if select_indices is not None and len(select_indices) == 1 or options.only_load:
        # Selecting a single input: don't use a pool
        processes = 1
    elif num_inputs is None:
        # We don't know how many inputs there will be
        if options.processes == -1:
            logger.error("Could not create a process pool the size of the "\
                "input because we don't know the size of the input")
            processes = 1
        else:
            # Just create the number we were asked to
            processes = options.processes
    else:
        # We know the number of inputs
        if select_indices is not None and len(select_indices) < options.processes:
            # We're only processing a subset of the inputs
            processes = len(select_indices)
        elif options.processes > num_inputs or options.processes == -1:
            # No point creating more processes than inputs
            processes = num_inputs
        else:
            processes = options.processes
    multiprocessing = (processes > 1)
    
    ############# Parameter output ################
    # Display the important parameter settings
    # This is useful for the user, because they see what settings they're 
    #  using even if they're defaults
    print >>sys.stderr, "===== The Jazz Parser ====="
    print >>sys.stderr, "Supertagger:         %s" % options.supertagger
    print >>sys.stderr, "Supertagger options: %s" % toptstr
    print >>sys.stderr, "Parser:              %s" % options.parser
    print >>sys.stderr, "Parser options:      %s" % poptstr
    print >>sys.stderr, "Backoff:             %s" % (options.backoff or "")
    print >>sys.stderr, "Backoff options:     %s" % npoptstr
    print >>sys.stderr, "Grammar:             %s" % grammar.name
    print >>sys.stderr, "Derivation traces:   %s" % ("yes" if options.derivations else "no")
    print >>sys.stderr, "Input file:          %s" % options.file
    print >>sys.stderr, "Input filetype:      %s" % options.filetype
    print >>sys.stderr, "Input options:       %s" % (options.file_options or "")
    print >>sys.stderr, "Input selection:     %s" % \
                            (",".join(str(i) for i in select_indices) \
                             if select_indices else "all")
    if multiprocessing:
        print >>sys.stderr, "Process pool size:   %d" % processes
    else:
        print >>sys.stderr, "No process pool"
    print >>sys.stderr, "===========================\n"
    if options.skip_done:
        print >>sys.stderr, "Skipping any completed parses"
    
    ###################### Process pool init ###########
    if multiprocessing:
        print >>sys.stderr, "Spawning %d worker processes" % processes
        pool = Pool(processes=processes)
    
    #################### Result callback ###############
    def get_output_filename(identifier):
        if output_dir is not None:
            return os.path.join(output_dir, \
                                "%s.res" % slugify(str(identifier)))
    # Callback for getting results back
    # This will be called when the parsing of a sequence is finished
    def _result_callback(response):
        if response is None:
            # Empty input, or the subprocess doesn't want us to do anything
            return
        else:
            # Mark this input as completed
            global completed_parses
            completed_parses[response['identifier']] = True
            
            if response['results'] is None:
                # There was some error: check what it was
                error = response['error']
                print >> sys.stderr, "Error parsing %s" % str(response['input'])
                print >> sys.stderr, "The error was:"
                print >>sys.stderr, error[2]
                global parse_exit_status
                parse_exit_status = 1
            else:
                # Keep this together with all the other processes' responses
                all_results.append(response)
                print "Parsed: %s" % response['input']
                
                # Run any cleanup routines that the formalism defines
                grammar.formalism.clean_results(response['results'])
                
                # Remove complex results if atomic-only option has been set
                if options.atoms_only:
                    response['results'] = remove_complex_categories(response['results'], grammar.formalism)
                
                if not options.no_results:
                    print "Results:"
                    list_results(response['results'])
                
                if output_dir is not None:
                    # Try getting a gold standard analysis if one has been 
                    #  associated with the input
                    gold = response['input'].get_gold_analysis()
                    
                    # Get the results with their probabilities
                    top_results = [(getattr(res, 'probability', None), res) \
                                        for res in response['results']]
                    if options.topn is not None:
                        # Limit the results that get stored
                        top_results = list(reversed(sorted(
                                                top_results)))[:options.topn]
                    # Output the results to a file
                    presults = ParseResults(
                                    top_results, 
                                    signs=True,
                                    gold_parse=gold,
                                    timed_out=response['timed_out'],
                                    cpu_time=response['time'])
                    filename = get_output_filename(response['identifier'])
                    presults.save(filename)
                    print "Parse results output to %s" % filename
                
                if time_parse:
                    print "Parse took %f seconds" % response['time']
                    
                if options.lh_analysis:
                    print >>sys.stderr, "\nLonguet-Higgins tonal space analysis for each result:"
                    # Output the tonal space path for each result
                    for i,result in enumerate(response['results']):
                        path = grammar.formalism.sign_to_coordinates(result)
                        coords,times = zip(*path)
                        print "%d> %s" % (i, ", ".join(
                            ["%s@%s" % (crd,time) for (crd,time) in 
                                    zip(coordinates_to_roman_names(coords),times)]))
                        
                if options.lh_coord:
                    print >>sys.stderr, "\nLonguet-Higgins tonal space coordinates for each result:"
                    # Output the tonal space path for each result
                    for i,result in enumerate(response['results']):
                        path = grammar.formalism.sign_to_coordinates(result)
                        print "%d> %s" % (i, ", ".join(["(%d,%d)@%s" % (x,y,t) for ((x,y),t) in path]))
                
                # Print out any messages the parse routine sent to us
                for message in response['messages']:
                    print message
                    
                # Print as summary of what we've completed
                num_completed = len(filter(lambda x:x[1], completed_parses.items()))
                if not stdinput:
                    if not options.no_progress:
                        print format_table([
                                [str(ident), 
                                 "Complete" if completed_parses[ident] else ""]
                                    for ident in sorted(completed_parses.keys())])
                    if num_inputs is None:
                        print "\nCompleted %d parses" % num_completed
                    else:
                        print "\nCompleted %d/%d parses" % (num_completed, num_inputs)
                    
                # Enter interactive mode now if requested in options
                # Don't do this is we're in a process pool
                if not multiprocessing and options.interactive:
                    print 
                    from jazzparser.shell import interactive_shell
                    env = {}
                    env.update(globals())
                    env.update(locals())
                    interactive_shell(response['results'],
                                      options,
                                      response['tagger'], 
                                      response['parser'],
                                      grammar.formalism,
                                      env,
                                      input_data=response['input'])
                print
                # Flush the output to make sure everything gets out before we start the next one
                sys.stderr.flush()
                sys.stdout.flush()
    #### End of _result_callback
    
    
    ########################### Input loop ####################
    # Process each input one by one
    all_results = []
    jobs = []
    # This will get set to 1 if any errors are encountered during parsing
    global parser_exit_status
    parser_exit_status = 0
    
    for input_index,input in enumerate(input_getter):
        # Get an identifier for this input
        input_identifier = name_getter.next()
        
        if select_indices is not None:
            # Check whether this is the input we're supposed to process
            if input_index not in select_indices:
                continue
            else:
                print >>sys.stderr, "Restricting to input %d" % input_index
        
        if options.only_load:
            # Just output that we'd process this input, but don't do anything
            print "Input %d: %s" % (input_index,input_identifier)
            continue
        
        if options.skip_done:
            # Skip any inputs for which a readable output file already exists
            outfile = get_output_filename(input_identifier)
            if os.path.exists(outfile):
                # Try loading the output file
                try:
                    old_res = ParseResults.from_file(outfile)
                except ParseResults.LoadError, err:
                    pass
                else:
                    # File loaded ok: don't process this input
                    # Mark it as complete
                    completed_parses[input_identifier] = True
                    continue
        
        # Mark this as incomplete
        completed_parses[input_identifier] = False
        
        # Get a filename for a logger for this input
        if parse_logger_dir:
            parse_logger = os.path.join(parse_logger_dir, "%s.log" % \
                                                slugify(input_identifier))
        else:
            parse_logger = None
        
        # Create a new copy of the options dicts for this partition
        input_topts = copy.deepcopy(topts)
        input_popts = copy.deepcopy(popts)
        input_npopts = copy.deepcopy(npopts)
        
        if partitions > 1:
            partition_num = partition_numbers[input_index]
            # All ModelTagger, PcfgParser and BackoffBuilder 
            #  subclasses take this option, so it's safe 
            #  to assume that if we're giving a model name we can also give 
            #  a partition number
            if 'model' in input_topts and input_topts['model'] is not None:
                input_topts['partition'] = partition_num
            if 'model' in input_popts and input_popts['model'] is not None:
                input_popts['partition'] = partition_num
            if 'model' in input_npopts and input_npopts['model'] is not None:
                input_npopts['partition'] = partition_num
        
        if multiprocessing:
            # Add a job to the process pool
            jobs.append(
                pool.apply_async(do_parse, \
                    (grammar, tagger_cls, parser_cls, input, input_topts, 
                        input_popts, backoff, input_npopts, options, 
                        input_identifier), 
                    { 'multiprocessing' : True, 
                      'logfile' : parse_logger },
                    _result_callback))
        else:
            # Just run do_parse on this input
            response = do_parse(grammar, tagger_cls, parser_cls, input, 
                input_topts, input_popts, backoff, input_npopts, options, 
                input_identifier, multiprocessing=False, 
                logfile=parse_logger)
            _result_callback(response)
    
    if multiprocessing:
        # Block until all processes are done
        try:
            pool.close()
            print >>sys.stderr, "Waiting for parse jobs to complete"
            pool.join()
        except KeyboardInterrupt:
            # Subprocesses return on keyboard interrupt, so we should receive 
            #  it here
            print >>sys.stderr, "Exiting on keyboard interrupt"
            sys.exit(1)
    
        # Check that each process completed and display the errors if not
        for job in jobs:
            if not job.successful():
                try:
                    # Get the exception
                    job.get()
                except Exception, err:
                    # Unfortunately, it's impossible to get any 
                    #  more info on where the error came from
                    print >>sys.stderr, "\nError in worker thread: %s" % err
                    parser_exit_status = 1
    
    if stdinput:
        print
        # Write the history out to a file
        if readline_loaded:
            readline.write_history_file(settings.INPUT_PROMPT_HISTORY_FILE)
    sys.exit(parser_exit_status)
# End of main() function


def do_parse(grammar, tagger_cls, parser_cls, input, topts, popts, backoff, 
        npopts, options, identifier, multiprocessing=False, 
        logfile=None, partition=None):
    """
    Function called for each input to do tagging and parsing and return the 
    results. It's a separate function so that we can hand it over to worker 
    processes to do multiprocessing.
    
    @type logfile: str
    @param logfile: filename to send logging output to. If None, will log 
        to stderr
    
    """
    # If the input's a string, preprocess it
    if isinstance(input, str):
        input = input.rstrip("\n")
        if len(input) == 0:
            return
        input = ChordInput.from_string(input)
    
    print "Processing input: %s (%s)" % (input, identifier)
        
    if logfile is None:
        # Sending logging output to stderr
        logger = create_plain_stderr_logger()
    else:
        logger = create_logger(filename=logfile)
        print "Logging parser progress to %s" % logfile
    
    # Prepare an initial response
    # We'll fill in some values of this later
    response = {
        'tagger' : None,
        'parser' : None,
        'input' : input,
        'error' : None,
        'messages' : [],
        'time' : None,
        'identifier' : identifier,
        'results' : None,
        'timed_out' : False,
    }
    tagger = None
    parser = None
    messages = []
    
    if options.short_progress:
        # Only output the short form of the progress reports
        progress = 2
    elif options.long_progress:
        progress = 1
    else:
        progress = 0
    
    # Start a timer now to time the parse
    timer = ExecutionTimer(clock=True)
    
    # Catch any errors and continue to the next input, instead of giving up
    try:
        ######### Do that parsing thang
        logger.info("Tagging sequence (%d timesteps)" % len(input))
        
        # Prepare a suitable tagger component
        tagger = tagger_cls(grammar, input, options=topts.copy(), logger=logger)
        if not multiprocessing:
            response['tagger'] = tagger
        
        # Create a parser using this tagger
        parser = parser_cls(grammar, tagger, options=popts.copy(), 
                                backoff=backoff, 
                                backoff_options=npopts.copy(),
                                logger=logger)
        if not multiprocessing:
            response['parser'] = parser
        try:
            # Parse to produce a list of results
            results = parser.parse(derivations=options.derivations, summaries=progress)
        except (KeyboardInterrupt, Exception), err:
            if multiprocessing:
                # Don't go interactive if we're in a subprocess
                # Instead, just return with an error
                response.update({
                    'error' : exception_tuple(str_tb=True),
                })
                return response
            else:
                # Drop into the shell
                if type(err) == KeyboardInterrupt:
                    print "Dropping out on keyboard interrupt"
                    print "Entering shell: use 'chart' command to see current state of parse"
                elif options.error_shell:
                    print >> sys.stderr, "Error parsing %s" % str(input)
                    print >> sys.stderr, "The error was:"
                    traceback.print_exc(file=sys.stderr)
                # If we keyboard interrupted, always go into the shell, so 
                #  the user can see how far we got
                if options.error_shell or type(err) == KeyboardInterrupt:
                    # Instead of exiting, enter the interactive shell
                    print 
                    from jazzparser.shell import interactive_shell
                    env = {}
                    env.update(globals())
                    env.update(locals())
                    interactive_shell(parser.chart.parses,options,tagger,parser,
                                grammar.formalism,env,input_data=input)
                    return
                else:
                    raise
    except (KeyboardInterrupt, Exception), err:
        if multiprocessing:
            response.update({
                'error' : exception_tuple(str_tb=True),
            })
            return response
        else:
            if type(err) == KeyboardInterrupt:
                print "Exiting on keyboard interrupt"
                sys.exit(1)
            else:
                response.update({
                    'error' : exception_tuple(str_tb=True),
                    'messages' : messages,
                    'time' : timer.get_time(),
                })
                return response
    else:
        # Parsed successfully
        # Do some postprocessing and return to the main function
    
        # Output audio files from the harmonical
        if (options.harmonical is not None or \
                options.enharmonical is not None) and len(results) > 0:
            path = grammar.formalism.sign_to_coordinates(results[0])
            # Assuming we used a temporal formalism, the times should be 
            #  available as a list from the semantics
            times = results[0].semantics.get_path_times()
            point_durations = [next-current for current,next in group_pairs(times)] + [0]
            # Get 3d coordinates as well
            path3d = zip(add_z_coordinates(path, pitch_range=2), point_durations)
            path2d = zip(path,point_durations)
            # Get chord types out of the input
            chords = tagger.get_string_input()
            chord_durs = [tagger.get_word_duration(i) for i in range(tagger.input_length)]
            chord_types = [(Chord.from_name(c).type,dur) for c,dur in zip(chords,chord_durs)]
            
            if options.midi:
                # Maybe set this as a CL option or a setting
                # 73 - flute
                # 0  - piano
                # 4  - e-piano
                instrument = 73
                # TODO: make these filenames different for multiple inputs
                if options.harmonical is not None:
                    filename = os.path.abspath(options.harmonical)
                    render_path_to_midi_file(filename, path3d, chord_types=chord_types, tempo=options.tempo, instrument=instrument, bass_root=True, root_octave=-1)
                    messages.append("Output JI MIDI data to %s" % filename)
                if options.enharmonical is not None:
                    filename = os.path.abspath(options.enharmonical)
                    render_path_to_midi_file(filename, path3d, chord_types=chord_types, equal_temperament=True, tempo=options.tempo, instrument=instrument, bass_root=True, root_octave=-1)
                    messages.append("Output ET MIDI data to %s" % filename)
            else:
                if options.harmonical is not None:
                    filename = os.path.abspath(options.harmonical)
                    render_path_to_wave_file(filename, path2d, chord_types=chord_types, double_root=True, tempo=options.tempo)
                    messages.append("Output JI wave data to %s" % filename)
                if options.enharmonical is not None:
                    filename = os.path.abspath(options.enharmonical)
                    render_path_to_wave_file(filename, path2d, chord_types=chord_types, double_root=True, equal_temperament=True, tempo=options.tempo)
                    messages.append("Output ET wave data to %s" % filename)
        
        response.update({
            'results' : results,
            'time' : timer.get_time(),
            'messages' : messages,
            'timed_out' : parser.timed_out,
        })
        return response


def list_results(results):
    """
    Prints out a list of the results in the given results list. 
    This is used after parsing and during interactive results viewing.
    """
    # Print out what we got
    if len(results) == 0:
        if settings.OPTIONS.OUTPUT_LATEX:
            print "\\textit{No results}\n"
        else:
            print "No results"    
    else:
        # Print the results with numbers and pretty arrows otherwise
        if settings.OPTIONS.OUTPUT_LATEX:
            print "\\begin{enumerate}"
            for i in range(len(results)):
                print "\\item %s" % (filter_latex(results[i].format_latex_result()))
            print "\\end{enumerate}"
        else:
            for i in range(len(results)):
                print "%d>  %s" % (i, results[i].format_result())

def remove_complex_categories(result_list, formalism):
    # Filter out results that aren't atomic categories
    return [sign for sign in result_list if type(sign.category) == formalism.Syntax.AtomicCategory]

if __name__ == "__main__":
    sys.exit(main())
