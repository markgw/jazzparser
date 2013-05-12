"""Base classes for in-house statistical models.

Supertagger components that use statistical models that are implemented 
within the Jazz Parser should use the baseclasses provided here.
They then only need to implement a model class, with a training method, 
and the usual tagger interface.

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

FILE_EXTENSION = "mdl"

class ModelTagger(Tagger):
    """
    Base class for corpus-trained supertagging models. Provides 
    interface and common methods for model classes, which must each 
    provide their own training methods and the usual tagger methods 
    (get_signs, etc).
    
    The main thing this provides is stuff for storing and retreiving 
    models.
    
    """
    COMPATIBLE_FORMALISMS = [ 'music_keyspan', 'music_halfspan' ]
    # When subclassing, make sure to include this in the options if you override
    TAGGER_OPTIONS = [
        ModuleOption('model', filter=str, 
            help_text="Model name. This model must have been previously trained. Required",
            usage="model=X, where X is the name of a trained model",
            required=True),
        ModuleOption('partition', filter=int, 
            help_text="If given, a partitioned version of the model will "\
                "be used, taking the model name as the base name. The "\
                "partitioned models must have been trained separately.",
            usage="partition=P, where P is an int",
            default=None),
        ModuleOption('batch', filter=float, 
            help_text="Probability ratio between one tag and the next "\
                "that allows the second to be returned in the same batch.",
            usage="batch=X, where X is a floating point value between 0 and 1",
            default=0.8),
        ModuleOption('max_batch', filter=int, 
            help_text="Maximum number of tags to include in a single batch, "\
                "regardless of whether they fall within the beam ratio (see "\
                "batch). 0 (default) means no limit.",
            usage="max_batch=X, where X is an int",
            default=0),
        ModuleOption('best', filter=lambda x: x.lower() != "false", 
            help_text="If true, only the highest probability sign will "\
                "be used for each word.",
            usage="best=X, where X is 'True' or 'False'",
            default=False),
    ]
    # Subclasses should use this to specify a subclass of TaggerModel to use
    MODEL_CLASS = None
    
    def __init__(self, *args, **kwargs):
        super(ModelTagger, self).__init__(*args, **kwargs)
        # Check the subclass is properly defined
        if type(self).MODEL_CLASS is None:
            raise NotImplementedError, "ModelTagger subclass %s does not define a model class" % type(self).__name__
        # Get the partitioned model name if necessary
        if self.options['partition'] is not None:
            self.model_name = type(self).partition_model_name(
                                                self.options['model'],
                                                self.options['partition'])
        else:
            self.model_name = self.options['model']
        self.logger.info("Tagging model: %s" % self.model_name)
        # Load a TaggerModel subclass instance to load the trained model data
        self.model = (type(self).MODEL_CLASS).load_model(self.model_name)
        
        self.batch_ratio = self.options['batch']
        self.best_only = self.options['best']
        # After calling this, subclasses should perform tagging on the input
        
    @staticmethod
    def partition_model_name(model_name, partition_number):
        """
        The model name to use when the given partition number is requested. 
        The default implementation simply appends the number to the model 
        name. Subclasses may override this if they want to do something 
        different.
        
        """
        return "%s%d" % (model_name, partition_number)
        
class TaggerModel(object):
    """
    A trainable model used by a ModelTagger.
    
    """
    # Subclasses should set the model type, which distinguishes its models from others
    MODEL_TYPE = None
    # Options can get passed into a model when instantiated for training
    TRAINING_OPTIONS = []
    
    def __init__(self, model_name, overwrite=False, options={}, description=None):
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
    
    def get_extra_filenames(self):
        """
        Should return a list of all the files that are stored along 
        with the main model file (not including the main file).
        
        By default this is an empty list, but some subclasses may want 
        to put some names in this list. These should just be filenames,
        not full paths. The files are assumed to be in the model type's 
        directory.
        
        """
        return []
    
    @classmethod
    def _get_model_dir(cls):
        if cls.MODEL_TYPE is None:
            raise NotImplementedError, "cannot load model: %s has not set a model type name" % cls.__name__
        return os.path.join(settings.MODEL_DATA_DIR, cls.MODEL_TYPE)
        
    @classmethod
    def list_models(cls):
        """
        Returns a list of the names of available models.
        
        """
        model_dir = cls._get_model_dir()
        if not os.path.exists(model_dir):
            return []
        model_ext = ".%s" % FILE_EXTENSION
        names = [name.rpartition(model_ext) for name in os.listdir(model_dir)]
        return [name for name,ext,right in names if ext == model_ext and len(right) == 0]
        
    def save(self):
        """
        Saves the model data to a file.
        """
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
        obj = cls._load_model(model_data['data'])
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
    
    ############### Abstract methods #################
    @classmethod
    def _load_model(cls,data):
        """
        Subclasses should implement this method to load up the model 
        data given in the argument data. They should return an 
        instance of themselves. The data will be in the form of a 
        dictionary, as returned by the class' _get_model_data().
        
        A default implementation that just uses simple pickling is 
        provided. It assumes that the class can be instantiated using 
        no arguments.
        
        """
        obj = data
        if not isinstance(obj, cls):
            raise ModelLoadError, "loaded file, but got wrong type of object out (%s)" % type(obj).__name__
        return obj
        
    def _get_model_data(self):
        """
        Subclasses should implement this method to return the raw data 
        of the model in a form that can be pickled and written 
        out to a file.
        
        A default implementation to complement the implementation of 
        _load_model is provided.
        
        *** IMPORTANT: ***
        Some implementations perform part of the model storage in their 
        _get_model_data method, so you shouldn't use this just to 
        get the data if you don't plan to store it. (Not sure why you'd 
        want the raw data anyway and this is a private method - just 
        warning you!)
        
        """
        return self
    
    def train(self, sequence_index, grammar=None, logger=None):
        """
        Trains the loaded model using the data in the list of sequences.
        """
        raise NotImplementedError, "called train() on abstract TaggerModel"
        
class ModelLoadError(Exception):
    pass
        
class ModelSaveError(Exception):
    pass
    
class TaggingModelError(Exception):
    """
    For errors encountered while tagging using a model. Usually 
    indicates something's wrong with the model or the way it's being
    used.
    
    """
    pass
