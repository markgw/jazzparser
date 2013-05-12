"""Generic n-gram model implementation, using NLTK's probability handling.

NLTK provides an n-gram POS tagger, but it can only assign the most 
likely tag sequence to observations. It doesn't calculate probabilities, 
so is no use for our supertagger component. Here I provide a generic 
n-gram model, using NLTK's probability stuff.

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

import copy,sys,logging, math, warnings
import numpy
from numpy import sum as array_sum
from jazzparser.utils.nltk.probability import laplace_estimator, logprob, \
                    cond_prob_dist_to_dictionary_cond_prob_dist, sum_logs
from nltk.probability import ConditionalProbDist, sum_logs, DictionaryProbDist, \
                    ConditionalFreqDist, FreqDist

NGRAM_JOINER = "::"

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

def matrix_log_probs_to_probs(matrix):
    """
    Utility function for methods below.
    Converts all the probabilities in the time-state matrix from log 
    probabilities to probabilities.
    
    """
    return [dict([(label, 2**log_prob) for (label,log_prob) in timestep.items()]) for timestep in matrix]

def sum_matrix_dims(matrix, dims=2):
    """
    Takes an n-dimensional matrix and sums over all but the first C{dims} 
    dimensions, returning a C{dims}-dimensional matrix. You can do this 
    easily in later versions of Numpy!
    
    """
    # Sum over all but the first two dimensions: time and last state in ngram
    start_dims = matrix.ndim
    for i in range(start_dims-dims):
        matrix = numpy.sum(matrix, axis=-1)
    return matrix

def _all_indices(length, num_labels):
    """
    Function to generate all index n-grams of a given length
    
    """
    if length < 1:
        return [[]]
    else:
        return sum([ [[i]+sub for i in range(num_labels)]
                        for sub in _all_indices(length-1, num_labels)], [])

class NgramModel(object):
    """
    A general n-gram model, trained on some labelled data.
    Generate models using NgramModel.train().
    
    Note that backoff assumes that an estimator with discounting is 
    being used. The backed off probabilities are scaled according to the 
    smoothing probability that would have been assigned to a zero 
    count. If you use this with MLE, the backoff is effectively disabled.
    
    The estimator should be picklable. This means you can't use a 
    lambda, for example.
    
    """
    def __init__(self, order, label_counts, emission_counts, \
                        estimator, \
                        backoff_model, \
                        label_dom, emission_dom):
        from ..storage import is_picklable
        
        self.order = order
        self.label_dom = label_dom
        self.num_labels = len(label_dom)
        self.emission_dom = emission_dom
        self.num_emissions = len(emission_dom)
        
        # Check the estimator's picklable
        # Otherwise we'll get mysterious errors when storing the model
        if not is_picklable(estimator):
            raise NgramError, "the estimator given for an n-gram model "\
                "is not picklable. Use a statically-defined function as "\
                "your estimator (got %s)" % type(estimator).__name__
        
        # Keep the freq dists to get the raw counts
        self.label_counts = label_counts
        self.emission_counts = emission_counts
        # Construct a probability distribution from these frequency dists
        self.label_dist = ConditionalProbDist(label_counts, estimator, self.num_labels+1)
        self.emission_dist = ConditionalProbDist(emission_counts, estimator, self.num_emissions)
        # Keep hold of this for when we store the model
        # It doesn't get used otherwise, as it was only to construct the prob dists
        self._estimator = estimator
        
        self.backoff_model = backoff_model
        
        self.clear_cache()
        
    def __repr__(self):
        return "<%s model,%d lab,%d em>" % (self.model_type, self.num_labels, self.num_emissions)
        
    def _get_model_type(self):
        """
        model_type gives a sensible name to the order of n-gram. Uses 
        unigram, bigram, trigram, or x-gram.
        
        """
        if self.order == 1:
            return "unigram"
        elif self.order == 2:
            return "bigram"
        elif self.order == 3:
            return "trigram"
        else:
            return "%d-gram" % self.order
    model_type = property(_get_model_type)
    
    def clear_cache(self):
        """
        Subclasses that use caches should override this method to reset them 
        and call this in the superclass.
        
        """
        self._transition_matrix_cache = None
        self._transition_matrix_transpose_cache = None
        # These will be filled as we access probabilities
        self._discount_cache = {}
        self._emission_discount_cache = {}
        self._transition_cache = {}
    
    @staticmethod
    def train(order, labelled_data, label_dom, emission_dom=None, cutoff=0, 
                backoff_order=0, estimator=None, ignore_list=None, backoff_kwargs={}):
        """
        Trains the n-gram model given some labelled data. The data 
        should be in the form of a sequence of sequences of tuples (e,t), 
        where e is an emission and t a tag.
        
        If ignore_list is given, all ngrams containing a label in 
        ignore_list will be ignored altogether. One use for this is to 
        ignore blank labels, so we don't learn the gaps in the labelled
        data.
        
        """
        if order <= 0:
            raise NgramError, "cannot construct a %d-gram model!" % order
        if backoff_order >= order:
            raise NgramError, "cannot construct a %d-gram model "\
                "with %d-order backoff" % (order, backoff_order)
        
        if estimator is None:
            estimator = laplace_estimator
                
        labelled_data = list(labelled_data)
        label_dist = ConditionalFreqDist()
        emission_dist = ConditionalFreqDist()
        seen_emissions = set()
        
        if ignore_list is not None:
            ignores = set(ignore_list)
        else:
            ignores = set()
        
        for training_sequence in labelled_data:
            # Add blanks to the start of the sequence to get our first n-grams
            # Add a blank to the end to get the final probabilities
            training_data = [(None,None)]*(order-1) + list(training_sequence) + [(None,None)]
            # Add counts to the model
            for i in range(len(training_data)-order):
                # This is actually a full ngram, to give us all states for 
                #  the transition
                ngram = list(reversed(training_data[i:i+order]))
                outputs,tags = zip(*ngram)
                # Check whether the tags include any of those we should be ignoring
                if ignores.isdisjoint(set(tags)):
                    tag = tags[0]
                    # Don't count emissions from None
                    if tag is not None and outputs[0] is not None:
                        # Emission count
                        emission_dist[tag].inc(outputs[0])
                        # Keep track of what emissions we've seen
                        seen_emissions.add(outputs[0])
                    # Labelled ngram count
                    context = tuple(tags[1:])
                    label_dist[context].inc(tag)
        
        # Apply low-count cutoff to both distributions
        for label in emission_dist.conditions():
            for sample in emission_dist[label].samples():
                if emission_dist[label][sample] <= cutoff:
                    emission_dist[label][sample] = 0
        for context in label_dist.conditions():
            for sample in label_dist[context].samples():
                if label_dist[context][sample] <= cutoff:
                    label_dist[context][sample] = 0
                
        # If no domain of emissions was given, use what we've seen in the data
        if emission_dom is None:
            emission_dom = seen_emissions
        else:
            emission_dom = set(emission_dom)
        
        if backoff_order > 0:
            kwargs = {
                "emission_dom" : emission_dom,
                "cutoff" : cutoff, 
                "backoff_order" : backoff_order-1,
                "estimator" : estimator,
                "ignore_list" : ignores
            }
            # Add in any args we've been told to use
            kwargs.update(backoff_kwargs)
            # Construct a model to back off to
            backoff_model = NgramModel.train(order-1, 
                                             labelled_data, 
                                             label_dom, 
                                             **kwargs)
        else:
            backoff_model = None
            
        # Return an actual model as trained above
        return NgramModel(order, label_dist, emission_dist, estimator, backoff_model, label_dom, emission_dom)
        
    def _get_transition_backoff_scaler(self, context):
        """
        Returns the amount to scale the backed off probabilities by 
        when backing off to an order n-1 model in the given context.
        This is presented as alpha in Jurafsky and Martin.
        
        Returned as a base 2 log.
        
        A more efficient way to do this would be to supply a function 
        of the context specific to the discounting technique. In this 
        case it wouldn't be necessary to sum the discounted mass each 
        time.
        
        """
        if context not in self._discount_cache:
            # The prob mass reserved for unseen events can be computed by 
            #  summing probabilities over all seen events and subtracting 
            #  from 1.
            # Our discounting model distributes this probability evenly over 
            #  the unseen events, so we can compute the discounted mass by 
            #  getting the probability of one unseen event and multiplying it.
            seen_labels = set([lab for lab in self.label_dom+[None] if 
                                        self.label_counts[context][lab] > 0])
            if len(seen_labels) == 0:
                # Not seen anything in this context. All mass is discounted!
                self._discount_cache[context] = 0.0
            else:
                unseen_labels = set(self.label_dom+[None]) - seen_labels
                # Try getting some event that won't have been seen
                # Compute how much mass is reserved for unseen events
                discounted_mass = self.label_dist[context].prob(
                                                    "%%% UNSEEN LABEL %%%") \
                                                * len(unseen_labels)
                # Compute how much probability the n-1 order model assigns to 
                #  things unseen by this model
                backoff_context = context[:-1]
                backoff_seen_mass = sum([
                            self.backoff_model.transition_probability(lab, 
                                                        *backoff_context) 
                                                for lab in unseen_labels], 0.0)
                self._discount_cache[context] = logprob(discounted_mass) - \
                                                    logprob(backoff_seen_mass)
        return self._discount_cache[context]
        
    def transition_log_probability(self, *ngram):
        """
        Gives the probability P(label_i | label_(i-1), ..., label_(i-n)),
        where the previous labels are given in the sequence 
        label_context. The context should be in reverse order, i.e. 
        with the most recent label at the start.
        
        Note that this is the probability of a label given the previous 
        n-1 labels, which is the same as the probability of the n-gram 
        [label_i, ..., label_(i-n+1)] given the ngram 
        [label_(i-1), ..., label_(i-n)], since all but the last element 
        of the ngram overlaps with the condition, so has probability 1.
        
        Caches all computed transition probabilities. This is 
        particularly important for backoff models. Many n-grams will 
        back off to the same (n-1)-gram and we don't want to recompute 
        the transition probability for that each time.
        
        """
        # Cache the probabilities we've computed
        if ngram not in self._transition_cache:
            # Check the context is the right size
            # This method gets called millions of times, but most times the 
            #  value is cached. We only need check this the first time
            if len(ngram) != self.order:
                raise NgramError, "a %d-gram model can only give transition "\
                    "probabilities for a context of length %d. Tried to use "\
                    "%d" % (self.order, self.order-1, len(ngram)-1)
            
            # Compute the probability as we've not seen it before
            context = tuple(ngram[1:])
            label = ngram[0]
            # Check whether we have enough observations of this whole n-gram
            if self.backoff_model is not None and self.label_counts[context][label] == 0:
                # Backoff to a lower-order model
                # Work out how much prob mass is reserved for unseen events
                scale = self._get_transition_backoff_scaler(context)
                # Backoff and scale to fill the reserved mass
                prob = scale + self.backoff_model.transition_log_probability(*(ngram[:-1]))
            else:
                prob = self.label_dist[context].logprob(label)
            # Don't compute this one again
            self._transition_cache[ngram] = prob
        return self._transition_cache[ngram]
        
    def transition_log_probability_debug(self, *ngram):
        """
        Debugging version of the above.
        Use this only for debugging. It prints stuff out and doesn't cache.
        
        """
        if len(ngram) != self.order:
            raise NgramError, "a %d-gram model can only give transition "\
                "probabilities for a context of length %d. Tried to use "\
                "%d" % (self.order, self.order-1, len(ngram)-1)
        
        # Compute the probability as we've not seen it before
        context = tuple(ngram[1:])
        label = ngram[0]
        # Check whether we have enough observations of this whole n-gram
        if self.backoff_model is not None and self.label_counts[context][label] == 0:
            print "Backing off: %s" % ", ".join([str(s) for s in ngram[:-1]])
            # Work out how much prob mass is reserved for unseen events
            scale = self._get_transition_backoff_scaler(context)
            print "  Scaler: %s, %f" % (", ".join([str(s) for s in context]),2**scale)
            # Backoff and scale by the reserved mass
            prob = scale + self.backoff_model.transition_log_probability_debug(*(ngram[:-1]))
        else:
            prob = self.label_dist[context].logprob(label)
            print "Using %d-gram model probability: %f" % (self.order, 2**prob)
        return prob
        
    def transition_probability(self, label, *label_context):
        """
        Wrapper for transition_log_probability to return a real 
        probability.
        
        """
        return 2**self.transition_log_probability(label, *label_context)
        
    def transition_probability_debug(self, *ngram):
        """ Debugging version of the above """
        return 2**self.transition_log_probability_debug(*ngram)
    
    def emission_log_probability(self, emission, label):
        """
        Gives the probability P(emission | label). Returned as a base 2
        log.
        
        """
        return self.emission_dist[label].logprob(emission)
            
    def emission_probability(self, emission, label):
        """
        Wrapper for emission_log_probability to return an real 
        probability.
        
        """
        return 2**self.emission_log_probability(emission, label)
            
    def get_backoff_models(self):
        """
        Returns a list consisting of this model and all the recursive 
        backoff models, until no more backoff models are provided.
        
        """
        if self.backoff_model is None:
            return [self]
        else:
            return [self]+self.backoff_model.get_backoff_models()
            
    def get_transition_matrix(self, transpose=False):
        """
        Produces a matrix of the transition probabilities from every 
        (n-1)-gram to every state. Matrix indices are based on enumeration of 
        C{self.label_dom}. The matrix is returned as a numpy array.
        
        The matrix has n dimensions. The first index is the current state, 
        the second the previous, etc. Thus, 
        matrix[i,j,...] = p(state_t = i | state_(t-1) = j, ...).
        
        Probabilities are not logs.
        
        """
        if transpose:
            if self._transition_matrix_transpose_cache is None:
                # Ensure that the normal transition matrix has been generated
                mat = self.get_transition_matrix()
                # Tranpose it and copy it, so it's a real array, not a view
                self._transition_matrix_transpose_cache = numpy.copy(mat.transpose())
            return self._transition_matrix_transpose_cache
        else:
            if self._transition_matrix_cache is None:
                # Compute the matrix from scratch, as we've not done it yet
                N = len(self.label_dom)
                shape = tuple([N]*self.order)
                trans = numpy.zeros(shape, numpy.float64)
                
                states = self.label_dom
                # Build a list of lists, each n long, with all possible array indices
                index_sets = _all_indices(self.order, N)
                
                # Fill the matrix
                for indices in index_sets:
                    # Get the ngram of state labels for this ngram of array indices
                    state_labels = [states[i] for i in indices]
                    trans[tuple(indices)] = self.transition_probability(*state_labels)
                
                self._transition_matrix_cache = trans
            return self._transition_matrix_cache
    
    def get_emission_matrix(self, sequence):
        """
        Produces a matrix of the probability of each timestep's emission from 
        each state.
        
        matrix[t,i] = p(o_t | state=i)
        
        """
        T = len(sequence)
        N = len(self.label_dom)
        
        ems = numpy.zeros((T, N), numpy.float64)
        
        # Set the probability for every timestep...
        for t,emission in enumerate(sequence):
            # ...given each state
            for i,label in enumerate(self.label_dom):
                ems[t,i] = self.emission_probability(emission, label)
        return ems
    
    def decode_forward(self, sequence):
        """
        Uses the forward probabilities to decode the sequence and 
        returns a list of labels.
        
        """
        forwards = self.normal_forward_probabilities(sequence)
        # Sum up ngram dimensions, leaving just time and state
        forwards = sum_matrix_dims(forwards)
        # Do an argmax over the possible states for each timestep
        states = numpy.argmax(forwards, axis=1)
        # Convert these indices into state labels
        return [self.label_dom[state] for state in states]
        
    def normal_forward_probabilities(self, sequence, seq_prob=False):
        """
        Return the forward probability matrix as a Numpy array. 
        This is equivalent to L{forward_probabilities}, but much faster. 
        It doesn't need logs because it's normalizing at each timestep.
        
        @param seq_prob: return the log probability of the whole sequence 
            as well as the array (tuple of (array,logprob)).
        @return: S-dimensional Numpy array, where S is the number of states.
            The first dimension represents timesteps, the rest the (S-1) 
            states in the ngrams.
        
        """
        N = len(sequence)
        states = self.label_dom
        
        # Create an array for the total logprobs
        coefficients = numpy.zeros((N,), numpy.float64)
        
        # Prepare the transition and emission matrices
        ems = self.get_emission_matrix(sequence)
        trans = self.get_transition_matrix()
        
        if self.order == 1:
            # We can do this quickly for unigrams and it saves dealing with 
            #  dodgy cases of everything below
            # We only use emission probabilities: transition probs 
            #  just supply (unconditioned) priors
            forward_matrix = trans*ems
            # Sum the probabilities in each timestep
            total_probs = numpy.sum(forward_matrix, axis=1)
            for t in range(N):
                coefficients[t] = logprob(total_probs[t])
                forward_matrix[t] /= total_probs[t]
            if seq_prob:
                return forward_matrix, numpy.sum(coefficients)
            else:
                return forward_matrix
            
        # Initialize an empty matrix
        forward_matrix = numpy.zeros([N]+[len(states)]*(self.order-1), numpy.float64)
        
        # First fill in the first columns with histories padded with Nones
        # In these columns, we only use a subset of the dimensions
        for time in range(self.order-1):
            # Get the indices corresponding to all possible sub-n-grams
            #  between the start and here
            index_sets = _all_indices(time+1, len(states))
            
            for indices in index_sets:
                # Get the actual ngram for these indices
                ngram = [self.label_dom[i] for i in indices]
                # Pad with Nones to a length of n
                ngram.extend([None]*(self.order-time-1))
                # Pad the indices with 0s so we use all the dimensions
                indices.extend([0]*(self.order-time-2))
                selector = tuple([time]+indices)
                
                # Fill in with the (None-padded) transition probability
                prob = self.transition_probability(*ngram)
                if time > 0:
                    # Multiply by the prob we must have come from
                    previous_state = tuple([time-1]+indices[1:]+[0])
                    prob *= forward_matrix[previous_state]
                forward_matrix[selector] += prob
            
            # Multiply in the emission probabilities
            forward_matrix[time] = (forward_matrix[time].transpose() * ems[time]).transpose()
            # Normalize
            coefficients[time] = logprob(numpy.sum(forward_matrix[time]))
            forward_matrix[time] /= numpy.sum(forward_matrix[time])
        
        for time in range(self.order-1, N):
            # Multiplying, the previous timestep gets broadcast over the 
            #  first axis of the transition matrix, which is what we need
            #  (that axis represents the most recent state in the n-gram)
            trans_step = forward_matrix[time-1] * trans
            # Sum probabilities over the last axis, i.e. the earliest state 
            #  in the n-gram
            trans_step = numpy.sum(trans_step, axis=-1)
            # Multiply in the emission probabilities
            forward_matrix[time] = (trans_step.transpose() * ems[time]).transpose()
            # Normalize the timestep
            coefficients[time] = logprob(numpy.sum(forward_matrix[time]))
            forward_matrix[time] /= numpy.sum(forward_matrix[time])
        
        if seq_prob:
            return forward_matrix, numpy.sum(coefficients)
        else:
            return forward_matrix
    
    def normal_backward_probabilities(self, sequence):
        """
        Return the backward probability matrices a Numpy array. This is 
        faster than L{backward_log_probabilities} because it uses Numpy 
        arrays with non-log probabilities and normalizes each timestep.
        
        @return: matrix over timesteps and all labels, with a dimension for 
            each state in each (n-1)-gram: for time steps 
            i and labels k, P(word^(i+1), ..., word^T | label_k^i)
        
        """
        N = len(sequence)
        states = self.label_dom
        S = len(states)
        
        # Prepare the transition and emission matrices
        trans_back = self.get_transition_matrix(transpose=True)
        ems = self.get_emission_matrix(sequence)
        
        if self.order == 1:
            # We can do this quickly for unigrams and it saves dealing with 
            #  dodgy cases of everything below
            # For unigrams, the backward probs are uniform
            backward_matrix = numpy.ones((N,S), numpy.float64) / S
            return backward_matrix
        
        # For other cases, things are a little more complicated
        # Initialize an empty matrix
        backward_matrix = numpy.zeros([N]+[S]*(self.order-1), numpy.float64)
        
        index_sets = _all_indices(self.order-1, S)
        
        # Initialize from the end
        for indices in index_sets:
            # Make an (n-1)-gram for the context
            ngram = [states[i] for i in indices]
            # Put the probability of going to the end state from each context
            # We read this from the model, since it's not in the trans matrix
            # Note that it's stored in transposed form (see below)
            selector = tuple([N-1]+list(reversed(indices)))
            backward_matrix[selector] = self.transition_probability(None, *ngram)
        backward_matrix[N-1] /= numpy.sum(backward_matrix[N-1])
        
        # Work backwards, filling in the matrix
        for time in range(N-2, self.order-2, -1):
            # Transposing the next timestep and the trans matrix causes their 
            #  indices to be reversed, so that the timestep is broadcast over 
            #  the last index (now the first)
            # Then we multiply in the emission probabilities, broadcast over 
            #  the first index (by doing it while transposed) and transpose 
            #  back to correct the indices
            # Summing over the 0th axis sums over possible next states 
            #  (the last element of the ngram in the next timestep)
            # To speed up the computations, we keep the whole lot transposed
            backward_matrix[time] = numpy.sum((trans_back * 
                                                backward_matrix[time+1]
                                                * ems[time+1]),
                                                    axis=-1)
            # Normalize over the timestep
            backward_matrix[time] /= numpy.sum(backward_matrix[time])
        
        # Fill in the first columns now, using None-padding histories
        for time in range(self.order-2, -1, -1):
            # Get the indices corresponding to all possible t-grams
            id_tgrams = _all_indices(time+1, S)
            
            for id_tgram in id_tgrams:
                # Get the actual ngram for these indices
                tgram = [self.label_dom[i] for i in id_tgram]
                # Fill this out to an (n-1)-gram stretching before the 
                #  start with Nones
                nm1gram = tgram + [None]*(self.order-2-time)
                # Pad indices with 0s
                id_nm1gram = id_tgram + [0]*(self.order-2-time)
                
                # Sum over the possible next states following this (n-1)-gram
                summed_prob = 0.0
                for next_id in range(S):
                    # Get transition probability from nm1gram to state next_id
                    prob = self.transition_probability(states[next_id], *nm1gram)
                    # Multiply in the emission probability for the next state
                    prob *= ems[time+1, next_id]
                    
                    # Multiply by the bwd prob for the next state
                    next_state = tuple([time+1]+list(reversed(id_nm1gram[:-1]))+[next_id])
                    prob *= backward_matrix[next_state]
                    # Sum this over the possible next states
                    summed_prob += prob
                backward_matrix[tuple([time]+list(reversed(id_nm1gram)))] = summed_prob
            
            # Normalize
            backward_matrix[time] /= numpy.sum(backward_matrix[time])
        
        # Now transpose all the timestep matrices back so the ngrams 
        #  correspond correctly to the indices
        for time in range(N):
            backward_matrix[time] = backward_matrix[time].transpose()
        
        return backward_matrix
        
    def normal_forward_backward_probabilities(self, sequence, forward=None, 
            backward=None):
        """
        A faster implementation of L{forward_backward_probabilities} for the 
        case where we're normalizing, using Numpy and non-log probabilities.
        
        This is still an S-dimensional matrix, not the state-occupation 
        probabilities. Use L{gamma_probabilities} to get that.
        
        """
        if forward is None:
            forward = self.normal_forward_probabilities(sequence)
        if backward is None:
            backward = self.normal_backward_probabilities(sequence)
        
        # This is simple with Numpy, since it does pointwise multiplication
        gamma = forward * backward
        # Now renormalize
        for time in range(len(sequence)):
            gamma[time] /= numpy.sum(gamma[time])
        return gamma
        
    def gamma_probabilities(self, sequence, dictionary=False,
            forward=None, backward=None):
        """
        State-occupation probabilities.
        
        @type dictionary: bool
        @param dictionary: return a list of label dictionaries instead 
            of a numpy matrix
        
        """
        fwd_bwd = self.normal_forward_backward_probabilities(sequence, 
                                forward=forward, backward=backward)
        # Sum over all but the first two dimensions: time and last state in ngram
        for i in range(fwd_bwd.ndim-2):
            fwd_bwd = numpy.sum(fwd_bwd, axis=-1)
            
        if dictionary:
            # Convert to a list of dictionaries, keyed by label
            gamma = []
            for t in range(fwd_bwd.shape[0]):
                dic = {}
                for s,state in enumerate(self.label_dom):
                    dic[state] = fwd_bwd[t,s]
                gamma.append(dic)
            return gamma
        else:
            return fwd_bwd
    
    def decode_gamma(self, sequence):
        """
        Use the state occupation probabilities to decode a sequence.
        
        """
        gamma = self.gamma_probabilities(sequence, dictionary=True)
        states = [max(timestep.items(), key=lambda x:x[1])[0] for timestep in gamma]
        return states
        
    def viterbi_decode(self, sequence):
        """
        Applies the Viterbi algorithm to return a single sequence of 
        states that maximises the probability of the sequence of 
        observations.
        
        """
        N = len(sequence)
        viterbi_matrix = [{} for i in range(N)]
        back_pointers = [{} for i in range(N)]
        def _trace_pointers(time, start_state, n):
            """
            Trace back through the pointer matrix from state start_state 
            at time time, return a list of length n of the states 
            (backwards in time).
            """
            if n == 0:
                return []
            elif time == 0:
                return [start_state] + ([None] * (n-1))
            else:
                state = back_pointers[time-1][start_state]
                return [start_state] + _trace_pointers(time-1, state, n-1)
            
        # Initialize the first column
        for label in self.label_dom:
            viterbi_matrix[0][label] = self.emission_log_probability(sequence[0], label) \
                                        + self.transition_log_probability(label, *([None]*(self.order-1)))
        
        # Fill in the other columns
        for i in range(1, N):
            for label in self.label_dom:
                # Work out the possible probabilities
                em = self.emission_log_probability(sequence[i], label)
                transitions = [ \
                    (self.transition_log_probability(label, *_trace_pointers(i-1, prev_label, self.order-1)) + 
                        viterbi_matrix[i-1][prev_label],
                     prev_label) for prev_label in self.label_dom]
                # Choose the previous state that maximises the Viterbi probability
                trans,prev_label = max(transitions)
                viterbi_matrix[i][label] =  trans + em
                # Set the pointer so we know what state we used
                back_pointers[i-1][label] = prev_label
        
        # Choose the most probable state to end in
        final_state = max([(prob,lab) for (lab,prob) in viterbi_matrix[N-1].items()])[1]
        states = _trace_pointers(N-1, final_state, N)
        return list(reversed(states))
        
    def generalized_viterbi(self, sequence, N=2):
        """
        Applies the N-best variant of the Viterbi algorithm to return 
        N sequences of states that maximize the probability of the 
        sequence of observations.
        
        @see: Generalization of the Viterbi Algorithm, Foreman, 1993
        
        @type N: int
        @param N: number of label sequences to return (defaults to 2)
        @rtype: list of (label sequence,probability) pairs
        @return: ordered list of possible decodings, paired with their 
            Viterbi probabilities
        
        """
        length = len(sequence)
        viterbi_matrix = [{} for i in range(length)]
        back_pointers = [{} for i in range(length)]
        def _trace_pointers(time, start_state, rank, n):
            """
            Trace back through the pointer matrix from state start_state 
            at time time, return, for a particular path (of the N-best we've 
            kept track of), a list of length n of the states (backwards 
            in time).
            
            Returns a single path
            
            """
            if n == 0:
                return []
            elif n==1:
                return [start_state]
            elif time == 0:
                return [start_state] + ([None] * (n-1))
            else:
                (prev_state,prev_rank) = back_pointers[time-1][start_state][rank]
                return [start_state] + _trace_pointers(time-1, prev_state, prev_rank, n-1)
            
        # Initialize the first column
        for t in range(self.order-1):
            for l,label in enumerate(self.label_dom):
                # There's only one possible path for each state at this point
                viterbi_matrix[t][l] = [ self.emission_log_probability(sequence[t], label) \
                                             + self.transition_log_probability(label, *([None]*(self.order-1-t))) ]
        
        trans = self.get_transition_matrix()
        
        # Fill in the other columns
        for i in range(self.order-1, length):
            for l0,label in enumerate(self.label_dom):
                # Work out the possible probabilities
                em = self.emission_log_probability(sequence[i], label)
                transitions = []
                for l1,prev_label in enumerate(self.label_dom):
                    # Work out the probability for coming from each of the 
                    #  top N ranked paths at the previous step
                    for prev_rank,prob in enumerate(viterbi_matrix[i-1][l1]):
                        selector = tuple([l0]+_trace_pointers(i-1, l1, prev_rank, self.order-1))
                        transitions.append(
                            (trans[selector] + prob, l1, prev_rank)
                        )
                # Choose up to N from the top of these
                top_N = list(reversed(sorted(transitions)))[:N]
                # Multiply in the emission probability to each
                top_probs = [trans_prob+em for (trans_prob,lab,rank) in top_N]
                viterbi_matrix[i][l0] =  top_probs
                # Set the pointer so we know what states and ranks we used
                back_pointers[i-1][l0] = [(lab,rank) for (trans_prob,lab,rank) in top_N]
        
        # Transition to the final state from each possible end state
        final_states = []
        for l1,prev_label in enumerate(self.label_dom):
            # Work out the probability for coming from each of the 
            #  top N ranked paths at the final step
            for prev_rank,prob in enumerate(viterbi_matrix[length-1][l1]):
                history = [self.label_dom[l] for l in \
                        _trace_pointers(length-1, l1, prev_rank, self.order-1)]
                final_prob = self.transition_log_probability(None, *history)
                final_states.append((prob+final_prob, l1, prev_rank))
        final_states = list(reversed(sorted(final_states)))[:N]
        # Now get a path for each of these
        path_probs = [
            (list(reversed(_trace_pointers(length-1, lab, rank, length))), prob) \
                for prob,lab,rank in final_states]
        # Transform the label indices into actual labels
        path_probs = [
            ([self.label_dom[l] for l in path], prob)
                for path,prob in path_probs]
        return path_probs
        
    def viterbi_selector_probabilities(self, sequence):
        """
        Returns a probability matrix like that given by the 
        forward-backward algorithm which assigns prob 1.0 to the Viterbi
        chosen tags and 0.0 to all others.
        
        """
        vit_seq = self.viterbi_decode(sequence)
        return [dict([(label, 1.0 if label == vit_lab else 0.0) for label in self.label_dom]) \
                    for vit_lab in vit_seq]
    
    def generate(self, length=10, labels=False):
        """
        Generate a sequence of emissions at random using the n-gram 
        model.
        If labels=True, outputs a sequence of (emission,label) pairs 
        indicating what hidden labels emitted the emissions.
        
        The sequence will have maximum length C{length}, but may be shorter 
        if the model so determines.
        
        """
        from jazzparser.utils.probabilities import random_selection
        sequence = []
        label_seq = []
        tag_context = [None]*(self.order-1)
        
        for i in range(length):
            # Get the transition probabilities to all possible states
            trans_probs = {}
            for lab in self.label_dom+[None]:
                trans_probs[lab] = self.transition_probability(lab, *tag_context)
            
            # Pick a label to use next
            new_lab = random_selection(trans_probs.items())
            if new_lab is None:
                # We've reached the end state: stop here
                break
            
            label_seq.append(new_lab)
            # Set the state to reflect this label choice
            if self.order > 1:
                tag_context = [new_lab] + tag_context[:-1]
            
            # Get all the emission probabilities from this state
            em_probs = {}
            for em in self.emission_dom:
                em_probs[em] = self.emission_probability(em, new_lab)
            # Pick an emission randomly
            sequence.append(random_selection(em_probs.items()))
            
        if labels:
            return zip(sequence, label_seq)
        else:
            return sequence
    
    def labeled_sequence_log_probability(self, sequence, labels):
        """
        Computes the joint probability that the model assigns to a sequence 
        and its gold standard labels.
        
        Probability is a log, because we'd get underflow otherwise.
        
        """
        from collections import deque
        labeled_data = zip(sequence, labels)
        
        # Keep track of the current label history
        history = deque([None] * (self.order-1))
        
        # Multiply the probabilities of all the labels and the emissions
        joint_logprob = 0.0
        
        for em,label in labeled_data:
            # Get the transition probability of this label given its history
            joint_logprob += self.transition_log_probability(label, *history)
            joint_logprob += self.emission_log_probability(em, label)
            
            if self.order > 1:
                # Move the history along
                history.pop()
                history.appendleft(label)
        return joint_logprob
            
    def get_all_ngrams(self, n):
        """
        Returns all possible ngrams of length n composed of elements 
        from this model's domain.
        
        """
        if n == 0:
            return [[]]
        elif n == 1:
            return [[lab] for lab in self.label_dom]
        else:
            return sum([[[label]+copy.deepcopy(ngram) for label in self.label_dom] for ngram in self.get_all_ngrams(n-1)], [])
    
    def precompute(self):
        """
        Creates a L{PrecomputedNgramModel} from this NgramModel.
        
        """
        trans_mat = self.get_transition_matrix()
        return PrecomputedNgramModel(
                            order = self.order, 
                            label_counts = self.label_counts, 
                            emission_counts = self.emission_counts, \
                            estimator = self._estimator, \
                            backoff_model = self.backoff_model, \
                            label_dom = self.label_dom, 
                            emission_dom = self.emission_dom,
                            transition_matrix = trans_mat)
            
    def to_picklable_dict(self):
        """
        Produces a picklable representation of model as a dict.
        You can't just pickle the object directly because some of the 
        NLTK classes can't be pickled. You can pickle this dict and 
        reconstruct the model using NgramModel.from_picklable_dict(dict).
        
        """
        from jazzparser.utils.nltk.storage import object_to_dict
        if self.backoff_model is None:
            backoff = None
        else:
            backoff = self.backoff_model.to_picklable_dict()
        
        return {
            'order' : self.order,
            'label_dom' : self.label_dom,
            'emission_dom' : self.emission_dom,
            'label_counts' : object_to_dict(self.label_counts),
            'emission_counts' : object_to_dict(self.emission_counts),
            'estimator' : self._estimator,
            'backoff_model' : backoff,
        }
        
    @staticmethod
    def from_picklable_dict(data, *args, **kwargs):
        """
        Reproduces an n-gram model that was converted to a picklable 
        form using to_picklable_dict.
        
        Extra args/kwargs are passed to the class constructor.
        
        """
        from jazzparser.utils.nltk.storage import dict_to_object
        
        # Instantiate a different class (subclass) if given
        cls = kwargs.pop('cls', NgramModel)
        
        if data['backoff_model'] is None:
            backoff = None
        else:
            # Recursively construct the backoff model
            # This is always an NgramModel, not the subclass
            backoff = NgramModel.from_picklable_dict(data['backoff_model'])
        
        return cls(data['order'],
                          dict_to_object(data['label_counts']),
                          dict_to_object(data['emission_counts']),
                          data['estimator'],
                          backoff,
                          data['label_dom'],
                          data['emission_dom'],
                          *args, **kwargs)
    
    #######################################
    ##### Old methods, now removed
    def forward_log_probabilities(self, sequence, normalize=True):
        """
        B{Removed.} Use L{normal_forward_probabilities} and take logs if 
        you're happy with normalized probabilities. Otherwise, 
        L{normal_forward_probabilities} needs to be made to return the 
        sums it normalizes by.
        
        """
        raise NotImplementedError, "deprecated"
    
    def forward_probabilities(self, sequence, normalize=True):
        """ B{Removed.} See note on L{forward_log_probabilities}. """
        raise NotImplementedError, "deprecated"
        
    def backward_log_probabilities(self, sequence, normalize=True):
        """ B{Removed.} See L{forward_log_probabilities} """
        raise NotImplementedError, "deprecated"
    
    def backward_probabilities(self, sequence, normalize=True):
        """ B{Removed.} See L{forward_log_probabilities} """
        raise NotImplementedError, "deprecated"
        
    def forward_backward_log_probabilities(self, sequence, normalize=True):
        """
        B{Removed.} See L{forward_log_probabilities}. Use either 
        L{normal_forward_backward_probabilities} or L{gamma_probabilities}.
        
        """
        raise NotImplementedError, "deprecated"
        
    def forward_backward_probabilities(self, *args, **kwargs):
        """ B{Removed.} See L{forward_backward_log_probabilities} """
        raise NotImplementedError, "deprecated"

class PrecomputedNgramModel(NgramModel):
    """
    Overrides parts of L{NgramModel} to provide exactly the same interface, but 
    stores the precomputed transition matrix and uses this to provide 
    transition probabilities. This makes using the model a lot faster if 
    you're doing things like forward-backward computations, since it needs the 
    full transition matrix anyway. This processing is effectively pushed to 
    training time instead of testing time.
    
    """
    def __init__(self, *args, **kwargs):
        transition_matrix = kwargs.pop('transition_matrix')
        NgramModel.__init__(self, *args, **kwargs)
        # Use the precomputed transition matrix to get transition probabilities
        self.transition_matrix = transition_matrix
        # Prepare a dictionary mapping ngrams to their matrix indices
        self._indices = dict(
            [(tuple([self.label_dom[s] for s in ngram]), tuple(ngram)) 
                    for ngram in _all_indices(self.order, len(self.label_dom))])
        
    @staticmethod
    def train(*args, **kwargs):
        """
        Just calls L{NgramModel}'s train method and converts the result to a 
        PrecomputedNgramModel.
        
        """
        model = NgramModel.train(*args, **kwargs)
        return model.precompute()
        
    def transition_probability(self, *ngram):
        """
        Like the superclass, but read off from the precomputed matrix.
        
        @see: NgramModel.transition_log_probability
        
        """
        if None in ngram:
            # Can't read this from the matrix, since it doesn't store 
            #  initial and final transitions
            return NgramModel.transition_probability(self, *ngram)
        else:
            return self.transition_matrix[self._indices[ngram]]
        
    def transition_log_probability(self, *ngram):
        """
        Like the superclass, but read off from the precomputed matrix.
        
        @see: NgramModel.transition_log_probability
        
        """
        if None in ngram:
            # Can't read this from the matrix, since it doesn't store 
            #  initial and final transitions
            return NgramModel.transition_log_probability(self, *ngram)
        else:
            return logprob(self.transition_matrix[self._indices[ngram]])

    def get_transition_matrix(self, transpose=False):
        """
        Returns the precomputed transition matrix.
        
        @see: NgramModel.get_transition_matrix
        
        """
        if transpose:
            # We still cache the transposed matrix as in NgramModel
            if self._transition_matrix_transpose_cache is None:
                # Ensure that the normal transition matrix has been generated
                mat = self.get_transition_matrix()
                # Tranpose it and copy it, so it's a real array, not a view
                self._transition_matrix_transpose_cache = numpy.copy(mat.transpose())
            return self._transition_matrix_transpose_cache
        else:
            # Just return the precomputed matrix
            return self.transition_matrix
    
    def to_picklable_dict(self):
        from StringIO import StringIO
        # Use the super method to pickle everything it stores
        data = NgramModel.to_picklable_dict(self)
        
        # Additionally store the transition matrix
        # Use Numpy's save method to convert it to binary data
        buff = StringIO()
        numpy.save(buff, self.transition_matrix)
        matrix_data = buff.getvalue()
        buff.close()
        
        data['transition_matrix'] = matrix_data
        return data
        
    @staticmethod
    def from_picklable_dict(data):
        from StringIO import StringIO
        
        if 'transition_matrix' not in data:
            # Probably trying to load from NgramModel data
            raise NgramError, "could not load PrecomputedNgramModel: "\
                "no precomputed transition matrix has been stored"
        # Pull out the transition matrix
        matrix_data = data.pop('transition_matrix')
        # Load a Numpy array from this data
        buff = StringIO(matrix_data)
        transition_matrix = numpy.load(buff)
        buff.close()
        
        model = NgramModel.from_picklable_dict(data, 
                                              cls=PrecomputedNgramModel,
                                              # Extra kwarg to constructor
                                              transition_matrix=transition_matrix)
        return model
    

class NgramError(Exception):
    pass

