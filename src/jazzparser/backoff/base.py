"""Base classes for grammarless tonal space models.

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

import os
from jazzparser import settings
from jazzparser.taggers.models import TaggerModel
from jazzparser.utils.options import ModuleOption
from jazzparser.data.input import detect_input_type
from jazzparser.utils.loggers import create_plain_stderr_logger

class BackoffModel(TaggerModel):
    """
    A model to be used by a L{BackoffBuilder}.
    
    The model-handling interface is inherited directly from 
    L{TaggerModel<jazzparser.taggers.models.TaggerModel>} and simply 
    stores the models to a different location.
    
    @note: if you're subclassing this, take a look at the 
    L{TaggerModel<jazzparser.taggers.models.TaggerModel>} interface 
    for requirements.
    
    """
    @classmethod
    def _get_model_dir(cls):
        if cls.MODEL_TYPE is None:
            raise NotImplementedError, "cannot load model: %s has not set a model type name" % cls.__name__
        return os.path.join(settings.BACKOFF_MODEL_DATA_DIR, cls.MODEL_TYPE)


class BackoffBuilder(object):
    """
    Defines the interface and common functions for models that assign 
    a semantics directly to an input sequence.
    
    The evaluation interface is similar to the 
    L{Tagger<jazzparser.taggers.Tagger>} interface.
    
    """
    # When subclassing, make sure to include this in the options if you override
    BUILDER_OPTIONS = []
    
    def __init__(self, input, options={}, logger=None):
        # Initialize using tagger-specific options
        self.options = type(self).check_options(options)
        # Check what input type we've received and preprocess it
        datatype, input = detect_input_type(input, allowed=self.INPUT_TYPES)
        # Store this for the subclass to use as appropriate
        self.input = input
        self.original_input = input
        # Subclasses may redefine self.input to taste
        # We keep the original wrapped input somewhere where it's sure to remain
        self.wrapped_input = input
        # Make sure we have some logger
        if logger is None:
            # Output to stderr instead
            self.logger = create_plain_stderr_logger()
        else:
            self.logger = logger
    
    @classmethod
    def check_options(cls, options):
        return ModuleOption.process_option_dict(options, cls.BUILDER_OPTIONS)
        
    @property
    def num_paths(self):
        return 0
        
    def _get_name(self):
        return type(self).__module__.rpartition(".")[2]
    name = property(_get_name)
        
    def _get_input_length(self):
        """
        Should return the number of words (chords) in the input, or 
        some other measure of input length appropriate to the type of 
        input.
        
        """
        return len(self.input)
    input_length = property(_get_input_length)
    
    def get_tonal_space_path(self, rank=0):
        """
        This is the main interface method.
        
        @type rank: int
        @param rank: the rank of the path the get, where 0 is the 
            highest ranked path
        
        @rtype: L{jazzparser.formalisms.base.semantics.lambdacalc.Semantics} 
            subclass instance
        @return: the C{rank}th highest ranked path through the tonal 
            space for this sequence. Returns C{None} if there is no 
            path with this rank.
        
        """
        raise NotImplementedError, "called get_tonal_space_path() on "\
            "base BackoffBuilder instance."
    
    def get_all_paths(self):
        """
        Gets a list of all the tonal space paths, highest rank first.
        Just a convenience method to get all the paths using 
        L{get_tonal_space_path} for every rank (self.num_paths).
        
        """
        return [self.get_tonal_space_path(i) for i in range(self.num_paths)]


class ModelBackoffBuilder(BackoffBuilder):
    """
    Subclass of L{BackoffBuilder} that handles model loading.
    
    """
    MODEL_CLASS = None  # This should be set by subclasses
    
    BUILDER_OPTIONS = BackoffBuilder.BUILDER_OPTIONS + [
        ModuleOption('model', filter=str, 
            help_text="Model name. This model must have been previously trained. Required",
            usage="model=X, where X is the name of a trained model",
            required=True),
        ModuleOption('partition', filter=int,
            help_text="If given, the numbered partition of the partitioned "\
                "model will be used. (This generally involves appending the "\
                "partition number to the model name.)",
            usage="partition=P, where P is an int",
            default=None
        ),
    ]
    
    def __init__(self, *args, **kwargs):
        BackoffBuilder.__init__(self, *args, **kwargs)
        # Check the subclass is properly defined
        if type(self).MODEL_CLASS is None:
            raise NotImplementedError, "BackoffBuilder "\
                "subclass %s does not define a model class" % type(self).__name__
        if self.options['partition'] is not None:
            self.model_name = type(self).partition_model_name(
                                                self.options['model'],
                                                self.options['partition'])
        else:
            self.model_name = self.options['model']
        self.logger.info("Backoff model: %s" % self.model_name)
        
        # Load a TaggerModel subclass instance to load the trained model data
        self.model = (type(self).MODEL_CLASS).load_model(self.model_name)
        
    @staticmethod
    def partition_model_name(model_name, partition_number):
        """
        The model name to use when the given partition number is requested. 
        The default implementation simply appends the number to the model 
        name. Subclasses may override this if they want to do something 
        different.
        
        """
        return "%s%d" % (model_name, partition_number)


def merge_repeated_points(path):
    """
    A tonal space path, represented as a list of TonalDenotations, 
    gets generated by the models. It may be sensible for a model to 
    generate exactly one point per chord, in which case repeated 
    points ought to be removed from the path before evaluating.
    
    This removes repeated points and returns the result.
    
    """
    new_path = [path[0]]
    last_point = path[0]
    
    for point in path[1:]:
        if last_point.root_number != point.root_number or \
                last_point.function != point.function:
            new_path.append(point)
    return new_path
