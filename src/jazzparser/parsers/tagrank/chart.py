"""Simple probabilistic extension to the CKY chart for the tagrank parser.

This is rather like the PCFG chart, but doesn't do as much - it just 
combines probabilities very naively from arguments of rule applications 
so that products of tag probabilities work their way up the tree.

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
import logging

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class TagProbabilitySignHashSet(SignHashSet):
    """
    For this chart's internal data structure, we use a modified 
    implementation of the HashSet which adds some basic handling of 
    the tag probabilities that came from the tagger's model.
    
    """
    DEFAULT_THRESHOLD = 0.001
    DEFAULT_MAX_SIZE = 50
    # The beam won't operate at all until there are this many signs on the arc
    DEFAULT_BEAMING_THRESHOLD = 20
    
    def __init__(self, *args, **kwargs):
        self.threshold = kwargs.pop('threshold', self.DEFAULT_THRESHOLD)
        self.maxsize = kwargs.pop('maxsize', self.DEFAULT_MAX_SIZE)
        self.beaming_threshold = kwargs.pop('beaming_threshold', self.DEFAULT_BEAMING_THRESHOLD)
        super(TagProbabilitySignHashSet, self).__init__(*args, **kwargs)
        
    def _add_existing_value(self, existing_value, new_value):
        # Take the max of the two probability products.
        # These aren't probabilities - don't sum them.
        # In effect, this means we're getting the probability of the
        #  most likely tag sequence that led to this sign
        existing_value.probability = max(existing_value.probability, new_value.probability)
        # Continue to do whatever the formalism wants with the signs
        super(TagProbabilitySignHashSet, self)._add_existing_value(existing_value, new_value)
        
    def _max_probability(self):
        return max([val.probability for val in self.values()]+[0.0])
        
    def _apply_beam(self):
        """
        Applies a beam, using the already given threshold, to the set,
        pruning out any signs with a probability lower than the 
        given ratio of the most probable sign.
        
        """
        if len(self) >= self.beaming_threshold:
            max_prob = self._max_probability()
            cutoff = max_prob * self.threshold
            to_remove = [sign for sign in self.values() if sign.probability < cutoff]
            for sign in to_remove:
                self.remove(sign)
            logger.debug("Beam removed %d signs (max %s, min %s)" % \
                            (len(to_remove), max_prob, cutoff))
            # Beam is now applied: check the remaining size
            if self.maxsize != 0 and len(self) > self.maxsize:
                logger.debug("Hard beam removed %d signs" % (len(self)-self.maxsize))
                # Too many signs: apply a hard cutoff
                ordered = list(sorted(self.values(), key=lambda s:s.probability))
                for sign in ordered[self.maxsize:]:
                    self.remove(sign)
            
    def ranked(self):
        """
        Returns the signs in the set ranked by tag probability product 
        (highest first).
        
        """
        return list(reversed(sorted(self.values(), key=lambda s:s.probability)))

class TagRankChart(Chart):
    """
    Overrides the CKY chart to add probabilistic stuff.
    
    Signs in the input should have an attribute 'probability'.
    The results of rule application will also have such an attribute.
    
    """
    HASH_SET_IMPL = TagProbabilitySignHashSet
    
    def __init__(self, *args, **kwargs):
        super(TagRankChart, self).__init__(*args, **kwargs)
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
        def _res_mod(result, sign):
            # Function to add the probability to each result from the input
            result.probability = sign.probability
        signs_added = super(TagRankChart, self).apply_unary_rule(rule, start, end, result_modifier=_res_mod)
        
        # Apply a beam if necessary
        if beam and signs_added:
            self.apply_beam((start,end))
        return signs_added
        
    def _apply_binary_rule(self, rule, sign_pair):
        """
        Override to provide probability propagation.
        
        See L{jazzparser.parsers.cky.chart.Chart._apply_binary_rule} 
        for full doc.
        
        """
        # Calculate the output probability product
        prob = sign_pair[0].probability * sign_pair[1].probability
        # Call the superclass method to do the application
        results = super(TagRankChart, self)._apply_binary_rule(rule, sign_pair)
        
        # Add probabilities to the results
        for result in results:
            result.probability = prob
        return results
        
    def _apply_binary_rule_semantics(self, rule, sign_pair, category):
        """
        Like _apply_binary_rule, but uses the C{apply_rule_semantics()}
        of the rule instead of C{apply_rule()}.
        
        Extends the overridden method to add probabilities.
        
        @see: jazzparser.parsers.cky.chart.Chart._apply_binary_rule_semantics
        
        """
        # Calculate the output probability product
        prob = sign_pair[0].probability * sign_pair[1].probability
        # Call the superclass method to do the application
        results = super(TagRankChart, self)._apply_binary_rule_semantics(rule, sign_pair, category)
        
        # Add probabilities to the results
        for result in results:
            result.probability = prob
        return results
    
    def apply_binary_rules(self, start, middle, end, beam=True):
        # Call the super method to apply the rules
        signs_added = super(TagRankChart, self).apply_binary_rules(start, middle, end)
        
        if beam and signs_added:
            # Apply a beam to the results
            self.apply_beam((start, end))
        return signs_added
    
    def apply_binary_rule(self, rule, start, middle, end, beam=True):
        # Call the super method to apply the rule
        signs_added = super(TagRankChart, self).apply_binary_rule(rule, start, middle, end)
        
        if beam and signs_added:
            # Apply the beam to the arc that might have got results
            self.apply_beam((start, end))
        return signs_added
    
    def apply_beam(self, arc=None):
        """
        Applies a beam to every arc in the chart. If arc is given, it 
        should be a tuple of (start,end): applies a beam only to the 
        arc starting at start and ending at end.
        Note that the beam will not be applied to any leaves (lexical 
        arcs) in the chart.
        
        """
        if arc is not None:
            start,end = arc
            if end != start + 1:
                # Apply to a specific arc
                logger.debug("Beaming (%s,%s)" % arc)
                self._table[start][end-start-1]._apply_beam()
        else:
            # Apply to whole chart
            for ends in self._table:
                for arcs in ends[1:]:
                    arcs._apply_beam()
    
    def _sign_string(self, sign):
        return "%s (%s)" % (sign, fmt_prob(sign.probability))
        
    def launch_inspector(self, input=None):
        # Inherit docs from Chart
        from .inspector import TagRankChartInspectorThread
        inspector = TagRankChartInspectorThread(self, input_strs=input)
        inspector.start()
