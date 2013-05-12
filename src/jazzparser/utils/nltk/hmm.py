"""Tools to extend NLTK's implementation of HMMs.

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


# The NLTK import has already been checked in our __init__.py
from nltk.tag.hmm import HiddenMarkovModelTrainer, HiddenMarkovModelTagger
from jazzparser.utils.nltk.storage import ObjectStorer

class PicklableHmmTrainer(HiddenMarkovModelTrainer):
    """
    We override HiddenMarkovModelTrainer to overcome the fact that it 
    produces HMMs that can't be pickled. We only make supervised 
    trained HMMs picklable at the moment.
    
    This is quite a nasty hack to overcome the fact that NLTK HMMs 
    can't be stored and also can't be pickled if constructed using the 
    default trainer. However, this is not very stable, since someone 
    could, for example, set some attribute of the model to be a Python 
    lambda and pickling would once again fail.
    
    """
    def train_supervised(self, *args, **kwargs):
        """
        If you set 'estimator' in the kwargs, make sure it's a top-level 
        named function, not a lambda, or else you won't be able to pickle
        your HMM.
        
        """
        from jazzparser.utils.nltk.probability import mle_estimator
        estimator = kwargs.get('estimator')
        if estimator is None:
            estimator = mle_estimator
        kwargs['estimator'] = estimator
        return super(PicklableHmmTrainer, self).train_supervised(*args, **kwargs)

class HiddenMarkovModelTaggerStorer(ObjectStorer):
    STORED_CLASS = HiddenMarkovModelTagger
    
    @staticmethod
    def _object_to_dict(obj):
        from .storage import object_to_dict
        data = {}
        # The states and symbols are just dicts of strings, so we're 
        #  fine to leave them as they are
        data['states'] = obj._states
        data['symbols'] = obj._symbols
        # The prior distribution is a FreqDist, which needs to be processed
        data['priors'] = object_to_dict(obj._priors)
        # The outputs and transitions are ConditionalProbDists
        data['outputs'] = object_to_dict(obj._outputs)
        data['transitions'] = object_to_dict(obj._transitions)
        return data
        
    @staticmethod
    def _dict_to_object(dic):
        from .storage import dict_to_object
        states = dic['states']
        symbols = dic['symbols']
        priors = dict_to_object(dic['priors'])
        outputs = dict_to_object(dic['outputs'])
        transitions = dict_to_object(dic['transitions'])
        return HiddenMarkovModelTagger(symbols, states, transitions, outputs, priors)
