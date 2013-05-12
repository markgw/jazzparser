"""Probabilistic (PCFG) extension to the CKY parser implementation.

This implements the CCG equivalent of a basic PCFG parser.
It is modelling on Julia Hockenmaier's original basic model of 2001.

@note: This used to have to be used with the PCFG tagger, which took care of 
assigning lexical probabilities, using the same model as the parser. This has 
now changed. You can use this with any tagger to limit the choice of available 
signs and the probabilities used will be taken by the parser from the 
parsing model.

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

from jazzparser.grammar import Grammar
from jazzparser.utils.input import assign_durations
from jazzparser.utils.base import filter_latex, comb
from jazzparser.utils.options import ModuleOption, zero_to_one_float
from jazzparser.utils.strings import str_to_bool
from jazzparser.utils.nltk.probability import logprob
from .chart import PcfgChart
from jazzparser.parsers.cky.parser import CkyParser
from jazzparser.parsers.cky.tools import ChartTool
from jazzparser.parsers import ParserInitializationError, ParseError
from jazzparser.data import Chord
from .chart import ProbabilisticSignHashSet
from .tools import ProbabilisticResultListTool, ProbabilityTool, \
    ProbabilisticChartTool, ProbabilisticDerivationTraceTool

import sys, re
import logging

from jazzparser import settings

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class PcfgParser(CkyParser):
    """
    """
    shell_tools = CkyParser.shell_tools + [
        ProbabilisticResultListTool(),
        ProbabilityTool(),
        ProbabilisticChartTool(),
        ProbabilisticDerivationTraceTool(),
    ]
    
    PARSER_OPTIONS = CkyParser.PARSER_OPTIONS + [
        ModuleOption('threshold', filter=zero_to_one_float,
            help_text="Ratio between the highest probability on an arc "\
                "and the probability of a new sign below which the new "\
                "sign will be ignored. (Lower throws away more and runs faster.)",
            usage="threshold=X, where X is a float between 0 and 1 (default %s)."\
                % settings.PCFG_PARSER.DEFAULT_THRESHOLD,
            default=settings.PCFG_PARSER.DEFAULT_THRESHOLD
        ),
        ModuleOption('maxarc', filter=int,
            help_text="An absolute maximum on the number of signs on an "\
                "arc. If an arc gets more signs than this even after the "\
                "beam is applied, the lowest probability signs will just "\
                "be dropped. Set to 0 to enforce no maximum at all.",
            usage="maxarc=X, where X is an integer (default %d)."\
                % settings.PCFG_PARSER.DEFAULT_MAX_ARC_SIZE,
            default=settings.PCFG_PARSER.DEFAULT_MAX_ARC_SIZE
        ),
        ModuleOption('model', filter=str,
            help_text="Name of a trained PCFG model to use for parsing.",
            usage="model=X, where X is the name of the model.",
            required=True
        ),
        ModuleOption('partition', filter=int,
            help_text="If given, the numbered partition of the partitioned "\
                "model will be used. (This generally involves appending the "\
                "partition number to the model name.)",
            usage="partition=P, where P is an int",
            default=None
        ),
        ModuleOption('nolex', filter=str_to_bool,
            help_text="Ignore lexical probabilities in model and force it "\
                "not to be a lexical model, even if it was trained with "\
                "lexical probabilities. Some input types force nolex to be "\
                "true. In these cases, this option will be overridden. "\
                "If the tagger is able to supply lexical probabilities, "\
                "these will be used instead of the model's probabilities, but "\
                "only if nolex=False",
            usage="nolex=B, where B is 'true' or 'false'",
            default=False,
        ),
        ModuleOption('viterbi', filter=str_to_bool,
            help_text="Perform viterbi parsing, using only the syntactic types "\
                "and ignoring the logical forms, to find the most probable "\
                "syntactic derivation, with its associated logical form",
            usage="viterbi=B, where B is 'true' or 'false'",
            default=False,
        ),
    ]
    
    def _create_chart(self, *args, **kwargs):
        kwargs['threshold'] = self.options['threshold']
        kwargs['maxarc'] = self.options['maxarc']
        kwargs['model'] = self.model
        kwargs['viterbi'] = self.options['viterbi']
        self.chart = PcfgChart(self.grammar, *args, **kwargs)
        return self.chart
        
    def _add_signs(self, offset):
        # Use our PCFG model to get lexical probabilities for all signs
        def prob_adder(start, end, signtup, words):
            sign, tag, tag_prob = signtup
            if self.use_tagger_probs:
                # Use the tagger to get lexical probabilities
                lex_prob = self.tagger.lexical_probability(start, end, tag)
            else:
                # We might get multiple words here: use the first
                # This is not really a satisfactory solution: better would be 
                #  to get the tagger to tell us which word to use
                if isinstance(words, list):
                    word = words[0]
                elif not isinstance(words, basestring):
                    # Check the word is a string
                    # If not, we probably shouldn't be trying to get a probability
                    raise ParseError, "PCFG model is trying to assign lexical "\
                        "probabilities to words, but the words aren't strings. "\
                        "Maybe you should have disabled lexical probs wtih "\
                        "parser option 'nolex'"
                else:
                    word = words
                # Consult the model to get the lexical probability of this sign
                lex_prob = self.model.inside_probability('leaf', sign, word)
            # Triangular number: nodes in the tree for multiword categories
            # This has the effect of penalizing multiword categories 
            #  proportionally to the number of tree nodes deriving the 
            #  categories they're competing with derived from single-word cats
            tree_size = comb(end-start+1, 2)
            lex_prob = lex_prob ** tree_size
            # Add the probabilities to the category
            sign.inside_probability = logprob(lex_prob)
            sign.probability = logprob(self.model.outside_probability(sign)) \
                                + sign.inside_probability
        # Call the CkyParser's method to get the basic tuples
        vals = super(PcfgParser, self)._add_signs(offset, prob_adder=prob_adder)
        return vals
        
    def __init__(self, *args, **kwargs):
        super(PcfgParser, self).__init__(*args, **kwargs)
        # Check that the formalism in use provides what we need to use this parser
        f = self.grammar.formalism
        if not hasattr(f, 'PcfgParser'):
            raise ParserInitializationError, "PcfgParser is not compatible "\
                "with the formalism %s" % f.get_name()
        # Load the PCFG probabilistic model
        if self.options['partition'] is not None:
            model_name = type(self).partition_model_name(self.options['model'], 
                                                    self.options['partition'])
        else:
            model_name = self.options['model']
        self.model = self.grammar.formalism.PcfgModel.load_model(self.options['model'])
        self.logger.info("Parsing model: %s" % model_name)
        
        self.use_tagger_probs = False
        self.model.lexical = True
        if not isinstance(self.tagger.wrapped_input, tuple(self.model.LEX_INPUT_TYPES)) \
                and not self.tagger.LEXICAL_PROBABILITY:
            # Model has to be non-lexical, since it's not an allowed lexical type
            self.model.lexical = False
            if not self.options['nolex']:
                # The user wasn't expecting this: warn them
                self.logger.warn("Could not use a lexical PCFG model with "\
                    "input type '%s'" % type(self.tagger.wrapped_input).__name__)
        elif self.options['nolex']:
            # Force the model to be non-lexical
            self.model.lexical = False
        elif self.tagger.LEXICAL_PROBABILITY:
            # The tagger can supply us with probabilities instead of the model's
            self.use_tagger_probs = True
    
    @staticmethod
    def partition_model_name(model_name, partition_number):
        """
        The model name to use when the given partition number is requested. 
        The default implementation simply appends the number to the model 
        name. Subclasses may override this if they want to do something 
        different.
        
        """
        return "%s%d" % (model_name, partition_number)
            
    def parse(self, *args, **kwargs):
        """
        Performs a full parse and returns the results ranked by 
        probability.
        
        """
        parses = super(PcfgParser, self).parse(*args, **kwargs)
        # Rank the parses
        # We can't use chart.ranked_parses because the parse might return parses 
        #  not from the chart (as in the case of backoff)
        return list(reversed(sorted(parses, key=lambda s:s.probability)))
