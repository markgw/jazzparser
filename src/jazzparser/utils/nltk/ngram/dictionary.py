"""Generic HMM model implementation, using NLTK's probability handling.

This is similar to L{jazzparser.utils.nltk.ngram.NgramModel}, but is 
specialized to HMMs (bigram models) and stores probability distributions 
as dictionaries instead of estimating them from counts. It may be trained 
from counts in a corpus, but these are thrown away once the model is 
estimated.

This type of model may be used in Baum-Welch re-estimation, since the 
probabilities can be updated, since they're not estimated from counts.
Baum-Welch training for this model type (and its subclasses) can be found 
in L{jazzparser.utils.nltk.ngram.baumwelch}.

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

import numpy
from numpy import sum as array_sum

from jazzparser.utils.nltk.probability import logprob, \
                    cond_prob_dist_to_dictionary_cond_prob_dist
from nltk.probability import sum_logs, DictionaryProbDist
from .model import NgramModel

class DictionaryHmmModel(NgramModel):
    """
    Like an NgramModel, but (a) restricted to be an HMM (order 2 and no 
    backoff) and (b) uses dictionary distributions, rather than distributions 
    generated from counts.
    
    Using dictionary distributions allows the parameters to be retrained, e.g.
    with Baum-Welch EM, but means we can't use the kind of backoff model 
    NgramModel implements, since this is dependent on having counts for the 
    training data available.
    
    The distributions given at initialization don't have to be dictionary 
    distributions, but will be converted to such.
    
    """
    def __init__(self, label_dist, emission_dist, label_dom, emission_dom, \
                        mutable=False):
        """
        @type label_dist: nltk prob dist
        @param label_dist: transition distribution
        @type emission_dist: nltk prob dist
        @param emission_dist: emission distribution
        @type label_dom: list
        @param label_dom: state domain
        @type emission_dom: list
        @param emission_dom: emission domain
        @type mutable: bool
        @param mutable: if true, the distributions stored will be mutable 
            dictionary distributions, so the model can be updated
        
        """
        self.order = 2
        
        self.label_dom = label_dom
        self.num_labels = len(label_dom)
        self.emission_dom = emission_dom
        self.num_emissions = len(emission_dom)
        
        self.label_dist = cond_prob_dist_to_dictionary_cond_prob_dist(\
                                label_dist, mutable=mutable)
        self.emission_dist = cond_prob_dist_to_dictionary_cond_prob_dist(\
                                emission_dist, mutable=mutable)
        # Marginalize the emission dist to get an unconditioned version
        observations = {}
        for label in emission_dist.conditions():
            for samp in emission_dist[label].samples():
                observations[samp] = observations.get(samp, 0.0) + \
                        emission_dist[label].prob(samp)
        self.observation_dist = DictionaryProbDist(observations)
        self.seen_labels = label_dom
        
        self.backoff_model = None
        
        # Initialize the various caches
        # These will be filled as we access probabilities
        self.clear_cache()
        
    @staticmethod
    def from_ngram_model(model, mutable=False):
        """
        Creates a DictionaryHmmModel from an L{NgramModel}. Note that the 
        ngram model must of the correct sort: order 2 with no backoff.
        
        """
        if model.order != 2:
            raise TypeError, "can only create an HMM from an order 2 ngram"
        if model.backoff_model is not None:
            raise TypeError, "tried to create a dictionary HMM from a model "\
                "with backoff. The backoff can't be replicated in such a model"
        
        return DictionaryHmmModel(model.label_dist, 
                                  model.emission_dist, 
                                  model.label_dom,
                                  model.emission_dom, 
                                  mutable=mutable)
        
    def to_picklable_dict(self):
        """
        Produces a picklable representation of model as a dict.
        
        """
        from jazzparser.utils.nltk.storage import object_to_dict
        
        return {
            'label_dom' : self.label_dom,
            'emission_dom' : self.emission_dom,
            'label_dist' : object_to_dict(self.label_dist),
            'emission_dist' : object_to_dict(self.emission_dist),
        }
        
    @staticmethod
    def from_picklable_dict(data):
        """
        Reproduces an n-gram model that was converted to a picklable 
        form using to_picklable_dict.
        
        """
        from jazzparser.utils.nltk.storage import dict_to_object
        
        return DictionaryHmmModel(dict_to_object(data['label_dist']),
                                  dict_to_object(data['emission_dist']),
                                  data['label_dom'],
                                  data['emission_dom'])
    
    def compute_gamma(self, *args, **kwargs):
        """
        This is now implemented much better than it used to be by the 
        superclass. Use 
        L{jazzparser.utils.nltk.ngram.NgramModel.gamma_probabilities}.
        This method is now just a wrapper to that.
        
        """
        return self.gamma_probabilities(*args, **kwargs)
        
    def compute_xi(self, sequence, forward=None, backward=None, 
                        emission_matrix=None, transition_matrix=None,
                        use_logs=False):
        """
        Computes the xi matrix used by Baum-Welch. It is the matrix of joint 
        probabilities of occupation of pairs of consecutive states: 
        P(i_t, j_{t+1} | O).
        
        As with L{compute_gamma} forward and backward matrices can optionally 
        be passed in to avoid recomputing.
        
        @type use_logs: bool
        @param use_logs: by default, this function does not use logs in its 
            calculations. This can lead to underflow if your forward/backward 
            matrices have sufficiently low values. If C{use_logs=True}, logs 
            will be used internally (though the returned values are 
            exponentiated again). This makes the function an order of magnitude 
            slower.
        
        """
        if forward is None:
            forward = self.normal_forward_probabilities(sequence)
        if backward is None:
            backward = self.normal_backward_probabilities(sequence)
        # T is the number of timesteps
        # N is the number of states
        T,N = forward.shape
        
        # Create the empty array to fill
        xi = numpy.zeros((T-1,N,N), numpy.float64)
        
        # Precompute all the emission probabilities
        if emission_matrix is None:
            emission_matrix = self.get_emission_matrix(sequence)
        # And transition probabilities: we'll need these many times over
        if transition_matrix is None:
            transition_matrix = self.get_transition_matrix()
        
        if not use_logs:
            # Do it without logs - much faster
            for t in range(T-1):
                total = 0.0
                # Transpose the forward probabilities so that we multiply them 
                #  along the vertical axis
                fwd_trans = forward[t,:, numpy.newaxis]
                # Compute the xi values by multiplying the arrays together
                xi[t] = transition_matrix.T * fwd_trans * backward[t+1] * \
                            emission_matrix[t+1]
                # Normalize all the probabilities
                # Sum all the probs for the timestep and divide them all by total
                total = array_sum(xi[t])
                xi[t] /= total
        else:
            # Take logs of all the matrices we need
            emission_matrix = numpy.log2(emission_matrix)
            transition_matrix = numpy.log2(transition_matrix)
            forward = numpy.log2(forward)
            backward = numpy.log2(backward)
            
            for t in range(T-1):
                total = 0.0
                fwd_trans = forward[t,:, numpy.newaxis]
                xi[t] = transition_matrix.T + fwd_trans + backward[t+1] + \
                            emission_matrix[t+1]
                # This takes a (relatively) long time
                total = numpy.logaddexp2.reduce(xi[t])
                xi[t] -= total
            # Exponentiate all the probabilities again
            # This also takes a while
            xi = numpy.exp2(xi)
        
        return xi
        
    def viterbi_decode(self, sequence):
        """ More efficient Viterbi decoding than superclass. """
        T = len(sequence)
        N = len(self.label_dom)
        
        viterbi_matrix = numpy.zeros((T,N), numpy.float64)
        back_pointers = numpy.zeros((T-1,N), numpy.int)
        
        ems = self.get_emission_matrix(sequence)
        trans = self.get_transition_matrix()    
        
        # Prepare the first column of the matrix: probs of all states in the 
        #  first timestep
        for i,state in enumerate(self.label_dom):
            viterbi_matrix[0,i] = self.transition_probability(state, None) * ems[0,i]
        
        # Fill in the other columns
        for t in range(1, T):
            # Get a matrix of all the possible transitions from previous states 
            #  to current states: transition prob multiplied by previous 
            #  timestep for the previous state
            transitions = trans * viterbi_matrix[t-1]
            # Find the maximum value for each state over possible previous states
            max_transitions = numpy.max(transitions, axis=1)
            # Multiply by the emission probilities in the current state to 
            #  get the next timestep of the viterbi matrix
            viterbi_matrix[t, :] = max_transitions * ems[t]
            # Normalize these so we don't disappear into underflow
            viterbi_matrix[t, :] /= numpy.sum(viterbi_matrix[t, :])
            # Note which state we came from for each of these (the argmax)
            back_pointers[t-1] = numpy.argmax(transitions, axis=1)
        
        # Choose the most probable state to end in
        final_state = numpy.argmax(viterbi_matrix[T-1,:])
        
        # Trace back the pointers to find the maximal sequence
        current_state = final_state
        states = [final_state]
        for t in range(T-2, -1, -1):
            last_state = back_pointers[t, current_state]
            states.append(last_state)
            current_state = last_state
        states = list(reversed(states))
        
        # Convert these indices to state labels
        states = [self.label_dom[s] for s in states]
        return states
