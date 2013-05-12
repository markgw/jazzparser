"""Evaluation tools for evaluating the parsing process.

Once upon a time, this was a handy interface to 
supertagging and parsing that made it easy to write evaluation routines. 
Nowadays, the main parse script is much more capable and the interface 
to the parsers is much cleaner anyway.

The only thing left here now is C{parse_sequence_with_annotations} 

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

import sys, traceback, os

from jazzparser.data.trees import build_tree_for_sequence, TreeBuildError
from jazzparser.parsers.cky.parser import DirectedCkyParser, DirectedParseError
from jazzparser.data.input import DbInput, AnnotatedDbInput
from jazzparser.taggers.pretagged import PretaggedTagger
from jazzparser.parsers import ParseError
from jazzparser.grammar import get_grammar
from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.data.parsing import ParseResults
from jazzparser.utils.loggers import create_logger, create_dummy_logger

def parse_sequence_with_annotations(sequence, grammar, logger=None, 
        allow_subparses=True, popts={}, parse_logger=None):
    """
    Parses an annotated sequence. This is essentially just constructing 
    the implicit derivation encoded in the annotations (categories 
    and coordination markers) and returning the top-level result that 
    this derivation yields.
    
    If there are missing annotations, this will not yield a single 
    result, but the results of each parse of a subsequence.
    
    Returns a list of parse results. If the annotation is complete, the 
    return value should be a single-item list containing the parse 
    result.
    
    @type allow_subparses: boolean
    @param allow_subparses: if True (default) will return multiple 
        subparses if the annotation is incomplete. If False, raises 
        a ParseError in this case.
    @type popts: dict
    @param popts: options to pass to the parser
    @type parse_logger: bool
    @param parse_logger: logger to which to report a trace of the shift-reduce 
        parse of the annotations. If None, nothing is output
    
    """
    # Prepare the input and annotations
    if isinstance(sequence, DbInput):
        input = sequence
        sequence = sequence.sequence
        durations = input.durations
        times = input.times
    else:
        raise ValueError, "parse_sequence_with_annotations can only be "\
            "applied to a DbInput. Got: %s" % type(sequence).__name__
    categories = [chord.category for chord in sequence.iterator()]
    
    try:
        tree = build_tree_for_sequence(sequence, grammar=grammar)
    except TreeBuildError, err:
        raise ParseError, "could not build a tree for '%s': %s" % \
            (sequence.string_name, err)
            
    if not allow_subparses and len(tree.children) > 1:
        raise ParseError, "gold standard for sequence '%s' does not "\
            "yield a single tree: annotation is incomplete" % \
            sequence.string_name
    
    sub_parses = []
    end = 0
    i = 0
    # Each subtree of the root represents a partial parse
    for sub_tree in tree.children:
        # Use each partial tree to get counts
        length = sub_tree.span_length
        start = end
        end += length
        
        # If this is just a leaf: ignore it - it came from an unlabelled chord
        if hasattr(sub_tree, 'chord'):
            continue
        i += 1
        
        # Prepare the tagger for this part of the sequence.
        # Get a sign for each annotated chord
        tags = []
        for word,tag,duration,time in zip(
                                list(input)[start:end],
                                categories[start:end],
                                durations[start:end],
                                times[start:end]):
            if tag == "":
                word_signs = []
            elif tag not in grammar.families:
                raise ParseError, "could not get a sign from the "\
                    "grammar for the tag %s (chord %s)" % \
                    (tag, word)
            else:
                # Get all signs that correspond to this tag from the grammar
                word_signs = grammar.get_signs_for_word(word, tags=[tag],
                                extra_features={
                                    'duration' : duration,
                                    'time' : time,
                                })
            tags.append(word_signs)
        tagger = PretaggedTagger(grammar, input.slice(start,end), tags=tags)
            
        # Use the directed parser to try parsing according to this tree
        parser = DirectedCkyParser(grammar, tagger, derivation_tree=sub_tree, options=popts)
        try:
            parser.parse(derivations=True)
        except DirectedParseError, err:
            # Parse failed, so we can't train on this sequence
            raise ParseError, "[Partial parse %d (%d-%d)] parsing using "\
                "the derivation tree failed: %s" % (i,start,end,err)
        # We should now have a complete parse available
        parses = parser.chart.parses
        if len(parses) == 0:
            raise ParseError, "[Partial parse %d (%d-%d)] parsing using the "\
                "derivation tree did not produce any results" % (i,start,end)
        elif len(parses) > 1:
            raise ParseError, "the annotated tree gave multiple "\
                "parse results: %s" % ", ".join(["%s" % p for p in parses])
        else:
            sub_parses.append(parses[0])
        
    return sub_parses
