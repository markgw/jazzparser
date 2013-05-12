""" Extensions to NLTK's probability module.

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

import math
from nltk.probability import FreqDist, ConditionalFreqDist, \
                    MLEProbDist, FreqDist, ConditionalFreqDist, \
                    ConditionalProbDist, LaplaceProbDist, WittenBellProbDist, \
                    GoodTuringProbDist, add_logs as nltk_add_logs, \
                    DictionaryProbDist, DictionaryConditionalProbDist, \
                    MutableProbDist, SimpleGoodTuringProbDist
from .storage import ObjectStorer
from ..probabilities import random_selection

def logprob(prob):
    """
    Returns the base 2 log of the given probability (or other float). If 
    prob == 0.0, returns -inf.
    
    """
    if prob == 0.0:
        return float('-inf')
    else:
        return math.log(prob, 2)

def add_logs(logx, logy):
    """
    Identical to NLTK's L{nltk.probability.add_logs}, but handles the special 
    case where one or both of the numbers is -inf. NLTK's version gives a nan 
    in this case.
    
    """
    if logx == float('-inf'):
        return logy
    elif logy == float('-inf'):
        return logx
    else:
        return nltk_add_logs(logx, logy)
    
def sum_logs(logs):
    """
    Identical to NLTK's L{nltk.probability.sum_logs}, but uses our version of 
    L{add_logs} and -inf for zero probs
    
    """
    if len(logs) == 0:
        return float('-inf')
    else:
        return reduce(add_logs, logs[1:], logs[0])

def generate_from_prob_dist(dist):
    """
    Generates a sample chosen randomly from the observed samples of an NLTK 
    prob dist, weighted according to their probability.
    NLTK provides this, but doesn't allow for the summed probability of the 
    observed samples not being 1.0. But, of course, this is the case when 
    we're smoothing.
    
    """
    samp_probs = [(samp, dist.prob(samp)) for samp in dist.samples()]
    return random_selection(samp_probs, normalize=True)

def prob_dist_to_dictionary_prob_dist(dist, mutable=False, samples=None):
    """
    Takes a probability distribution estimated in any way (e.g. from 
    a freq dist) and produces a corresponding dictionary prob dist 
    that just stores the probability of every sample.
    
    Can be used to turn any kind of prob dist into a dictionary-based 
    one, including a MutableProbDist.
    
    @type mutable: bool
    @param mutable: if True, the returned dist is a mutable prob dist
    
    """
    # We may want to give a different set of samples, for example, if there 
    #  are samples not represented in the original dist
    if samples is None:
        samples = dist.samples()
    
    probs = {}
    for sample in samples:
        probs[sample] = dist.prob(sample)
    # We'd expect these to sum to one, but normalize just in case
    dictpd = DictionaryProbDist(probs, normalize=True)
    
    if mutable:
        # Convert to a mutable distribution
        dictpd = MutableProbDist(dictpd, samples)
    return dictpd

def cond_prob_dist_to_dictionary_cond_prob_dist(dist, mutable=False, \
                samples=None, conditions=None):
    """
    Takes a conditional probability distribution which may estimate 
    its probabilities in any way (most likely from a set of frequency 
    distributions) and produces an equivalent dictionary conditional 
    distribution, whose distributions are dictionary prob dists.
    
    @type mutable: bool
    @param mutable: if True, the returned dist contains mutable prob dists
    
    """
    dists = {}
    if conditions is None:
        conditions = dist.conditions()
    for condition in conditions:
        dists[condition] = prob_dist_to_dictionary_prob_dist(dist[condition], \
                                mutable=mutable, samples=samples)
    return DictionaryConditionalProbDist(dists)


class WittenBellProbDistFix(WittenBellProbDist):
    """
    There's a nasty bug in WittenBellProbDist, but the fix is very simple.
    Use this instead of WittenBellProbDist.
    
    """
    def __init__(self, freqdist, bins=None):
        assert bins == None or bins >= freqdist.B(),\
               'Bins parameter must not be less than freqdist.B()'
        if bins == None:
            bins = freqdist.B()
        self._freqdist = freqdist
        self._T = self._freqdist.B()
        self._Z = bins - self._freqdist.B()
        self._N = self._freqdist.N()
        # self._P0 is P(0), precalculated for efficiency:
        if self._Z == 0:
            # No unseen events: probability of anything we have no 
            # counts for is 0
            self._P0 = 0.0
        elif self._N==0: 
            # if freqdist is empty, we approximate P(0) by a UniformProbDist:
            self._P0 = 1.0 / self._Z
        else:
            self._P0 = self._T / float(self._Z * (self._N + self._T))



def estimator_name(name):
    """ Decorator to add a name attribute to the estimator functions """
    def _estimator_name(estimator):
        estimator.estimator_name = name
        return estimator
    return _estimator_name

@estimator_name('mle')
def mle_estimator(fdist, bins):
    return MLEProbDist(fdist)
    
@estimator_name('laplace')
def laplace_estimator(fdist, bins):
    return LaplaceProbDist(fdist, bins=bins)
    
@estimator_name('witten-bell')
def witten_bell_estimator(fdist, bins):
    return WittenBellProbDistFix(fdist, bins=bins)
    
@estimator_name('good_turing')
def good_turing_estimator(fdist, bins):
    return GoodTuringProbDist(fdist, bins=bins)
    
@estimator_name('good_turing')
def simple_good_turing_estimator(fdist, bins):
    return SimpleGoodTuringProbDist(fdist, bins=bins)
    
def get_estimator_name(estimator):
    if hasattr(estimator, 'estimator_name'):
        # Use the readable name if one is available
        return estimator.estimator_name
    else:
        return estimator.__name__

ESTIMATORS = {
    'mle' : mle_estimator,
    'laplace' : laplace_estimator,
    'witten-bell' : witten_bell_estimator,
    'good-turing' : good_turing_estimator,
    'simple-good-turing' : simple_good_turing_estimator,
}

class CutoffFreqDist(FreqDist):
    """
    Like FreqDist, but returns zero counts for everything with a count 
    less than a given cutoff. Also adjusts the total count to account 
    for the lost counts.
    
    """
    def __init__(self, cutoff, *args, **kwargs):
        self._cutoff = cutoff
        super(CutoffFreqDist, self).__init__(*args, **kwargs)
        
    def __getitem__(self, key):
        val = self.raw_count(key)
        if val <= self._cutoff:
            return 0
        else:
            return val
            
    def raw_counts(self):
        """
        Returns the raw counts (i.e. without the cutoff applied) as a 
        dictionary. This could, for example, be used as init data to 
        another FreqDist.
        
        """
        return dict(dict.items(self))
        
    def raw_count(self, sample):
        """
        Returns the raw count of this sample (doesn't apply a cutoff).
        
        """
        return super(CutoffFreqDist, self).__getitem__(sample)
            
    def N(self):
        return self._N - self.lost_N()
        
    def B(self):
        """
        This is slightly more complicated than the superclass, because 
        we want to count only samples that have non-zero counts after the 
        cutoff has been applied.
        
        """
        return len([count for count in self.values() if count > self._cutoff])
    
    def __len__(self):
        return self.B()
        
    def freq(self, sample):
        """
        Have to override this because the superclass doesn't use N(), 
        but the internal _N to calculate the frequency.
        
        """
        if self.N() == 0:
            return 0
        return float(self[sample]) / self.N()
        
    def copy(self):
        # Don't use our samples, but the ones without the cutoff applied
        return CutoffFreqDist(self._cutoff, self.raw_counts())
        
    def __add__(self, other):
        """
        Returns a CutoffFreqDist like this one, but with counts from the 
        other added. The other may only be another CutoffFreqDist.
        
        """
        if not isinstance(other, CutoffFreqDist):
            raise TypeError, "can only sum a CutoffFreqDist with "\
                "another CutoffFreqDist, not %s" % type(other).__name__
        clone = self.copy()
        clone.update(other.raw_counts())
        return clone
        
    def _reset_caches(self):
        """ Add our own caches to the superclass' """
        self._lost_N = None
        super(CutoffFreqDist, self)._reset_caches()
        
    def lost_N(self):
        """ The number of counts lost by applying the cutoff """
        if self._lost_N is None:
            # Recompute the cached value
            self._lost_N = 0
            raw_counts = self.raw_counts()
            for key in raw_counts:
                if raw_counts[key] <= self._cutoff:
                    # Would have counted this much but for the cutoff
                    self._lost_N += raw_counts[key]
        return self._lost_N
        
    def _get_cutoff(self):
        """ Make cutoff a read-only attribute """
        return self._cutoff
    cutoff = property(_get_cutoff)
    
    def _sort_keys_by_value(self):
        """
        Need to override this because dict.items(self) accesses the 
        non-cutoff values.
        """
        if not self._item_cache:
            items = [(key,self[key]) for key in dict.keys(self)]
            # Eliminate 0 counts
            items = [(key,val) for (key,val) in items if val != 0]
            self._item_cache = sorted(items, key=lambda x:(-x[1], x[0]))

class CutoffConditionalFreqDist(ConditionalFreqDist):
    """
    A version of ConditionalFreqDist that uses a CutoffFreqDist for 
    each distribution instead of FreqDist.
    
    """
    def __init__(self, cutoff, *args, **kwargs):
        self._cutoff = cutoff
        super(CutoffConditionalFreqDist, self).__init__(*args, **kwargs)
        
    def _get_cutoff(self):
        """ Make cutoff a read-only attribute """
        return self._cutoff
    cutoff = property(_get_cutoff)

    def __getitem__(self, condition):
        """
        Override this to use CutoffFreqDists instead of FreqDists.
        
        """
        # Create the conditioned freq dist, if it doesn't exist
        if condition not in self._fdists:
            self._fdists[condition] = CutoffFreqDist(self._cutoff)
        return self._fdists[condition]
    
########################## Storers (see .storage) ######################
class CutoffFreqDistStorer(ObjectStorer):
    STORED_CLASS = CutoffFreqDist
    
    @staticmethod
    def _object_to_dict(obj):
        from .storage import FreqDistStorer
        # This overrides FreqDistStorer, so can use most of its method
        data = FreqDistStorer._object_to_dict(obj)
        # Add our own value
        data['cutoff'] = obj.cutoff
        return data
        
    @staticmethod
    def _dict_to_object(dic):
        from .storage import FreqDistStorer
        dist = CutoffFreqDist(dic.pop('cutoff'))
        return FreqDistStorer._dict_to_object(dic, start_dist=dist)

class CutoffConditionalFreqDistStorer(ObjectStorer):
    STORED_CLASS = CutoffConditionalFreqDist
    
    @staticmethod
    def _object_to_dict(obj):
        from .storage import ConditionalFreqDistStorer
        data = ConditionalFreqDistStorer._object_to_dict(obj)
        # Add the cutoff value
        data['cutoff'] = obj._cutoff
        return data
        
    @staticmethod
    def _dict_to_object(dic):
        from .storage import dict_to_object
        # Would be nice to use the superclass' storage better, but 
        #  simpler to copy this for now
        obj = CutoffConditionalFreqDist(dic['cutoff'])
        obj._fdists = dict([
                (condition, dict_to_object(dist)) \
                    for condition,dist in dic['fdists'].items()])
        return obj
