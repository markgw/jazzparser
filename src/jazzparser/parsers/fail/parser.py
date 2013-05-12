"""A parser that always fails to find a result.

This is a dummy parser that allows other components to be tested in their 
natural habitat without a parser getting in the way.

It just keeps requesting signs from the supertagger until it has none 
left and then fails.

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

import logging

from jazzparser.utils.base import filter_latex, ExecutionTimer
from jazzparser.parsers.cky.parser import CkyParser, ParserTimeout

from jazzparser import settings

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class FailParser(CkyParser):
    """
    A dummy parser that never does any actual parsing.
    
    """
    def parse(self, derivations=False, summaries=False, inspect=False):
        # Find out from the tagger how long the input it read in was
        input_length = self.tagger.input_length
        # Create and initialise a chart for parsing
        # Don't initialise the chart with signs - we'll add signs gradually instead
        chart = self._create_chart(
                                [[]]*input_length,
                                derivations=derivations)
        
        # Stop after a given number of iterations
        if self.options['max_iter'] == 0:
            max_iter = None
        else:
            max_iter = self.options['max_iter']
        timeout = 60*self.options['timeout']
        check_timeout = timeout>0
        
        # This is where progress output will go
        # Note that it's not the same as logger, which is the main system logger
        prog_logger = self.logger
        
        if check_timeout:
            prog_logger.info("Due to timeout after %d mins" % self.options['timeout'])
        
        ##################################################
        ### The dummy parse loop
        # Keep track of how long since we started for timing out
        timeout_timer = ExecutionTimer()
        
        signs_added = True
        offset = 0
        try:
            # Keep adding signs until none left
            while len(chart.get_signs(0, input_length)) == 0 and signs_added:
                if max_iter is not None and offset >= max_iter:
                    # Exceded maximum number of iterations: give up
                    prog_logger.info("Reached maximum number of iterations: "\
                                        "continuing to backoff/fail")
                    break
                prog_logger.info(">>> Parsing iteration: %d" % (offset+1))
                
                # Get new signs from the tagger
                added = self._add_signs(offset=offset)
                # Note whether we added anything new
                signs_added = bool(added)
    
                # Check whether the timeout has expired
                if check_timeout:
                    if int(timeout_timer.get_time()) > timeout:
                        raise ParserTimeout
                # Don't do any parsing: just go round again to get more signs
                offset += 1
        except ParserTimeout:
            # The given timeout elapsed: just continue with no parses
            logger.debug("Parse loop timeout (%d mins) expired" % self.options['timeout'])
            prog_logger.info("Parse timeout (%d mins) expired: continuing "\
                            "to backoff/fail" % self.options['timeout'])
        
        parses = []
        # If a backoff model was given, always use it now
        if self.backoff is not None:
            backoff_results = self.run_backoff()
            if len(backoff_results) > 0:
                for res in backoff_results:
                    # Put the semantics result into a sign, with a dummy 
                    #  syntactic category
                    sign = self.grammar.formalism.Syntax.Sign(
                                self.grammar.formalism.Syntax.DummyCategory(),
                                res)
                    # If the semantics has a probability, put this on the sign
                    if hasattr(res, "probability"):
                        sign.probability = res.probability
                    parses.append(sign)
        
        return parses
