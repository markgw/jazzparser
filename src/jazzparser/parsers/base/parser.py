"""Parser module common base class.

This provides the common base classes for parser modules.

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

from jazzparser.utils.options import ModuleOption
from jazzparser.utils.loggers import create_plain_stderr_logger
from .. import ParseError

class Parser(object):
    """
    Base class for all parsers.
    """
    shell_tools = []
    # Parser-specific options. List of ModuleOptions
    PARSER_OPTIONS = []
    
    def __init__(self, grammar, tagger, options={}, backoff=None, 
                    backoff_options={}, logger=None):
        """
        @param grammar: the L{jazzparser.grammar.Grammar} instance to use for 
            parsing
        @param tagger: the L{jazzparser.taggers.tagger.Tagger} subclass 
            instance to use to tag the input
        @param backoff: an optional 
            L{jazzparser.backoff.base.BackoffBuilder} class 
            to use as a fallback if the parser returns no parses. Whether 
            this is used and in what circumstances depends on the type of 
            parser.
        @param backoff_options: dictionary of options to pass to the backoff 
            model if it gets used.
        @type logger: C{logging.Logger}
        @param logger: a logger to which all progress information during 
            parsing will be written. By default, outputs to stderr.
        
        """
        self.grammar = grammar
        self.tagger = tagger
        self.backoff_options = backoff_options
        if backoff is not None:
            # Look up the backoff model if one is requested
            self.backoff = backoff
            # Pre-check the options dict
            # This will be done again by the module when instantiated, but 
            #  we do it now to verify the options
            ModuleOption.process_option_dict(backoff_options, 
                                             backoff.BUILDER_OPTIONS)
        else:
            self.backoff = None
        # Initialize using parser-specific options
        self.options = type(self).check_options(options)
        
        if logger is None:
            # Output to stderr instead
            self.logger = create_plain_stderr_logger()
        else:
            self.logger = logger
        
        self.timed_out = False
        
    def parse(self, derivations=False, summaries=False):
        """
        Should be implemented by subclasses.
        """
        raise NotImplementedError, "Parser.parse() should be implemented by parser subclasses."
    
    def run_backoff(self):
        """
        Convenience method. Uses the backoff model on the input supplied 
        to the tagger and returns the results. If no backoff model has been 
        given, returns an empty list.
        
        """
        if self.backoff is None:
            return []
        if self.tagger.original_input is None:
            raise ParseError, "tagger %s did not store the input in its "\
                        "original form, so we can't now use a backoff model" % \
                        type(self.tagger).__name__
        builder = self.backoff(self.tagger.original_input, 
                               options=self.backoff_options,
                               logger=self.logger)
        return builder.get_all_paths()
    
    @classmethod
    def check_options(cls, options):
        """
        In normal parser usage, the options dictionary is checked for 
        validity when the parser is instantiated. In this interface, you may 
        want to check the options before this point using this method.
        
        """
        return ModuleOption.process_option_dict(options, cls.PARSER_OPTIONS)
