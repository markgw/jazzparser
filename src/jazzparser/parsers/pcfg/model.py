"""Probabilistic models for the PCFG parser.

The PCFG parser need to be able to access certain probabilities to 
parse. The interface contained in this module 
provide access to these probabilities, using a model previously 
trained on training data. The model implementation itself is provided by 
the formalism, since it needs to manipulate categories.

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
__author__ = "Mark Granroth-Wilding <mark@granroth-wilding.co.uk>" 

import os
import cPickle as pickle
from jazzparser.taggers import Tagger
from jazzparser import settings
from jazzparser.utils.options import ModuleOption
from jazzparser.utils.base import abstractmethod

FILE_EXTENSION = "mdl"

class PcfgModel(object):
    """
    A trainable model used by a pcfg parser.
    
    """
    # Subclasses should set the model type, which distinguishes its models from others
    MODEL_TYPE = None
    # Options can get passed into a model when instantiated for training
    TRAINING_OPTIONS = []
    # Input types for which the model amy be used lexically
    LEX_INPUT_TYPES = []
    
    def __init__(self, model_name, overwrite=False, options={}, 
            description=None, grammar=None):
        """
        Creates an empty, untrained model. To load a previously 
        stored model, use from_file().
        
        Optionally stores some custom descriptive text. This will be 
        included in the descriptive text that gets stored along with 
        the model.
        
        """
        self.model_name = model_name
        if overwrite and os.exists(self._filename):
            # Remove the old file if we're asked to overwrite
            if overwrite:
                os.remove(self._filename)
        self._options = None
        self._options_dict = options
        self._generate_description()
        self.model_description = description
        self.grammar = grammar
        
    @classmethod
    def __get_filename(cls, model_name):
        return os.path.join(cls._get_model_dir(), "%s.%s" % (model_name, FILE_EXTENSION))
    def __get_my_filename(self):
        return type(self).__get_filename(self.model_name)
    _filename = property(__get_my_filename)
    
    def process_training_options(self):
        """
        Verifies and processes the training option values. Access them in 
        self.options.
        
        """
        self._options = ModuleOption.process_option_dict(self._options_dict, 
                                                         self.TRAINING_OPTIONS)
    
    def _get_options(self):
        """
        Instead of processing training options when instantiating (which makes 
        it impossible to have required options, since we're not always training 
        when instantiating), we process the training options the first time 
        they're needed.
        
        If you want to do this ahead of time to verify the validity of the 
        values, call L{process_training_options}.
        
        """
        if self._options is None:
            self.process_training_options()
        return self._options
    options = property(_get_options)
    
    @classmethod
    def _get_model_dir(cls):
        return os.path.join(settings.PCFG_MODEL_DATA_DIR, cls.MODEL_TYPE)
        
    @classmethod
    def list_models(cls):
        """ Returns a list of the names of available models. """
        model_dir = cls._get_model_dir()
        if not os.path.exists(model_dir):
            return []
        model_ext = ".%s" % FILE_EXTENSION
        names = [name.rpartition(model_ext) for name in os.listdir(model_dir)]
        return [name for name,ext,right in names if ext == model_ext and len(right) == 0]
        
    def save(self):
        """ Saves the model data to a file. """
        data = {
            'data' : self._get_model_data(),
            'desc' : self._description,
            'model_desc' : self.model_description,
        }
        data = pickle.dumps(data, 2)
        filename = self._filename
        # Check the directory exists
        filedir = os.path.dirname(filename)
        if not os.path.exists(filedir):
            os.mkdir(filedir)
        f = open(filename, 'wb')
        f.write(data)
        f.close()
        
    def delete(self):
        """
        Removes all the model's data. It is assumed that the tagger 
        will not be used at all after this has been called.
        
        """
        fn = self._filename
        if os.path.exists(fn):
            os.remove(fn)
        # Get rid of any extra files that the model creates
        for filename in self.get_extra_filenames():
            if os.path.exists(filename):
                os.remove(filename)
            
    @classmethod
    def load_model(cls, model_name):
        filename = cls.__get_filename(model_name)
        # Load the model from a file
        if os.path.exists(filename):
            f = open(filename, 'rb')
            model_data = f.read()
            model_data = pickle.loads(model_data)
            f.close()
        else:
            raise ModelLoadError, "the model '%s' has not been trained" % model_name
        obj = cls._load_model(model_name, model_data['data'])
        # Load the descriptive text (stored for every model type)
        obj._description = model_data['desc']
        obj.model_description = model_data['model_desc']
        return obj
        
    def _generate_description(self):
        """
        Don't override this.
        You can add your own information into the 
        descriptive text (per subclass, for example) by calling 
        __init__ with the description kwarg, or by setting the 
        model_description attribute. You might, for example, want to 
        do this at training time.
        
        """
        from datetime import datetime
            
        desc = """\
Model type: %(type)s
Model name: %(name)s
Created: %(creation)s\
""" % \
            {
                'type' : self.MODEL_TYPE,
                'name' : self.model_name,
                'creation' : datetime.now().strftime('%d %b %Y %H:%M'),
            }
        self._description = desc
        
    def __get_description(self):
        if self.model_description is not None:
            model_desc = "\n\n%s" % self.model_description
        else:
            model_desc = ""
        return "%s%s" % (self._description,model_desc)
    description = property(__get_description)
    
    def generate(self, logger=None, max_depth=None):
        """
        Generate a surface form from the PCFG model. A pcfg model might 
        not provide an implementation of this, in which case it will 
        always return None.
        
        """
        return
    
    ############### Abstract methods #################
    @classmethod
    def _load_model(cls, name, data):
        """
        Subclasses should implement this method to load up the model 
        data given in the argument data. They should return an 
        instance of themselves. The data will be in the form of a 
        dictionary, as returned by the class' _get_model_data().
        
        A default implementation that just uses simple pickling is 
        provided.
        
        """
        obj = data
        if not isinstance(obj, cls):
            raise ModelLoadError, "loaded file, but got wrong type of object "\
                "out (%s)" % type(obj).__name__
        return obj
        
    def _get_model_data(self):
        """
        Subclasses should implement this method to return the raw data 
        of the model in a form that can be pickled and written 
        out to a file.
        
        A default implementation to complement the implementation of 
        _load_model is provided.
        
        """
        return self
    
    @staticmethod
    def train(name, training_data, options, grammar=None, logger=None):
        """
        Trains a new model using the data in the list of sequences.
        """
        raise NotImplementedError, "called train() on abstract TaggerModel"
    
    @abstractmethod
    def inside_probability(self, expansion, parent, left, right=None):
        """
        Probability of a (non-leaf) subtree, computed from the probability 
        of its expansions and the inner probabilities already associated 
        with its components. The result is the inside probability of the 
        subtree.
        
        There are several different cases. It may be a unary expansion, in 
        which case C{expansion='unary'} and C{right=None}. It may be a 
        right-head expansion: C{expansion='right'} and both C{left} and 
        C{right} daughters are given. Or it may be a left-head expansion:
        C{expansion='left'} and both daughters are given.
        
        """
        return
    
    @abstractmethod
    def outside_probability(self, parent):
        """
        Outside probability of a subtree. This is approximated in these models 
        as the prior probability of the parent of the tree.
        
        """
        return
        
class ModelLoadError(Exception):
    pass
        
class ModelSaveError(Exception):
    pass

class ModelError(Exception):
    pass

class ModelTrainingError(Exception):
    pass
