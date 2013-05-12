#!/usr/bin/env ../jazzshell
"""Evaluate a tagging model by tagging sequences from an input file.

This script takes care of all evaluation purely of supertaggers, without 
parsing. Its functions used to be part of eval.py (see below), but eval.py 
is now just for evaluation of full parsing, including a supertagging 
phase.

= History =
The original evaluation script was eval_tagger.py. It was only concerned 
with evaluating supertaggers, as this script is. I then built parser 
evaluation into the same script and eventually renamed it eval.py. Now 
it seems silly to use the same script for both of these things, so tagger 
evaluation gets its own script again!

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

import sys, math, os, logging, copy, traceback, time

from jazzparser import settings
from jazzparser.grammar import Grammar
from jazzparser.evaluation.taggers import tagger_agreement, tagger_entropy
from jazzparser.utils.options import ModuleOption
from jazzparser.utils.output import confusion_matrix
from jazzparser.utils.tableprint import pprint_table
from jazzparser.taggers import TAGGERS
from jazzparser.taggers.loader import get_tagger
from jazzparser.taggers.models import ModelTagger
from jazzparser.parsers.loader import get_parser
from jazzparser.utils.scripts import prepare_evaluation_options
from jazzparser.backoff.loader import get_backoff_builder
from jazzparser.data.input import DbInput

class IdAdder(object):
    """
    Just a very simple closure, but we need to be able to pickle it.
    
    """
    def __init__(self, basename):
        self.basename = basename
    
    def __call__(self, seq):
        return "%s%d" % (self.basename, seq.id)

def main():
    def _check_args(args):
        if len(args) != 3:
            print >>sys.stderr, "Specify a tagger, model name and input file"
            sys.exit(1)
        return args[1],args[2]
    
    partitions,part_ids,options,arguments = prepare_evaluation_options(
        usage = "%prog [options] <tagger> <model-name> <input-file>",
        description = "Evaluate a tagging model by "\
            "tagging sequences from an input file. If the tagger doesn't "\
            "need a model name, use '-' as the model name.",
        check_args = _check_args,
        optparse_groups = [
            (("Tagging",),
                [(("--topt", "--tagger-options"), 
                    {'dest':"topts", 'action':"append", 'help':"options to pass to the tagger."}),
                ]),
            (("Output",), 
                [(("--no-model-info",), 
                    {'dest':"no_model_info", 'action':"store_true", 'help':"turns of outputing of information about the model being used before using it (useful for identifying output piped to a file later, but may be too verbose sometimes)"}),
                ]),
            (("Evaluation", "Type of evaluation and options"),
                [(("-a", "--agreement"), 
                    {'dest':"agreement", 'action':"store_true", 'help':"instead of doing any parses, just report the agreement of the tops tags with the gold standard tags."}),
                 (("--confusion",), 
                    {'dest':"confusion", 'action':"store_true", 'help':"print out confusion matrix after agreement calculation. Applies only in combination with --agreement"}),
                 (("-e", "--entropy"), 
                    {'dest':"entropy", 'action':"store_true", 'help':"instead of doing any parses, just report the entropy of the returned tag distribution with respect to the gold standard tags."}),
                 (("--tag-stats",), 
                    {'dest':"tag_stats", 'action':"store_true", 'help':"just output stats about the tags that the model assigns to this sequence (or these sequences)"}),
                 (("--topn",), 
                    {'dest':"topn", 'type':"int", 'action':"store", 'help':"when evaluating agreement consider the top N tags the tagger returns. By default, allows only the top one to count as a hit.", 'default':1}),
                ]),
        ],
    )
    
    grammar = Grammar()
    
    tagger_name = arguments[0]
    model_name = arguments[1]
    # Tagger shouldn't use a model in some cases
    no_tagger_model = model_name == "-"
    
    # Load the requested tagger class
    tagger_cls = get_tagger(tagger_name)
    topts = ModuleOption.process_option_string(options.topts)
    
    def _model_info(mname):
        """ Outputs info about the named model """
        if options.no_model_info:
            print >>sys.stderr, "Model %s" % mname
        else:
            # Can only output the nice model info if it's a ModelTagger
            if issubclass(tagger_cls, ModelTagger):
                print >>sys.stderr, "======== Model info ========"
                print >>sys.stderr, tagger_cls.MODEL_CLASS.load_model(mname).description
                print >>sys.stderr, "============================"
            else:
                print >>sys.stderr, "Tagger %s using model %s" % (tagger_cls.__name__, mname)
    
    num_parts = len(partitions)
    num_seqs = sum([len(p[0]) for p in partitions])
    
    ################# Evaluation ########################
    if options.tag_stats:
        raise NotImplementedError, "fix this if you want it"
        # Print out statistics for each partition, with its model
        if no_tagger_model:
            # There could be some circumstance in which we want to do this, 
            #  but I can't think what it is, so I'm not implementing it for now
            print >>sys.stderr, "Cannot run tag_stats with no tagger model"
            sys.exit(1)
        all_stats = {}
        for parti in range(num_parts):
            sequences,model,part_num = partitions[parti]
            # Output the model training info if requested
            _model_info(model)
            ######## This doesn't exist any more
            stats = sequences_top_tags_dict(tagger_cls, model, sequences, topn=options.topn)
            for tag,num in stats.items():
                if tag in all_stats:
                    all_stats[tag] += stats[tag]
                else:
                    all_stats[tag] = stats[tag]
        pprint_table(sys.stdout, list(reversed(sorted(all_stats.items(), key=lambda r:r[1]))), separator="|")
    elif options.agreement:
        # Print out agreement stats for each partition
        if no_tagger_model:
            # Same a tag_stats: probably no need for this ever
            print >>sys.stderr, "Cannot run agreement with no tagger model"
            sys.exit(1)
        correct = 0
        total = 0
        conf_mat = {}
        for parti in range(num_parts):
            sequences,model,part_num = partitions[parti]
            topts['model'] = model
            # Output the model training info if requested
            _model_info(model)
            pcorrect = 0
            ptotal = 0
            # Go through each sequence
            for seq in sequences:
                print >>sys.stderr, "Evaluating %s" % seq.string_name
                input = DbInput.from_sequence(seq)
                correct_tags = [chord.category for chord in seq.iterator()]
                cor,tot = tagger_agreement(input, grammar, tagger_cls, correct_tags, options=topts, confusion_matrix=conf_mat, topn=options.topn)
                pcorrect += cor
                ptotal += tot
                print "  Sequence: %.1f%%" % (float(cor)/tot*100)
                print "  So far: %.1f%%" % (float(pcorrect)/ptotal*100)
            print "Partition %d: %d / %d (%.2f%%)" % (part_num, pcorrect, ptotal, (float(pcorrect)/ptotal*100))
            correct += pcorrect
            total += ptotal
        if num_parts > 1:
            # Print out the overall stats
            print "%d / %d (%f%%)" % (correct,total,(float(correct)/total*100))
        if options.confusion:
            confusion_matrix(conf_mat) 
    elif options.entropy:
        print "Calculating cross-entropy of tagger with gold standard tags"
        entropy = 0.0
        num_chords = 0
        for parti in range(num_parts):
            sequences,model,part_num = partitions[parti]
            if not no_tagger_model:
                topts['model'] = model
                # Output the model training info if requested
                _model_info(model)
            pentropy = 0.0
            pnum_chords = 0
            # Compute the entropy for the partition model
            for seq in sequences:
                print >>sys.stderr, "Evaluating %s" % seq.string_name
                input = " ".join([str(chord) for chord in seq.iterator()])
                correct_tags = [chord.category for chord in seq.iterator()]
                ent,crds = tagger_entropy(input, grammar, tagger_cls, correct_tags, options=topts)
                pentropy += ent
                pnum_chords += crds
                print "   %f bits per chord" % (ent/crds)
            print "Partition %d: %f bits per chord (%d chords)" % (part_num, (pentropy/pnum_chords), pnum_chords)
            entropy += pentropy
            num_chords += pnum_chords
        # Print out the stats for all partitions together
        if num_parts > 1:
            print "%f bits per chord (%d chords)" % ((entropy/num_chords), num_chords)
    else:
        print >>sys.stderr, "Select an evaluation operation with one of the options"
        sys.exit(1)

if __name__ == "__main__":
    main()
