#!/usr/bin/env ../../jazzshell
"""Queries an ngram model interactively.

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

import sys, readline
from optparse import OptionParser

from jazzparser import settings
from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.interface import input_iterator
from jazzparser.data.input import ChordInput
from jazzparser.taggers.ngram.tagger import NgramTaggerModel

class QueryError(Exception):
    pass

def main():
    usage = "%prog [<options>] <model-name>"
    description = "Queries an ngram model interactively"
    optparser = OptionParser(usage=usage, description=description)
    # Read in command line options and args
    options, arguments = parse_args_with_config(optparser)
    
    if len(arguments) < 1:
        print "Specify a model name"
        sys.exit(1)
    model_name = arguments[0]
        
    # Load the ngram model
    ngmodel = NgramTaggerModel.load_model(model_name)
    model = ngmodel.model
    
    input_getter = input_iterator(">> ")
    # Load the shell history if possible
    try:
        readline.read_history_file(settings.NGRAM_QUERY_HISTORY_FILE)
    except IOError:
        # No history file found. No problem
        pass
    print "N-gram model query"
    print "Loaded", model_name
    print
    print "Transition:      t <state> <state-1> ... <state-n>"
    print "Emission:        e <chord> <state>"
    print "State domain:    states"
    print "Emission domain: ems"
    
    def _check_state(s):
        if s not in model.label_dom+[None]:
            raise QueryError, "invalid state label: %s" % s
    
    for query in input_getter:
        query = query.rstrip("\n").strip()
        if query:
            try:
                if query.startswith("states"):
                    print ", ".join(model.label_dom)
                elif query.startswith("ems"):
                    print ", ".join(model.emission_dom)
                elif query.startswith("t"):
                    # Transition prob query
                    states = query.split()[1:]
                    if len(states) != model.order:
                        print "Ngram must have length %d" % model.order
                        continue
                    states = [s if s != "None" else None for s in states]
                    # Verify all these states
                    for state in states:
                        _check_state(state)
                    # Get the transition probability
                    prob = model.transition_probability_debug(*states)
                    print "P(Qi = %s | %s) = %f" % (states[0], 
                                    ", ".join(["Q(i-%d) = %s" % (i+1,s) 
                                        for (i,s) in enumerate(states[1:])]),
                                    prob)
                elif query.startswith("e"):
                    # Emission prob query
                    em_state = query.split()[1:]
                    if len(em_state) != 2:
                        print "Emission query must consist of a chord and a state"
                        continue
                    em, state = em_state
                    # Check the state label's valid
                    _check_state(state)
                    # Get the emission probability
                    prob = model.emission_probability(em, state)
                    # Print out the probability
                    print "P(Oi = %s | Qi = %s) = %f" % (em, state, prob)
                else:
                    print "Invalid query: %s" % query
            except QueryError, err:
                print "Check your query: %s" % err
            except Exception, err:
                print "Error processing query: %s" % err
    
    # Write the history out to a file
    readline.write_history_file(settings.NGRAM_QUERY_HISTORY_FILE)
    print

if __name__ == "__main__":
    main()
