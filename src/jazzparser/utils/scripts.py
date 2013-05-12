"""Utilities for bin scripts.

These are used by scripts outside the Jazz Parser packages, in 
<PROJECT_ROOT>/bin.

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

def prepare_evaluation_options(usage=None, description=None, 
        optparse_options=[], check_args=None, optparse_groups=[]):
    """
    Various tasks common to the initial part of the evaluation routine
    scripts (C{models/eval.py}).
    
    @todo: This is not used any more. Remove it, after checking it's definitely 
        not used.
    
    @param usage: the optparse usage string
    @param description: the optparse description string
    @type optparse_options: list of tuples
    @param optparse_options: (args,kwargs) pairs to add additional 
        options to the optparse parser.
    @type check_args: function
    @param check_args: function to take the command-line arguments and 
        check them. This will be called early in the script. Must 
        return a tuple of (1) the model name (or model basename) that 
        will be used in the partition model names and (2) the input 
        filename to get sequences from.
    @type optparse_groups: list of pairs
    @param optparse_groups: specificatios for option groups to add to the 
        optparse option parser. The first of each pair is a tuple of 
        args to C{OptionGroup}'s init (excluding the first). 
        The second is a list of options 
        each formatted as C{optparse_options}.
        
    @rtype: tuple
    @return: (1) list of (sequences,model_name,partition_index) tuples
        for each partition; (2) list of lists containing the sequence 
        ids for each partition; (3) optparse options; (4) optparse 
        arguments.
    
    """
    import sys
    from optparse import OptionParser, OptionGroup
    from jazzparser.utils.config import parse_args_with_config
    from jazzparser.utils.loggers import init_logging
    from jazzparser.data.db_mirrors import SequenceIndex
    from jazzparser.utils.data import partition
    
    parser = OptionParser(usage=usage, description=description)
    group = OptionGroup(parser, "Input", "Input data and partitioning for evaluation")
    group.add_option("-s", "--sequence", dest="sequence", action="store", help="limit the evaluation to just one sequence, with the given index in the input file")
    group.add_option("--partition", dest="partition", action="store", help="restrict to only one partition of the data. Specify as i/n, where i is the partition number and n the total number of partitions.")
    group.add_option("-p", "--partitions", dest="partitions", type="int", action="store", help="test on all n partitions of the data, using a different model for each. Will look for a model <NAME>i, where <NAME> is the given model name and i the partition number.")
    parser.add_option_group(group)
    
    parser.add_option("--debug", dest="debug", action="store_true", help="show debugging output")
    
    # Add the options according to their specs
    for args,kwargs in optparse_options:
        parser.add_option(*args, **kwargs)
        
    # Add groups and their options
    for group_args,options in optparse_groups:
        # Check whether the group already exists
        same_titles = [g for g in parser.option_groups if g.title == group_args[0]]
        if same_titles:
            group = same_titles[0]
        else:
            group = OptionGroup(parser, *group_args)
            parser.add_option_group(group)
        # Add options to this group
        for args,kwargs in options:
            group.add_option(*args, **kwargs)
    options, arguments = parse_args_with_config(parser)
    
    if check_args is None:
        raise ValueError, "could not check arguments and get model "\
            "name. check_args must not be None"
    model_name,input_filename = check_args(arguments)
        
    if options.debug:
        # Set the log level to debug and do the standard logging init
        init_logging(logging.DEBUG)
    else:
        init_logging()
        
    # Load up sequences
    seqs = SequenceIndex.from_file(input_filename)
        
    def _get_seq_by_index(index):
        seq = seqs.sequence_by_index(index)
        if seq is None:
            print >>sys.stderr, "There are only %d sequences" % len(seqs)
            sys.exit(1)
        return seq
    
    ################ Data partitioning ####################
    if options.partitions is not None:
        # Divide the data up into n partitions and use a different model name for each
        total_parts = options.partitions
        print >>sys.stderr, "Cross validation: dividing test data into %d partitions" % total_parts
        partitions = [(part,"%s%d" % (model_name,i), i) for i,part in enumerate(partition(seqs.sequences, total_parts))]
        part_ids = partition(seqs.ids, total_parts)
    elif options.partition is not None:
        # Just select one partition
        # Split up the argument to get two integers
        parti,total_parts = options.partition.split("/")
        parti,total_parts = int(parti), int(total_parts)
        print >>sys.stderr, "Restricting sequences to %d-way partition %d" % (total_parts,parti)
        # Get a list of sequence indices to restrict our set to
        part_ids = partition(seqs.ids, total_parts)[parti]
        partitions = [ [(part,"%s%d" % (model_name,i), i) for i,part in enumerate(partition(seqs.sequences, total_parts))][parti] ]
    elif options.sequence is not None:
        # Just select one sequence
        seq = _get_seq_by_index(int(options.sequence))
        partitions = [( [seq], model_name, 0 )]
        part_ids = [seq.id]
    else:
        # Don't partition the sequences
        partitions = [(seqs.sequences, model_name,0)]
        part_ids = [None]
    
    return partitions,part_ids,options,arguments
