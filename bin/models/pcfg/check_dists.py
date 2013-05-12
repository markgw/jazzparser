#!/usr/bin/env ../../jazzshell
"""This is just for debugging of the PCFG model.

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
from jazzparser.data.input import command_line_input
from jazzparser.parsers.cky import DirectedCkyParser
from jazzparser.data.trees import build_tree_for_sequence, TreeBuildError
from jazzparser.taggers.pretagged import PretaggedTagger
from jazzparser.formalisms.music_halfspan.pcfg import model_category_repr, \
                        category_relative_chord
from jazzparser.data import Chord

def main():
    usage = "%prog <model-name>"
    description = "Debug a PCFG model"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-g", "--grammar", dest="grammar", action="store", \
                        help="use the named grammar instead of the default.")
    parser.add_option("-d", "--debug", dest="debug", action="store_true", \
                        help="output debugging information during generation")
    parser.add_option("--file-options", "--fopt", dest="file_options", \
                        action="store", help="options for the input file "\
                        "(--file). Type '--fopt help' for a list of available "\
                        "options.")
    options, arguments = parse_args_with_config(parser)
    
    if len(arguments) < 1:
        print "Specify a model name"
        sys.exit(1)
    model_name = arguments[0]
    
    if len(arguments) < 2:
        print "Specify an input file"
    
    grammar = get_grammar(options.grammar)
    PcfgModel = grammar.formalism.PcfgModel
    # Load the trained model
    model = PcfgModel.load_model(model_name)
    
    # Try getting a file from the command-line options
    input_data = command_line_input(filename=arguments[1], 
                                    filetype="db",
                                    options=options.file_options)
    
    # Prepare the input and annotations
    sequence = input_data.sequence
    categories = [chord.category for chord in sequence.iterator()]
    str_inputs = input_data.inputs
    # Build the implicit normal-form tree from the annotations
    try:
        tree = build_tree_for_sequence(sequence)
    except TreeBuildError, err:
        raise ModelTrainingError, "could not build a tree for '%s': %s" % \
            (sequence.string_name, err)
    
    def _tree_probs(trace):
        """ Add counts to the model from a derivation trace """
        parent = trace.result
        # Get prob for the parent category
        parent_rep = model_category_repr(parent.category)
        print "%s : %s" % (parent_rep, model._parent_dist.prob(parent_rep))
        
        if len(trace.rules) == 0:
            # Leaf node - lexical generation
            # Get prob for this parent expanding as a leaf
            print "%s -leaf- : %s" % (parent_rep, model._expansion_type_dist[parent_rep].prob('leaf'))
            # Interpret the word as a chord
            chord = Chord.from_name(trace.word)
            chord = category_relative_chord(chord, parent.category)
            observation = model.chord_observation(chord)
            # Count this parent producing this word
            # The chord root is now relative to the base pitch of the category
            print "%s -leaf-> %s : %s" % \
                (parent_rep, observation, model._lexical_dist[parent_rep].prob(observation))
        else:
            # Internal node - rule application
            # There should only be one rule application, but just in case...
            for rule,args in trace.rules:
                if rule.arity == 1:
                    # Unary rule
                    raise ModelTrainingError, "we don't currently support "\
                        "unary rule application, but one was found in "\
                        "the training data"
                if rule.arity == 2:
                    # Binary rule
                    expansion = 'right'
                    print "%s -right- : %s" % \
                        (parent_rep, model._expansion_type_dist[parent_rep].prob(expansion))
                    # Count this parent expanding to the head daughter
                    head_rep = model_category_repr(args[1].result.category, 
                                                        parent.category)
                    print "%s -right-> %s : %s" % \
                        (parent_rep, head_rep, 
                         model._head_expansion_dist[(expansion,parent_rep)].prob(head_rep))
                    # Count this parent with this head expansion expanding
                    #  to the non-head daughter
                    non_head_rep = model_category_repr(
                                    args[0].result.category, parent.category)
                    print "%s -right-> %s | %s : %s" % \
                        (parent_rep, head_rep, non_head_rep, 
                         model._non_head_expansion_dist[(
                            head_rep, expansion, parent_rep)].prob(non_head_rep))
                # Recurse to count derivations from the daughters
                for arg in args:
                    _tree_probs(arg)
    
    # The root of this structure is an extra node to contain all separate 
    #  trees. If there's more than one tree, it represents partial parses
    end = 0
    successes = 0
    for sub_tree in tree.children:
        # Use each partial tree to get counts
        length = sub_tree.span_length
        start = end
        end += length
        
        # If this is just a leaf, ignore it - it came from an unlabelled chord
        if not hasattr(sub_tree, 'chord'):
            # Prepare the tagger for this part of the sequence
            # Get a sign for each annotated chord
            tags = []
            for word,tag in zip(str_inputs[start:end],categories[start:end]):
                if tag == "":
                    word_signs = []
                elif tag not in grammar.families:
                    raise ModelTrainingError, "could not get a sign from "\
                        "the grammar for tag '%s' (chord '%s')" % \
                        (tag, word)
                else:
                    # Get all signs that correspond to this tag from the grammar
                    word_signs = grammar.get_signs_for_word(word, pos=[tag])
                tags.append(word_signs)
            
            tagger = PretaggedTagger(grammar, input_data.slice(start,end), tags=tags)
            # Use the directed parser to parse according to this tree
            parser = DirectedCkyParser(grammar, tagger, derivation_tree=sub_tree)
            try:
                parser.parse(derivations=True)
            except DirectedParseError, err:
                # Parse failed, so we can't train on this sequence
                logger.error("Parsing using the derivation tree failed: "\
                    "%s" % err)
                continue
            
            # We should now have a complete parse available
            parses = parser.chart.parses
            if len(parses) > 1:
                raise ModelTrainingError, "the annotated tree gave multiple "\
                    "parse results: %s" % ", ".join(["%s" % p for p in parses])
            parse = parses[0]
            # Now use the derivation trace to compute the probability of each 
            #  bit of the tree
            _tree_probs(parse.derivation_trace)

    
if __name__ == "__main__":
    main()
