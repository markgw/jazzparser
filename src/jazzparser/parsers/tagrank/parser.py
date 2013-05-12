"""Simple extension of a CKY parser to propagate probabilities 
through a derivation from the tag probabilities.

This is not really a probabilistic parser, it's just a basic CKY 
parser with some extra bits to pass probabilities up through a 
derivation from the tags. It's designed to be used with the C&C 
tagger, so that the results get ranked according to the probabilities 
of the tags they came from.

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

from jazzparser.parsers.cky.parser import CkyParser
from jazzparser.parsers.pcfg.tools import ProbabilisticResultListTool, ProbabilityTool, ProbabilisticChartTool
from jazzparser.parsers.cky.tools import ChartTool

from .chart import TagRankChart

import sys, re
import logging

from jazzparser import settings

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class TagRankParser(CkyParser):
    shell_tools = [
        ChartTool(),
        # The PCFG parser provides some handy probability tools
        ProbabilisticResultListTool(),
        ProbabilityTool(),
        ProbabilisticChartTool(),
    ]
    
    def _create_chart(self, *args, **kwargs):
        self.chart = TagRankChart(self.grammar, *args, **kwargs)
        return self.chart
        
    def _add_signs(self, offset):
        vals = super(TagRankParser, self)._add_signs(offset) or []
        for (start,end,signtup) in vals:
            if signtup[0] is None:
                continue
            # Add the probabilities as an attribute to the signs
            cat,tag,prob = signtup
            cat.probability = prob
        return vals
            
    def parse(self, *args, **kwargs):
        """
        Performs a full parse and returns the results ranked by 
        a product of their tag probabilities.
        
        """
        parses = super(TagRankParser, self).parse(*args, **kwargs)
        # If parses were found, use the ranked version of them
        if len(self.chart.parses) > 0:
            return self.chart.ranked_parses
        else:
            # No parses, but the backoff could have given something
            return parses
