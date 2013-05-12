"""Base classes for supertaqger components.

This module contains the superclass of tagger components for the Jazz 
Parser. New taggers should be created by importing this and subclassing
Tagger.

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

from jazzparser import settings
from .loader import TaggerLoadError
from jazzparser.utils.options import ModuleOption
from jazzparser.utils.input import assign_durations, strip_input
from jazzparser.data import Fraction
from jazzparser.data.input import detect_input_type
from jazzparser.utils.loggers import create_dummy_logger

class Tagger(object):
    """
    The superclass of all taggers. Subclass this to create tagger components.
    
    Probabilities are returned by the tagger along with signs. These 
    are posterior probabilities for the C&C supertagging approach: 
    that is, Pr(tag | observations). For the PCFG parser approach, 
    the taggers must yield likelihoods: Pr(observation | tag). A tagger 
    of this sort should have POSTERIOR set to False.
    
    """
    COMPATIBLE_FORMALISMS = []
    TAGGER_OPTIONS = []
    """ Tagger-specific options. List of ModuleOptions. """
    INPUT_TYPES = []
    """ List of allowed input datatypes. See L{jazzparser.data.input.INPUT_TYPES}. """
    shell_tools = []
    """ Interactive shell tools available when this tagger is used. """
    LEXICAL_PROBABILITY = False
    """
    Some models provide lexical probabilities that the parsing models 
    can use. They should set this to true. They should also provide a method 
    C{lexical_probability(start_time, end_time, span_label)}.
    """
    
    def __init__(self, grammar, input, options={}, original_input=None, logger=None):
        """
        The tagger must have reference to the grammar being used to parse
        the input. It must also be given the full input when instantiated.
        The format of this input will depend on the tagger: for example,
        it might be a string or a MIDI file.
        
        @param original_input: the input in its original, unprocessed form. This 
            will usually be a string. This is optional, but in some 
            circumstances things might fall apart if it hasn't been given.
            E.g. using a backoff model as backoff from a tagging model requires 
            the original input to be passed to the backoff model.
        @param logger: optional progress logger. Logging will be sent to this 
            during initialization of the tagger and tagging. If not given, the 
            logging will be lost. Subclasses may access the logger (or a dummy 
            logger if none was given) in C{self.logger}.
        
        """
        self.grammar = grammar
        # Check the formalism is one that's allowed by this tagger
        formalism = self.grammar.formalism.get_name()
        if formalism not in self.COMPATIBLE_FORMALISMS:
            raise TaggerLoadError, "Formalism '%s' cannot be used with "\
                "tagger '%s'" % (formalism,self.name)
        
        # Check what input type we've received and preprocess it
        datatype, input = detect_input_type(input, allowed=self.INPUT_TYPES, \
                                errmess=" for use with tagger '%s'" % self.name)
        # Store this for the subclass to use as appropriate
        self.input = input
        if original_input is None:
            self.original_input = input
        else:
            self.original_input = original_input
        # Subclasses may redefine self.input to taste
        # We keep the original wrapped input somewhere where it's sure to remain
        self.wrapped_input = input
        # Initialize using tagger-specific options
        self.options = type(self).check_options(options)
        
        if logger is not None:
            self.logger = logger
        else:
            self.logger = create_dummy_logger()
        
    def _get_name(self):
        return type(self).__module__.split(".")[2]
    name = property(_get_name)
        
    def _get_input_length(self):
        """
        Should return the number of words (chords) in the input, or 
        some other measure of input length appropriate to the type of 
        tagger.
        
        """
        return len(self.input)
    input_length = property(_get_input_length)
    
    def get_signs(self, offset=0):
        """
        Returns a list of tuples C{(start, end, signtup)}. These represent spans 
        to be added to the chart, C{start} and C{end} being the start and 
        end nodes.
        
        Each signtup is a (sign,tag,probability) tuple representing a sign 
        that the tagger wishes to add to the chart in this position.
        How many are returned
        is up to the tagger (it may wish to return more in cases where there
        are no clear winners, for example).
        If the tag is not found in the grammar, sign will be None.
        
        Returned list is sorted by probability, highest first.
        
        offset may be set >0 in order to retrieve further signs once some have
        already been returned. If offset=k, the tagger should disregard 
        all the signs that would have been returned for offset<k and 
        return the next bunch - as many as it sees fit. offset is incremented
        each time the parse fails.
        
        The simplest approach, and that employed by most taggers, has some 
        signs for each word and none spanning more than one word. That is, 
        the tuples in the list would be of the form 
        C{(wordnum, wordnum+1, signtup)}. This is by no means required, though:
        some taggers will want to add multi-node spans to the chart.
        
        @note: This functionality used to be provided by C{get_signs_for_word}.
        For convenience, if a tagger provides C{get_signs_for_word} and not 
        get_signs(), the results of the former will be used to produce the 
        latter. New taggers should not do this, but override this method 
        directly.
        
        """
        if hasattr(self, "get_signs_for_word"):
            # The tagger doesn't provide get_signs(), but is an old class 
            #  that provides get_signs_for_word() instead
            # We can use the output of get_signs_for_word() to produce 
            #  the required output of get_signs()
            signs = []
            for start_node in range(self.input_length):
                word_signs = self.get_signs_for_word(start_node, offset=offset)
                for sign in word_signs:
                    signs.append((start_node, start_node+1, sign))
            return signs
        else:
            # Must be overridden
            raise NotImplementedError, "Cannot use the Tagger abstract superclass."
    
    def get_word(self, index):
        """
        Returns the input word at this index. This does not need to be 
        a string, but must have a sensible __str__, so that it can 
        be converted to a readable string.
        The purpose of this is to provide a readable form of the input 
        for the parser to store in derivation traces.
        """
        # Must be overridden
        raise NotImplementedError, "Tagger.get_word() must be overridden by tagger classes."
        
    def get_word_duration(self, index):
        """
        Returns the duration of the word at this index if durations 
        are available. Otherwise raises an AttributeError.
        
        """
        if not hasattr(self, 'durations'):
            raise AttributeError, "tagger has not stored durations. "\
                "Tried to get the duration of an input word"
        return self.durations[index]
        
    def get_string_input(self):
        """
        Returns a list of string representations of the inputs.
        This is just a convenience function, which uses whatever 
        representation gets returned by get_word() to produce a 
        representation of the whole input.
        
        """
        return [str(self.get_word(i)) for i in range(self.input_length)]
        
    def get_tag_probability(self, index, tag, end_index=None):
        """
        Returns as a float the probability with which the tagger judges 
        the given span will be assigned the given sign.
        
        If C{end_index} is not given, it defaults to C{index}+1.
        
        """
        if end_index is None:
            end_index = index+1
        # Check all the signs for a match
        all_signs = self.get_all_signs()
        
        if (index,end_index) not in all_signs:
            # The sign was not assigned at all
            return 0.0
        else:
            for __,assigned_tag,prob in all_signs[(index,end_index)]:
                if assigned_tag == tag:
                    return prob
            return 0.0
    
    def get_all_signs(self):
        """
        Gets all signs that the tagger will return, regardless of offset.
        This just uses L{get_signs} to get the signs for every offset.
        
        @rtype: dict
        @return: all the signs, keyed by (start,end) tuple
        
        """
        if not hasattr(self, "_all_signs"):
            # Compute and cache the signs list
            signs = {}
            offset = 0
            new_signs = None
            # Get all the signs by incrementing the offset until there are no more
            while new_signs is None or len(new_signs) > 0:
                new_signs = self.get_signs(offset=offset)
                # Index the signs by their span tuple
                for (start,end,sign) in new_signs:
                    signs.setdefault((start,end), []).append(sign)
                offset += 1
            self._all_signs = signs
        return self._all_signs
    
    @classmethod
    def check_options(cls, options):
        """
        Normally, options are validated when the tagger is instantiated. 
        This allows you to check them before that.
        
        """
        return ModuleOption.process_option_dict(options, cls.TAGGER_OPTIONS)
        
def process_chord_input(tagger):
    """
    Convenience function for taggers that accept chord input.
    
    All taggers that handle chord sequence input do the same 
    preprocessing to the input argument. This function is called to 
    handle string or database input which has already been preprocessed 
    by the Tagger superclass.
    
    It is called by the __init__ of the taggers.
    
    """
    from jazzparser.data.input import DbInput, WeightedChordLabelInput, \
                            ChordInput
    
    inobj = tagger.wrapped_input
    if isinstance(inobj, ChordInput):
        inobj = inobj.to_db_input()
    
    if isinstance(inobj, DbInput):
        tagger.input = inobj.inputs
        tagger.times = inobj.times
        tagger.durations = inobj.durations
    elif isinstance(inobj, WeightedChordLabelInput):
        tagger.times = list(range(len(inobj)))
        tagger.durations = [1]*len(inobj)
    else:
        raise TypeError, "process_chord_input was called on input of type "\
            "%s. It's only meant for chord,  db and lattice inputs" % \
            type(inobj).__name__
