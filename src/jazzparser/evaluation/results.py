"""A few simple convenience functions for processing results from evaluation

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

from jazzparser.data.parsing import ParseResults
from jazzparser.grammar import get_grammar

def get_top_result(filename):
    """
    Loads a top parse result from a ParseResults file and the gold standard 
    result.
    
    @note: effectively now moved to ParseResults.get_top_result(). 
        This is just a wrapper for backward compatibility.
    
    @rtype: pair
    @return: gold standard result and top parser result
    
    """
    # Load the data in from the file
    res = ParseResults.from_file(filename)
    top,gold = res.get_top_result()
    if top is not None:
        return top.lf, gold.lf
    else:
        return None,None

def results_alignment(top_result, gold, grammar=None):
    """
    Returns the list of alignment operations that result in the optimal alignment.
    
    @return: tuple containing the alignment and the two sequences in the form 
    that they were compared (gold, top result).
    
    """
    if grammar is None:
        grammar = get_grammar()
    # Perform the alignment
    alignment,gold_seq,result_seq = grammar.formalism.Evaluation.tonal_space_alignment(gold, top_result)
    return alignment,gold_seq,result_seq

def result_lengths(filename, grammar=None):
    """
    Opens the parse results file and returns the lengths of the gold standard 
    path and the top parse result's path.
    
    """
    if grammar is None:
        grammar = get_grammar()
    # Load the data in from the file
    res = ParseResults.from_file(filename)
    
    gold_parse = res.get_gold_semantics()
    if gold_parse is None:
        gold_length = 0
    else:
        # Measure the length of the gold standard
        gold_length = grammar.formalism.Evaluation.tonal_space_length(gold_parse)
    
    # Get the results in order of probability
    results = res.semantics
    if len(results) == 0:
        # No results: cannot analyse them
        return gold_length,0
    top_result = results[0][1]
    top_length = grammar.formalism.Evaluation.tonal_space_length(top_result)
        
    return gold_length, top_length
