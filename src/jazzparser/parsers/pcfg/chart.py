"""Chart representation for the PCFG parser.

Since the PCFG parser is just a CKY parser with probabilities added 
in, the chart implementation merely extends the CKY chart and overrides 
the crucial step of applying rules so that it can do its probabilistic 
stuff.

Note that all probabilities are log probabilities.

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

from jazzparser.parsers.cky.chart import Chart, SignHashSet
from jazzparser.data import DerivationTrace
from jazzparser.utils.strings import fmt_prob
from jazzparser.utils.nltk.probability import logprob

from nltk.probability import add_logs, _NINF

from jazzparser import settings
import logging

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class ProbabilisticSignHashSet(SignHashSet):
    """
    For this chart's internal data structure, we use a modified 
    implementation of the HashSet which adds handling of probabilities.
    
    All probabilities are logged,
    
    """
    def __init__(self, *args, **kwargs):
        self.threshold = kwargs.pop('threshold', settings.PCFG_PARSER.DEFAULT_THRESHOLD)
        self.maxsize = kwargs.pop('maxsize', settings.PCFG_PARSER.DEFAULT_MAX_ARC_SIZE)
        self.viterbi = kwargs.pop('viterbi', False)
        if self.viterbi:
            # We don't need to check to avoid duplicates
            # We already check here to eliminate duplicate syntactic types, 
            #  so we can speed up the implementation by skipping this check
            kwargs['check_existing'] = False
        super(ProbabilisticSignHashSet, self).__init__(*args, **kwargs)
        self._beamed = False
    
    def _add_existing_value(self, existing_value, new_value):
        # Sum the probabilities of the two signs
        existing_value.probability = add_logs(new_value.probability, existing_value.probability)
        # Do the same for the inside probs
        existing_value.inside_probability = add_logs(
                                            new_value.inside_probability, 
                                            existing_value.inside_probability)
        # Continue to do whatever the formalism wants with the signs
        super(ProbabilisticSignHashSet, self)._add_existing_value(existing_value, new_value)
        
    def _max_probability(self):
        return max([val.probability for val in self.values()]+[_NINF])
        
    def append(self, *args, **kwargs):
        """
        There's no point in applying a beam if nothing's been added to 
        the set and it's already been applied. Note that something's 
        been added.
        
        """
        new_entry = args[0]
        if self.viterbi:
            if new_entry.category in self._signs_by_category:
                # A sign with this syntactic type already exists
                # Just keep the one with higher score
                # There should only be one in here
                existing = self._signs_by_category[new_entry.category][0]
                if existing.inside_probability < new_entry.inside_probability:
                    # Replace the existing one with this
                    self.remove(existing)
                else:
                    # Ignore this one: it's not as good as what we've got
                    return False
            self._beamed = False
            return super(ProbabilisticSignHashSet, self).append(*args, **kwargs)
        else:
            self._beamed = False
            return super(ProbabilisticSignHashSet, self).append(*args, **kwargs)
        
    def remove(self, *args, **kwargs):
        self._beamed = False
        super(ProbabilisticSignHashSet, self).remove(*args, **kwargs)
        
    def _apply_beam(self):
        """
        Applies a beam, using the already given threshold, to the set,
        pruning out any signs with a probability lower than the 
        given ratio of the most probable sign.
        """
        if not self._beamed:
            max = self._max_probability()
            cutoff = max + logprob(self.threshold)
            to_remove = [sign for sign in self.values() if sign.probability < cutoff]
            for sign in to_remove:
                self.remove(sign)
            logger.debug("Beam removed %d signs (max %s, min %s)" % \
                            (len(to_remove),max, cutoff))
            # Beam is now applied: check the remaining size
            if self.maxsize != 0:
                if len(self) > self.maxsize:
                    logger.debug("Hard beam removed %d signs" % (self.maxsize-len(self)))
                    # Too many signs: apply a hard cutoff
                    ordered = list(sorted(self.values(), key=lambda s:s.probability))
                    for sign in ordered[self.maxsize:]:
                        self.remove(sign)
            # Don't apply the beam again until something changes
            self._beamed = True
            
    def ranked(self):
        """
        Returns the signs in the set ranked by probability (highest 
        first).
        
        """
        return list(reversed(sorted(self.values(), key=lambda s:s.probability)))

class PcfgChart(Chart):
    """
    Overrides the CKY chart to add probabilistic stuff.
    
    Signs in the input should have an attribute 'probability'.
    The results of rule application will also have such an attribute.
    
    """
    HASH_SET_IMPL = ProbabilisticSignHashSet
    
    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', None)
        if self.model is None:
            raise ValueError, "PcfgChart must be instantiated with a "\
                "model it can use to assign probabilities."
        # The threshold probability below which we throw signs away
        kwargs['hash_set_kwargs'] = {
            'threshold' : kwargs.pop('threshold', None),
            'maxsize' : kwargs.pop('maxarc', None),
            'viterbi' : kwargs.pop('viterbi', False)
        }
        super(PcfgChart, self).__init__(*args, **kwargs)
        # For convenience
        self.catrep = self.grammar.formalism.PcfgParser.category_representation
    
    def _get_ranked_parses(self):
        """
        Full parses ranked by probability.
        Returns a list.
        
        """
        return list(reversed(sorted(self.parses, key=lambda s:s.probability)))
    ranked_parses = property(_get_ranked_parses)
        
    def apply_unary_rule(self, rule, start, end, beam=True):
        # Apply the rule using the super method
        def _get_res_mod(model):
            # Closure to get model and catrep
            def _res_mod(result, sign):
                # Function to add the probability to each result from the input
                # Use the model to get the probabilities
                inside_prob = logprob(model.inside_probability(
                                                    'unary', result, sign)) + \
                                            sign.inside_probability
                outside_prob = logprob(model.outside_probability(result))
                result.inside_probability = inside_prob
                result.probability = outside_prob + inside_probability
        _result_modifier = _get_res_mod(self.model)
        
        # Now just use the superclass' method with this to modify to results
        signs_added = super(PcfgChart, self).apply_unary_rule(rule, start, end, result_modifier=_result_modifier)
        
        if beam and signs_added:
            # Apply a beam to the arc
            self.apply_beam((start,end))
        return signs_added
    
    def _binary_expansion_probability(self, sign_pair, result):
        """
        Used by L{_apply_binary_rule} and L{_apply_binary_rule_semantics} to 
        compute the expansion probabilitiy.
        
        This is a separate function because both of the above do the same 
        to compute the probabilities, so I don't want to repeat the code.
        
        Returns a tuple of the probability and the inside probability.
        
        """
        parent = result
        left, right = sign_pair
        expansion = 'right'
        # Get the probabilities from the model
        subtree_prob = logprob(self.model.inside_probability(
                                            expansion, parent, left, right))
        outside_prob = logprob(self.model.outside_probability(parent))
        # Multiply in the daughters' inside probs to get the inside prob
        inside_prob = subtree_prob + left.inside_probability + \
                                        right.inside_probability
        return (inside_prob+outside_prob, inside_prob)
        
    def _apply_binary_rule(self, rule, sign_pair):
        # Call the superclass method to do the application
        results = super(PcfgChart, self)._apply_binary_rule(rule, sign_pair)
        
        # Add probabilities to the results
        for result in results:
            result.probability, result.inside_probability = \
                    self._binary_expansion_probability(sign_pair, result)
        return results
        
    def _apply_binary_rule_semantics(self, rule, sign_pair, category):
        # Call the superclass method to do the application
        results = super(PcfgChart, self)._apply_binary_rule_semantics(rule, sign_pair, category)
        
        # Add probabilities to the results
        for result in results:
            result.probability, result.inside_probability = \
                        self._binary_expansion_probability(sign_pair, result)
        return results
    
    def apply_binary_rules(self, start, middle, end, beam=True):
        # Call the super method to apply the rules
        signs_added = super(PcfgChart, self).apply_binary_rules(start, middle, end)
        
        if beam and signs_added:
            # Apply a beam to the results
            self.apply_beam((start, end))
        return signs_added
    
    def apply_binary_rule(self, rule, start, middle, end, beam=True):
        # Call the super method to apply the rule
        signs_added = super(PcfgChart, self).apply_binary_rule(rule, start, middle, end)
        
        if beam and signs_added:
            # Apply the beam to the arc that might have got results
            self.apply_beam((start, end))
        return signs_added
    
    def apply_beam(self, arc=None):
        """
        Applies a beam to every arc in the chart. If arc is given, it 
        should be a tuple of (start,end): applies a beam only to the 
        arc starting at start and ending at end.
        
        """
        if arc is not None:
            start,end = arc
            # Never beam the longest span: there's no point, as it won't be 
            #  used in any other productions
            if not (start == 0 and end == self.size):
                # Apply to a specific arc
                logger.debug("Beaming (%s,%s)" % arc)
                self._table[start][end-start-1]._apply_beam()
        else:
            # Apply to whole chart
            for i,ends in enumerate(self._table):
                for j,arcs in enumerate(ends):
                    # Exclude the longest span
                    if not (i==0 and i+j+1==self.size):
                        arcs._apply_beam()
    
    def _sign_string(self, sign):
        return "%s (%s)" % (sign, fmt_prob(2**sign.probability))

    def launch_inspector(self, input=None, block=False):
        # Inherit docs from Chart
        from .inspector import PcfgChartInspectorThread
        inspector = PcfgChartInspectorThread(self, input_strs=input)
        self.inspector = inspector
        if block:
            inspector.run()
        else:
            inspector.start()
