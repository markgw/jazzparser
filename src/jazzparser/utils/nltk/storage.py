"""Elaborate ruse to allow NLTK's probability models to be stored to disk.

NLTK's classes can't all be pickled and it doesn't provide any other 
way of storing things like probability distributions. This module 
provides procedures to produce a picklable representation of various 
NLTK classes.

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

from nltk.probability import MLEProbDist, FreqDist, ConditionalFreqDist, \
                    ConditionalProbDist, LaplaceProbDist, WittenBellProbDist, \
                    GoodTuringProbDist, DictionaryProbDist, \
                    DictionaryConditionalProbDist, MutableProbDist
import cPickle as pickle
    
def is_picklable(obj):
    """
    Returns True is the given object can be successfully pickled, 
    False otherwise. This is just a neat way of catching a pickling 
    error and usually you'll be better off trying to pickle and 
    catching the exception.
    
    """
    try:
        # Try pickling
        pickle.dumps(obj)
    except pickle.PicklingError:
        # Pickling failed!
        return False
    return True

class ObjectStorer(object):
    """
    Interface for various storers that take certain types of objects 
    and produce a dictionary with the essential data needed to recreate 
    them. The dict's values should all be picklable.
    
    The purpose of this is to define a storable form of NLTK's things 
    that don't have any storable representation.
    
    """
    STORED_CLASS = None
    
    @classmethod
    def object_to_dict(cls, obj):
        if not isinstance(obj, cls.STORED_CLASS):
            raise ObjectStorerError, "%s can only "\
                "store objects of type %s, not %s" % \
                (cls.__name__, cls.STORED_CLASS.__name__, type(obj).__name__)
        dic = cls._object_to_dict(obj)
        # Keep a record of the type of this
        dic['_type'] = cls.STORED_CLASS
        return dic
        
    @classmethod
    def dict_to_object(cls, dic):
        return cls._dict_to_object(dic)
        
    @staticmethod
    def _object_to_dict(obj):
        raise NotImplementedError, "this storer should implement a dict_from_object method"
        
    @staticmethod
    def _dict_to_object(dic):
        raise NotImplementedError, "this storer should implement a dict_from_object method"
    
class ObjectStorerError(Exception):
    pass


################## Basic storers for probability things ################

class FreqDistStorer(ObjectStorer):
    STORED_CLASS = FreqDist
    
    @staticmethod
    def _object_to_dict(obj):
        data = {}
        data['counts'] = dict(obj)
        return data
        
    @staticmethod
    def _dict_to_object(dic, start_dist=None):
        # This is so that storers for overriding classes can call this
        if start_dist is None:
            dist = FreqDist()
        else:
            dist = start_dist
        
        # Add the counts one by one so that the FreqDist gets properly built
        for key,val in dic['counts'].items():
            dist[key] = val
        return dist

class ConditionalProbDistStorer(ObjectStorer):
    STORED_CLASS = ConditionalProbDist
    
    @staticmethod
    def _object_to_dict(obj):
        data = {}
        # We don't know what type this is
        # We hope it's picklable
        if not is_picklable(obj._probdist_factory):
            raise ObjectStorerError, "The probdist factory on the "\
                "ConditionalProbDist is not picklable: %s" % type(obj._probdist_factory).__name__
        if not is_picklable(obj._factory_args) or not is_picklable(obj._factory_kw_args):
            raise ObjectStorerError, "Something in the probdist "\
                "factory's args on the ConditionalProbDist is not "\
                "picklable. They are: %s and %s" % (obj._factory_args, obj._factory_kw_args)
        data['probdist_factory'] = obj._probdist_factory
        data['cfdist'] = object_to_dict(obj._cfdist)
        data['factory_args'] = obj._factory_args
        data['factory_kw_args'] = obj._factory_kw_args
        return data
        
    @staticmethod
    def _dict_to_object(dic):
        return ConditionalProbDist(
                        dict_to_object(dic['cfdist']),
                        dic['probdist_factory'],
                        *dic['factory_args'],
                        **dic['factory_kw_args'])

class MLEProbDistStorer(ObjectStorer):
    STORED_CLASS = MLEProbDist
    
    @staticmethod
    def _object_to_dict(obj):
        return {
            'freqdist' : object_to_dict(obj._freqdist),
        }
        
    @staticmethod
    def _dict_to_object(dic):
        freqdist = dict_to_object(dic['freqdist'])
        return MLEProbDist(freqdist)

class LaplaceProbDistStorer(ObjectStorer):
    STORED_CLASS = LaplaceProbDist
    
    @staticmethod
    def _object_to_dict(obj):
        return {
            'freqdist' : object_to_dict(obj._freqdist),
            'bins' : obj._bins,
        }
        
    @staticmethod
    def _dict_to_object(dic):
        freqdist = dict_to_object(dic['freqdist'])
        bins = dic['bins']
        return LaplaceProbDist(freqdist, bins)

class WittenBellProbDistStorer(ObjectStorer):
    STORED_CLASS = WittenBellProbDist
    
    @staticmethod
    def _object_to_dict(obj):
        return {
            'freqdist' : object_to_dict(obj._freqdist),
            'bins' : obj._Z + obj._T,
        }
        
    @staticmethod
    def _dict_to_object(dic):
        freqdist = dict_to_object(dic['freqdist'])
        bins = dic['bins']
        return WittenBellProbDist(freqdist, bins)

class GoodTuringProbDistStorer(ObjectStorer):
    STORED_CLASS = GoodTuringProbDist
    
    @staticmethod
    def _object_to_dict(obj):
        return {
            'freqdist' : object_to_dict(obj._freqdist),
            'bins' : obj._bins,
        }
        
    @staticmethod
    def _dict_to_object(dic):
        freqdist = dict_to_object(dic['freqdist'])
        bins = dic['bins']
        return GoodTuringProbDist(freqdist, bins)

class ConditionalFreqDistStorer(ObjectStorer):
    STORED_CLASS = ConditionalFreqDist
    
    @staticmethod
    def _object_to_dict(obj):
        data = {}
        data['fdists'] = dict([
                (condition, object_to_dict(dist)) \
                    for condition,dist in obj._fdists.items()])
        return data
        
    @staticmethod
    def _dict_to_object(dic):
        obj = ConditionalFreqDist()
        obj._fdists = dict([
                (condition, dict_to_object(dist)) \
                    for condition,dist in dic['fdists'].items()])
        return obj

class DictionaryProbDistStorer(ObjectStorer):
    STORED_CLASS = DictionaryProbDist
    
    @staticmethod
    def _object_to_dict(obj):
        return {
            'dict' : dict((sample,obj.logprob(sample)) for sample in obj.samples()),
        }
    
    @staticmethod
    def _dict_to_object(dic):
        return DictionaryProbDist(prob_dict=dic['dict'], log=True)

class MutableProbDistStorer(DictionaryProbDistStorer):
    STORED_CLASS = MutableProbDist
    
    @staticmethod
    def _dict_to_object(dic):
        return MutableProbDist(
                        DictionaryProbDist(prob_dict=dic['dict'], log=True),
                        samples=dic['dict'].keys())

class DictionaryConditionalProbDistStorer(ObjectStorer):
    STORED_CLASS = DictionaryConditionalProbDist
    
    @staticmethod
    def _object_to_dict(obj):
        # Each individual distribution needs to be storable too
        dists = dict((cond, object_to_dict(obj[cond])) for cond in obj.conditions())
        return {
            'dists' : dists,
        }
    
    @staticmethod
    def _dict_to_object(dic):
        dists = dict((cond, dict_to_object(dist)) for (cond,dist) in dic['dists'].items())
        return DictionaryConditionalProbDist(dists)

############################ Utilities #############################

def get_storer(cls):
    """
    Returns an ObjectStorer subclass that store's the given type if one 
    is found. Raises an ObjectStorerError otherwise.
    
    """
    from . import STORERS
    for storer in STORERS:
        if storer.STORED_CLASS is cls:
            return storer
    raise ObjectStorerError, "could not get an object storer for type %s" % cls.__name__
    
def object_to_dict(obj):
    return get_storer(type(obj)).object_to_dict(obj)
    
def dict_to_object(dic):
    return get_storer(dic['_type']).dict_to_object(dic)
