"""Some data utilities relating to parsing annotated data to evaluate model.

Tools for running the parser on input from the database to test the 
data.
Note that these should be used on the database mirrors (see 
jazzparser.data.db_mirrors) so that they can be run independently of 
the database itself.

This module now provides some utilities for the parsing routines. The 
actual evaluation routines are in jazzparser.evaluation.parsing.

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

import sys

from jazzparser.parsers import ParseError
from jazzparser.grammar import get_grammar

def keys_for_sequence(sequence, grammar=None):
    """
    Takes a chord sequence from the chord corpus and parses using its 
    annotations. Returns a list of the key (as a pitch class integer) for 
    each chord.
    
    This is simply worked out, once the parse is done. Every chord in a cadence 
    has the same key as the resolution of the cadence, which can be read off 
    by taking the equal temperament pitch class for the tonal space point of 
    the resolution.
    
    """
    from jazzparser.evaluation.parsing import parse_sequence_with_annotations
    if grammar is None:
        grammar = get_grammar()
    # Try parsing the sequence according to the tree in the database
    sub_parses = parse_sequence_with_annotations(sequence, grammar)
    if len(sub_parses) > 1:
        # We can only continue if we got a full parse
        raise ParseError, "could not fully parse the sequence %s." % \
                sequence.string_name
    sems = sub_parses[0].semantics
    
    # Get the keys for this LF, and the times when they start
    keys = grammar.formalism.semantics_to_keys(sems)
    key_roots, change_times = zip(*keys)
    key_roots = iter(key_roots)
    change_times = iter(change_times)
    
    chords = iter(sequence)
    # Get the first key as the current key
    key = key_roots.next()
    # Ignore the first time, as it should be 0
    change_times.next()
    chord_keys = []
    try:
        # Get the next time at which we'll need to change
        next_change = change_times.next()
        
        time = 0
        for chord in sequence.chords:
            if time >= next_change:
                # Move onto the next key
                key = key_roots.next()
                next_change = change_times.next()
            # Add the next chord with the current key value
            chord_keys.append((chord, key))
            time += chord.duration
    except StopIteration:
        # No more timings left
        # Include the rest of the chords with the current key
        for chord in chords:
            chord_keys.append((chord, key))
    
    return chord_keys

class ParseResults(object):
    """
    A simple wrapper object to store the results of a parse, plus the 
    gold standard result, so that they can easily be dumped out to 
    a file using pickle.
    
    The gold parse may be omitted if it's not available. Alternatively, 
    you may store an annotated sequence as your gold standard: this 
    should go in C{gold_sequence}. You may, of course, store both.
    
    @note: this used to store a list of logical forms. Now it can store signs 
    as well: in this case, the logical form can be found in C{sign.semantics} 
    for any sign and C{signs} should be C{True}.
    
    """
    def __init__(self, parses, gold_parse=None, signs=False, \
                    gold_sequence=None, timed_out=None, cpu_time=None):
        self.parses = parses
        """
        List of (probability,interpretation) tuples, where the 
        interpretation is a sign parse result, or a logical form. Which is used 
        should be reflected in C{signs}.
        """
        self.gold_parse = gold_parse
        """The interpretation (tonal space semantics) given by the gold standard."""
        self.signs = signs
        """True is the stored parses are signs and not logical forms."""
        self.gold_sequence = gold_sequence
        """Gold standard interpretation in the form of an annotated chord sequence."""
        self.timed_out = timed_out
        """True if the parse timed out (might still have results from a backoff model)."""
        self.cpu_time = cpu_time
        """Time taken for the parse, measured in CPU time (not wall clock)."""
    
    def __get_sorted_results(self):
        """
        The list of results (TS interpretations or signs) ordered by 
        descending probability.
        
        """
        return list(reversed(sorted(self.parses, key=lambda p:p[0])))
    sorted_results = property(__get_sorted_results)
    
    def __get_semantics(self):
        """
        Always returns a list of (probability,semantics) pairs, whether or 
        not the results were stored as signs. The results are sorted by 
        descending probability.
        
        """
        if hasattr(self, "signs") and self.signs:
            lfs = [(prob,res.semantics) for (prob,res) in self.parses]
        else:
            lfs = self.parses
        return list(reversed(sorted(lfs, key=lambda p:p[0])))
    semantics = property(__get_semantics)
    
    def get_gold_semantics(self):
        """
        Tries to return a gold standard semantics. In some cases this is 
        stored along with the results in C{gold_parse}. In others this is 
        not available, but a gold annotated chord sequence is: then we 
        can get the gold semantics by parsing the annotations. Note that 
        this might take a little bit of time.
        
        In other cases neither is available. Then C{None} will be returned.
        
        """
        from jazzparser.evaluation.parsing import parse_sequence_with_annotations
        
        if self.gold_parse is not None:
            return self.gold_parse
        elif self.gold_sequence is not None:
            # Parse the annotations to get a semantics
            try:
                gold_parses = parse_sequence_with_annotations(
                                                    self.gold_sequence, 
                                                    grammar=get_grammar(),
                                                    allow_subparses=False)
                if len(gold_parses) != 1:
                    # This shouldn't happen, since allow_subparses was False
                    return None
                # Got a result: return its semantics
                return gold_parses[0].semantics
            except ParseError:
                # Could not parse annotated sequence
                return None
        else:
            return None
    
    def get_top_result(self):
        """
        Loads the top parse result and the gold standard result.
        Both a None if there are no results.
        
        @rtype: pair
        @return: top parser semantics and gold standard semantics
        
        """
        if len(self.parses) == 0:
            return None,None
        gold = self.get_gold_semantics()
        top_res = self.semantics[0][1]
        return top_res,gold
    
    def get_name(self):
        """
        Returns a name for the input if one is available, otherwise None.
        
        """
        if self.gold_sequence is not None:
            return self.gold_sequence.string_name
        return 
        
    def save(self, filename):
        import cPickle as pickle
        file = open(filename, 'w')
        pickle.dump(self, file, -1)
        file.close()
        
    @staticmethod
    def from_file(filename):
        import cPickle as pickle
        file = open(filename, 'r')
        data = file.read()
        file.close()
        try:
            obj = pickle.loads(data)
        except Exception, err:
            # It would be nice to except a specific exception, but 
            #  unfortunately unpickling can raise pretty much anything,
            #  (because it's badly written)
            raise ParseResults.LoadError, "could not read parse results "\
                "from %s. %s: %s" % (filename, type(err).__name__, err)
        return obj
    
    class LoadError(Exception):
        pass
