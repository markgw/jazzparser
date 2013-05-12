"""Ngram-multi tagging model.

@see: jazzparser.taggers.ngram_multi.tagger

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

from numpy import ones, float64, sum as array_sum, zeros
import copy, numpy

from jazzparser.utils.nltk.ngram import NgramModel
from jazzparser.utils.nltk.probability import logprob, add_logs, \
                        sum_logs, prob_dist_to_dictionary_prob_dist, \
                        cond_prob_dist_to_dictionary_cond_prob_dist, \
                        CutoffConditionalFreqDist, CutoffFreqDist
from jazzparser.utils.strings import str_to_bool
from jazzparser.utils.loggers import create_dummy_logger
from jazzparser.utils.base import group_pairs
from .. import TaggerTrainingError

from nltk.probability import ConditionalProbDist, FreqDist, \
            ConditionalFreqDist, DictionaryProbDist, \
            DictionaryConditionalProbDist, MutableProbDist

def _all_indices(length, num_labels):
    """
    Function to generate all index n-grams of a given length
    
    """
    if length < 1:
        return [[]]
    else:
        return sum([ [[i]+sub for i in range(num_labels)]
                        for sub in _all_indices(length-1, num_labels)], [])

class MultiChordNgramModel(NgramModel):
    """
    An ngram model that takes multiple chords (weighted by probability) as 
    input to its decoding. It is trained on labeled data.
    
    State labels are pairs (root,schema), each representing a lexical 
    schema instantiated on a specific root, i.e. a lexical category.
    Emissions are pairs (root,label), representing chords. The parameters 
    are tied so that chords (r,l) can only be emitted from states (r,s).
    
    The component distributions that are actually stored are:
     - P(label | schema, chord_root=state_root)  C{emission_dist}
     - P(schema[t] | schema[t-1])                C{schema_transition_dist}
     - P(root[t] - root[t-1] | schema[t-1])      C{root_transition_dist}
        
    """
    def __init__(self, order, root_transition_counts, schema_transition_counts, 
                    emission_counts, 
                    estimator, backoff_model, schemata, chord_vocab, 
                    history=""):
        self.order = order
        self.backoff_model = backoff_model
        
        chord_vocab = list(set(chord_vocab))
        
        # Construct the domains by combining possible roots with 
        #  the other components of the labels
        self.label_dom = [(root,schema) for root in range(12) \
                                        for schema in schemata]
        self.num_labels = len(self.label_dom)
        self.emission_dom = [(root,label) for root in range(12) \
                                        for label in chord_vocab]
        self.num_emissions = len(self.emission_dom)
        
        self.schemata = schemata
        self.chord_vocab = chord_vocab
        
        # Keep hold of the freq dists
        self.root_transition_counts = root_transition_counts
        self.schema_transition_counts = schema_transition_counts
        self.emission_counts = emission_counts
        
        # Make some prob dists
        self.root_transition_dist = ConditionalProbDist(
                                    root_transition_counts, estimator, 12)
        self.schema_transition_dist = ConditionalProbDist(
                            schema_transition_counts, estimator, len(schemata)+1)
        self.emission_dist = ConditionalProbDist(
                            emission_counts, estimator, len(chord_vocab)+1)
        
        self._estimator = estimator
        
        # Store a string with information about training, etc
        self.history = history
        
        # Initialize the various caches
        # These will be filled as we access probabilities
        self.clear_cache()
    
    def clear_cache(self):
        """
        Initializes or empties probability distribution caches.
        
        Make sure to call this if you change or update the distributions.
        
        No caches used thus far, so this does nothing for now, except call 
        the super method.
        
        """
        self._schema_transition_matrix_cache = None
        self._schema_transition_matrix_transpose_cache = None
        self._root_transition_matrix_cache = None
        return NgramModel.clear_cache(self)
        
    def add_history(self, string):
        """ Adds a line to the end of this model's history string. """
        self.history += "%s: %s\n" % (datetime.now().isoformat(' '), string)
    
    @staticmethod
    def train(data, schemata, chord_types, estimator, cutoff=0, logger=None, 
                chord_map=None, order=2, backoff_orders=0, backoff_kwargs={}):
        """
        Initializes and trains an HMM in a supervised fashion using the given 
        training data. Training data should be chord sequence data (input 
        type C{bulk-db} or C{bulk-db-annotated}).
        
        """
        # Remove any sequences that aren't fully labeled
        sequences = [
            sequence for sequence in data if \
                    all([c.category is not None and len(c.category) \
                            for c in sequence.chords])
        ]
        
        if len(sequences) == 0:
            raise TaggerTrainingError, "empty training data set"
        
        # Prepare a dummy logger if none was given
        if logger is None:
            logger = create_dummy_logger()
        logger.info(">>> Beginning training of multi-chord ngram tagging model")
        
        # Prepare training data from these sequences
        # Training set for emission dist
        if chord_map is None:
            chord_trans = lambda x:x
        else:
            chord_trans = lambda x: chord_map[x]
        emission_data = sum([
            [(chord.category, chord_trans(chord.type)) 
                                                for chord in sequence.chords] 
                                                for sequence in sequences], [])
        
        # Train the emission distribution
        emission_counts = CutoffConditionalFreqDist(cutoff)
        for schema,ctype in emission_data:
            emission_counts[schema].inc(ctype)
        
        # Train the transition distribution
        schema_transition_counts = CutoffConditionalFreqDist(cutoff)
        root_transition_counts = CutoffConditionalFreqDist(cutoff)
        
        for sequence in sequences:
            # Add a count for the transition to the final state
            final_ngram = tuple([c.category for c in sequence.chords[-order:-1]])
            schema_transition_counts[sequence.chords[-1].category].inc(None)
            # Make n-gram counts
            transition_data = [None]*(order-1) + sequence.chords
            
            for i in range(len(transition_data)-order):
                ngram = list(reversed(transition_data[i:i+order]))
                
                # Count the schema transition
                schema_ngram = [c.category if c is not None else None for c in ngram]
                schema_transition_counts[tuple(schema_ngram[1:])].inc(schema_ngram[0])
                
                # Now count the relative root, conditioned on the schema
                if order > 1 and ngram[1] is not None:
                    root_change = (ngram[0].root - ngram[1].root) % 12
                    root_transition_counts[ngram[1].category].inc(root_change)
        
        if backoff_orders > 0:
            # Train a lower-order model
            kwargs = {
                'cutoff' : cutoff,
                'logger' : logger, 
                'chord_map' : chord_map,
            }
            kwargs.update(backoff_kwargs)
            # These kwargs can't be overridden
            kwargs['order'] = order-1
            kwargs['backoff_orders'] = backoff_orders-1
            # Run the model training
            backoff_model = MultiChordNgramModel.train(
                                                    data, 
                                                    schemata, 
                                                    chord_types,
                                                    estimator,
                                                    **kwargs)
        else:
            backoff_model = None
        
        # Instantiate a model with these distributions
        model = MultiChordNgramModel(order,
                                      root_transition_counts, 
                                      schema_transition_counts, 
                                      emission_counts, 
                                      estimator, 
                                      backoff_model,
                                      schemata, 
                                      chord_types)
        return model
    
    
    ################## Probabilities ###################
    def _get_transition_backoff_scaler(self, context):
        # This is just for the schema distribution
        if context not in self._discount_cache:
            # The prob mass reserved for unseen events can be computed by 
            #  summing probabilities over all seen events and subtracting 
            #  from 1.
            # Our discounting model distributes this probability evenly over 
            #  the unseen events, so we can compute the discounted mass by 
            #  getting the probability of one unseen event and multiplying it.
            seen_labels = set([lab for lab in self.schemata+[None] if 
                                        self.schema_transition_counts[context][lab] > 0])
            if len(seen_labels) == 0:
                # Not seen anything in this context. All mass is discounted!
                self._discount_cache[context] = 0.0
            else:
                unseen_labels = set(self.schemata+[None]) - seen_labels
                # Try getting some event that won't have been seen
                # Compute how much mass is reserved for unseen events
                discounted_mass = self.schema_transition_dist[context].prob(
                                                    "%%% UNSEEN LABEL %%%") \
                                                * len(unseen_labels)
                # Compute how much probability the n-1 order model assigns to 
                #  things unseen by this model
                backoff_context = context[:-1]
                backoff_seen_mass = sum_logs([
                    self.backoff_model.schema_transition_log_probability_schemata(lab, 
                                                        *backoff_context) 
                                                    for lab in unseen_labels])
                self._discount_cache[context] = logprob(discounted_mass) - \
                                                        backoff_seen_mass
        return self._discount_cache[context]
        
    def schema_transition_log_probability(self, *states):
        """
        Just the schema part of the transition distribution.
        
        """
        schemata = [state[1] if state is not None else None \
                        for state in states]
        return self.schema_transition_log_probability_schemata(*schemata)
    
    def schema_transition_log_probability_schemata(self, schema, *previous_schemata):
        """
        Just the schema part of the transition distribution. This method 
        takes just schemata as args, instead of whole states.
        
        """
        if len(previous_schemata):
            schemata = tuple(previous_schemata)
        else:
            schemata = tuple()
        
        # Check whether we have enough observations of this whole n-gram
        if self.backoff_model is not None and self.schema_transition_counts[schemata][schema] == 0:
            # Backoff to a lower-order model
            # Work out how much prob mass is reserved for unseen events
            scale = self._get_transition_backoff_scaler(schemata)
            # Backoff and scale to fill the reserved mass
            schema_prob = scale + self.backoff_model.schema_transition_log_probability_schemata(schema, *(previous_schemata[:-1]))
        else:
            schema_prob = self.schema_transition_dist[schemata].logprob(schema)
        return schema_prob
        
    def transition_log_probability(self, state, *previous_states):
        previous_states = [s if s is not None else (None,None) for s in previous_states]
        if self.order == 1:
            roots,schemata = [],[]
        else:
            roots,schemata = zip(*previous_states)
        schemata = tuple(schemata)
        
        # Use the separate method to get the probability from the schema dist
        schema_prob = self.schema_transition_log_probability(state, *previous_states)
        
        # Then the root transition distribution
        # Don't look at the root transition if this is a unigram model
        if self.order == 1 or all(s is None for s in schemata):
            # All roots equiprobable
            root_prob = - logprob(12)
        elif state is None:
            # Final state: no root transition, prob comes from state dist
            root_prob = 0
        else:
            # Calculate the root change from the previous chord
            root_change = (state[0] - roots[0]) % 12
            # Condition the root change prob on the *previous* schema
            root_prob = self.root_transition_dist[schemata[0]].logprob(root_change)
        
        # Multiply together the probability of the schema transition and the 
        #  root change
        return root_prob + schema_prob
        
    def emission_log_probability(self, emission, state):
        """
        Gives the probability P(emission | label). Returned as a base 2
        log.
        
        The emission should be a pair of (root,label), together defining a 
        chord.
        
        There's a special case of this. If the emission is a list, it's 
        assumed to be a I{distribution} over emissions. The list should 
        contain (prob,em) pairs, where I{em} is an emission, such as is 
        normally passed into this function, and I{prob} is the weight to 
        give to this possible emission. The probabilities of the possible 
        emissions are summed up, weighted by the I{prob} values.
        
        """
        if type(emission) is list:
            # Average probability over the possible emissions
            probs = []
            for (prob,em) in emission:
                probs.append(logprob(prob) + \
                             self.emission_log_probability(em, state))
            return sum_logs(probs)
        
        # Single chord label
        state_root,schema = state
        chord_root,label = emission
        # Probability is 0 if the roots don't match
        if state_root != chord_root:
            return float('-inf')
        else:
            return self.emission_dist[schema].logprob(label)
    
    ##############################################
    # We override the forward and backward computations. Using the generic 
    # implementation, with the full transition matrix, takes a lot of 
    # memory with this model (and it's not necessary)
    
    def get_schema_transition_matrix(self, transpose=False):
        """ Transition matrix just for the schema distribution. """
        if transpose:
            if self._schema_transition_matrix_transpose_cache is None:
                # Ensure that the normal transition matrix has been generated
                mat = self.get_schema_transition_matrix()
                # Tranpose it and copy it, so it's a real array, not a view
                self._schema_transition_matrix_transpose_cache = \
                                            numpy.copy(mat.transpose())
            return self._schema_transition_matrix_transpose_cache
        else:
            if self._schema_transition_matrix_cache is None:
                # Compute the matrix from scratch, as we've not done it yet
                N = len(self.schemata)
                shape = tuple([N]*self.order)
                trans = numpy.zeros(shape, numpy.float64)
                # Build a list of lists, each n long, with all possible array indices
                index_sets = _all_indices(self.order, N)
                # Fill the matrix
                for indices in index_sets:
                    # Get the ngram of state labels for this ngram of array indices
                    ngram_schemata = [self.schemata[i] for i in indices]
                    trans[tuple(indices)] = 2**self.schema_transition_log_probability_schemata(*ngram_schemata)
                
                self._schema_transition_matrix_cache = trans
            return self._schema_transition_matrix_cache
    
    def get_root_transition_matrix(self):
        """ Transition matrix just for the root change distribution. """
        if self._root_transition_matrix_cache is None:
            # Compute the matrix from scratch, as we've not done it yet
            N = len(self.schemata)
            trans = numpy.zeros((12,12,N), numpy.float64)
            # Unigram case: all equiprobable
            if self.order == 1:
                trans[:,:,:] = 1.0/12
            else:
                # Fill the matrix
                for i,schema in enumerate(self.schemata):
                    for root_change in range(12):
                        # Get the probability for this root *change*
                        root_prob = self.root_transition_dist[schema].prob(root_change)
                        # Fill this in for each pair of roots that have this difference
                        roots = [(last_root+root_change)%12 for last_root in range(12)]
                        last_roots = range(12)
                        # Select all pairs of roots with this difference and 
                        #  set the probability
                        trans[roots,last_roots,i] = root_prob
            self._root_transition_matrix_cache = trans
        return self._root_transition_matrix_cache
        
    def get_schema_emission_matrix(self, sequence):
        """
        Emission matrix for states decomposed into schema and root. 
        Matrix has dimensions (time, root, schema).
        
        """
        T = len(sequence)
        S = len(self.schemata)
        ems = numpy.zeros((T, 12, S), numpy.float64)
        # Set the probability for every timestep...
        for t,emission in enumerate(sequence):
            # ...given each state
            for root in range(12):
                for i,schema in enumerate(self.schemata):
                    ems[t,root,i] = self.emission_probability(emission, (root,schema))
        return ems
    
    def normal_forward_probabilities(self, sequence, root_schema=False):
        """
        @see: jazzparser.utils.nltk.ngram.model.NgramModel.normal_forward_probabilities
        @note: tested against superclass method. They're giving the same 
            results to a high precision (differences ~1e-20)
        @return: if root_schema=True, 
            (S+1)-dimensional Numpy array, where S is the number of schemata.
            The dimensions are (time, last root, last schema, previous schema, etc).
            Otherwise, the array has the same definition as the superclass.
        
        """
        N = len(sequence)
        states = self.label_dom
        schemata = self.schemata
        
        # Prepare the transition and emission matrices
        schema_ems = self.get_schema_emission_matrix(sequence)
        sc_trans = self.get_schema_transition_matrix()
        root_trans = self.get_root_transition_matrix()
        
        if self.order == 1:
            # We can do this quickly for unigrams
            # We only use emission probabilities: transition probs 
            #  just supply (unconditioned) priors
            # We can ignore the root transitions: all equiprobable
            forward_matrix = sc_trans*schema_ems
            # Normalize
            for t in range(N):
                forward_matrix[t] /= numpy.sum(forward_matrix[t])
            if not root_schema:
                return forward_matrix.reshape(N,12*len(schemata))
            return forward_matrix
            
        # Initialize an empty matrix
        forward_matrix = numpy.zeros([N,12]+[len(schemata)]*(self.order-1), numpy.float64)
        
        # First fill in the first columns with histories padded with Nones
        # In these columns, we only use a subset of the dimensions
        # Simplest to do this exhaustively over all states
        for time in range(self.order-1):
            # Get the indices corresponding to all possible sub-n-grams
            #  between the start and here
            index_sets = _all_indices(time+1, len(schemata))
            
            for indices in index_sets:
                # Get the actual ngram for these indices
                ngram = [schemata[i] for i in indices]
                # Pad with Nones to a length of n
                ngram.extend([None]*(self.order-time-1))
                # Pad the indices with 0s so we use all the dimensions
                indices.extend([0]*(self.order-time-2))
                # Probability of this schema transition
                schema_prob = 2**self.schema_transition_log_probability_schemata(*ngram)
                
                if time == 0:
                    # All roots equiprobable
                    selector = tuple([time,slice(None)]+indices)
                    forward_matrix[selector] += schema_prob
                else:
                    # Multiply by the prob we came from, considering all possible roots
                    previous_states = forward_matrix[
                                        tuple([time-1,slice(None)] + indices[1:]+[0])]
                    # Multiply in the appropriate root transitions
                    # Sum over possible previous roots
                    root_probs = numpy.sum(
                                    root_trans[:,:,indices[1]] * previous_states, 
                                        axis=1)
                    # root_probs is now a 1D array of probs for each possible 
                    #  root in the current state
                    selector = tuple([time,slice(None)]+indices)
                    forward_matrix[selector] += root_probs
            
            # Multiply in the emission probabilities
            forward_matrix[time] = (forward_matrix[time].transpose() * schema_ems[time].transpose()).transpose()
            # Normalize
            forward_matrix[time] /= numpy.sum(forward_matrix[time])
        
        for time in range(self.order-1, N):
            # Multiplying, the previous timestep gets broadcast over the 
            #  first axis of the transition matrix, which is what we need
            #  (that axis represents the most recent state in the n-gram)
            trans_step = forward_matrix[time-1,:,numpy.newaxis] * sc_trans
            # DIMS: (root[-1], schema, schema[-1], ..., schema[-n+1])
            # Dimension 0 currently represents the *previous* root
            # Multiply in the root transition probabilities
            trans_step = trans_step[numpy.newaxis].transpose() * root_trans[:,:,numpy.newaxis,:].transpose()
            # DIMS: (schema[-n+1], ..., schema, root[-1], root)
            # Note that we don't transpose back yet
            # Sum probabilities over the last axis, i.e. the earliest schema 
            #  in the n-gram
            trans_step = numpy.sum(trans_step, axis=0)
            # DIMS: (schema[-n+2], ..., schema, root[-1], root)
            # Dimension 0 (i.e. -1) is now a new dim representing the *current* root
            # Sum over previous roots, now dim 1 (i.e. -2)
            trans_step = numpy.sum(trans_step, axis=-2)
            # DIMS: (schema[-n+2], ..., schema, root)
            # Multiply in the emission probabilities
            # Now we transpose back
            forward_matrix[time] = (trans_step * schema_ems[time].transpose()).transpose()
            # DIMS: (root, schema, ..., schema[-n+2])
            # Normalize the timestep
            forward_matrix[time] /= numpy.sum(forward_matrix[time])
            
        if not root_schema:
            # Convert to a state matrix
            new_forward_matrix = numpy.zeros([N,len(states)]*(self.order-1), numpy.float64)
            indices = _all_indices(self.order-1, len(states))
            for time in range(N):
                for state_indices in indices:
                    # Get the index into the new-style matrix
                    schema_indices = [self.schemata.index(self.label_dom[i][1]) \
                                                        for i in state_indices]
                    root = self.label_dom[state_indices[0]][0]
                    selector = tuple([time,root]+schema_indices)
                    # Set the value in the matrix we're creating
                    new_forward_matrix[tuple([time]+state_indices)] = forward_matrix[selector]
            return new_forward_matrix
        return forward_matrix
    
    def normal_backward_probabilities(self, sequence, root_schema=False):
        """
        @see: jazzparser.utils.nltk.ngram.model.NgramModel.normal_backward_probabilities
        @return: if root_schema=True, 
            (S+1)-dimensional Numpy array, where S is the number of schemata.
            The dimensions are (time, last root, last schema, previous schema, etc).
            Otherwise, the array has the same definition as the superclass.
        
        """
        N = len(sequence)
        states = self.label_dom
        schemata = self.schemata
        S = len(schemata)
        
        if self.order == 1:
            # We can do this quickly for unigrams and it saves dealing with 
            #  dodgy cases of everything below
            # For unigrams, the backward probs are uniform
            if root_schema:
                backward_matrix = numpy.ones((N,12,S), numpy.float64) / (12*S)
            else:
                backward_matrix = numpy.ones((N,12*S), numpy.float64) / (12*S)
            return backward_matrix
        
        # Prepare the transition and emission matrices
        schema_ems = self.get_schema_emission_matrix(sequence)
        # We add an extra dim to the end of this to allow for the root axis
        sc_trans_back = self.get_schema_transition_matrix()
        sc_trans_back = numpy.copy(sc_trans_back[numpy.newaxis].transpose())
        root_trans = self.get_root_transition_matrix().transpose()
        
        # For other cases, things are a little more complicated
        # Initialize an empty matrix
        backward_matrix = numpy.zeros([N]+[S]*(self.order-1)+[12], numpy.float64)
        
        index_sets = _all_indices(self.order-1, S)
        
        # Initialize from the end
        for indices in index_sets:
            # Make an (n-1)-gram for the context
            ngram = [schemata[i] for i in indices]
            # Put the probability of going to the end state from each context
            # Ignore the root transition: final state is only in the schema dist
            # Note we store this in transposed form (see below)
            selector = tuple([N-1]+list(reversed(indices))+[slice(None)])
            backward_matrix[selector] = 2**self.schema_transition_log_probability_schemata(None, *ngram)
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
            
            # Multiply in the emission probabilities
            bwd = schema_ems[time+1].transpose() * backward_matrix[time+1]
            # sc_trans_back has an extra axis at the end so it's broadcast
            #  over the root axis
            bwd = sc_trans_back * bwd
            # DIMS: (schema[-n+2], ..., schema[1], root[1])
            # Sum over next schemata: the root transition is not dependent on them
            bwd = numpy.sum(bwd, axis=-2)
            # DIMS: (schema[-n+2], ..., schema, root[1])
            # Add a new axis second from the end to accommodate this timestep's roots
            bwd = (bwd.transpose()[:,numpy.newaxis]).transpose()
            # DIMS: (schema[-n+2], ..., schema, (root), root[1])
            # The final dimension of this will be the *next* root
            bwd = bwd * root_trans
            # DIMS: (schema[-n+2], ..., schema, root, root[1])
            # Sum over next roots
            bwd = numpy.sum(bwd, axis=-1)
            # DIMS: (schema[-n+2], ..., schema, root)
            backward_matrix[time] = bwd
            # Normalize over the timestep
            backward_matrix[time] /= numpy.sum(backward_matrix[time])
        
        # Fill in the first columns now, using None-padding histories
        for time in range(self.order-2, -1, -1):
            # Get the indices corresponding to all possible t-grams
            id_tgrams = _all_indices(time+1, S)
            
            for id_tgram in id_tgrams:
                # Get the actual ngram for these indices
                tgram = [schemata[i] for i in id_tgram]
                # Fill this out to an (n-1)-gram stretching before the 
                #  start with Nones
                nm1gram = tgram + [None]*(self.order-2-time)
                # Pad indices with 0s
                id_nm1gram = id_tgram + [0]*(self.order-2-time)
                
                # Sum over the possible next states following this (n-1)-gram
                summed_prob = 0.0
                for next_id in range(S):
                    # Get schema transition probability from nm1gram to next_id
                    schema_prob = 2**self.schema_transition_log_probability_schemata(schemata[next_id], *nm1gram)
                    # Consider each possible next root
                    for next_root in range(12):
                        # Multiply in the emission probability for the next state
                        prob = schema_prob * schema_ems[time+1, next_root, next_id]
                    
                        # Multiply by the bwd prob for the next state
                        next_state = tuple([time+1]+list(reversed(id_nm1gram[:-1]))+[next_id,next_root])
                        prob *= backward_matrix[next_state]
                        
                        # Consider all possible current roots
                        for current_root in range(12):
                            if time > 0:
                                root_change = (next_root - current_root) % 12
                                root_prob = self.root_transition_dist[nm1gram[0]].prob(root_change)
                            else:
                                # All roots equiprobable
                                root_prob = 1.0/12
                            backward_matrix[tuple(
                                        [time] + 
                                        list(reversed(id_nm1gram)) + 
                                        [current_root])] += prob * root_prob
            
            # Normalize
            backward_matrix[time] /= numpy.sum(backward_matrix[time])
        
        # Now transpose all the timestep matrices back so the ngrams 
        #  correspond correctly to the indices
        reordered_backward_matrix = numpy.zeros([N,12]+[S]*(self.order-1), numpy.float64)
        for time in range(N):
            reordered_backward_matrix[time] = backward_matrix[time].transpose()
        
        if not root_schema:
            # Convert to a state matrix
            new_backward_matrix = numpy.zeros([N,len(states)]*(self.order-1), numpy.float64)
            indices = _all_indices(self.order-1, len(states))
            for time in range(N):
                for state_indices in indices:
                    # Get the index into the new-style matrix
                    schema_indices = [self.schemata.index(self.label_dom[i][1]) \
                                                        for i in state_indices]
                    root = self.label_dom[state_indices[0]][0]
                    selector = tuple([time,root]+schema_indices)
                    # Set the value in the matrix we're creating
                    new_backward_matrix[tuple([time]+state_indices)] = reordered_backward_matrix[selector]
            return new_backward_matrix
        return reordered_backward_matrix
        
    def gamma_probabilities(self, sequence, dictionary=False,
            forward=None, backward=None):
        """
        State-occupation probabilities.
        
        Overridden so we don't need to construct the full ngram matrix, 
        which can be huge with trigrams to the point of running out of 
        memory.
        
        @type dictionary: bool
        @param dictionary: return a list of label dictionaries instead 
            of a numpy matrix
        
        """
        # Don't use normal_forward_backward_probabilities: just get the 
        #  root_schema version of the matrices
        forward = self.normal_forward_probabilities(sequence, root_schema=True)
        backward = self.normal_backward_probabilities(sequence, root_schema=True)
        gamma = forward * backward
        # Sum over all but the first three dimensions: time and last root 
        #  and schema in ngram
        for i in range(gamma.ndim-3):
            gamma = numpy.sum(gamma, axis=-1)
        
        (T,R,S) = gamma.shape
        # Renormalize
        for t in range(T):
            gamma[t] /= numpy.sum(gamma[t])
            
        if dictionary:
            # Convert to a list of dictionaries, keyed by label
            dict_gamma = []
            for t in range(T):
                dic = {}
                for r in range(12):
                    for s,schema in enumerate(self.schemata):
                        dic[(r,schema)] = gamma[t,r,s]
                dict_gamma.append(dic)
            return dict_gamma
        else:
            # Convert to a matrix of state probabilities
            new_gamma = numpy.copy(gamma.reshape(T,R*S))
            return new_gamma
    
    def compute_gamma(self, *args, **kwargs):
        """ Alias for backward compatibility. Use C{gamma_probabilities} """
        return self.gamma_probabilities(*args, **kwargs)
        
    
    ################## Storage ####################
    def to_picklable_dict(self):
        """ Produces a picklable representation of model as a dict. """
        from jazzparser.utils.nltk.storage import object_to_dict
        
        if self.backoff_model is not None:
            backoff_model = self.backoff_model.to_picklable_dict()
        else:
            backoff_model = None
        
        return {
            'order' : self.order, 
            'root_transition_counts' : object_to_dict(self.root_transition_counts),
            'schema_transition_counts' : object_to_dict(self.schema_transition_counts),
            'emission_counts' : object_to_dict(self.emission_counts),
            'estimator' : self._estimator,
            'backoff_model' : backoff_model,
            'chord_vocab' : self.chord_vocab,
            'schemata' : self.schemata, 
            'history' : self.history,
        }
        
    @classmethod
    def from_picklable_dict(cls, data):
        """
        Reproduces an model that was converted to a picklable 
        form using to_picklable_dict.
        
        """
        from jazzparser.utils.nltk.storage import dict_to_object
        
        if data['backoff_model'] is not None:
            backoff_model = cls.from_picklable_dict(data['backoff_model'])
        else:
            backoff_model = None
        
        return cls(data['order'],
                    dict_to_object(data['root_transition_counts']),
                    dict_to_object(data['schema_transition_counts']),
                    dict_to_object(data['emission_counts']),
                    data['estimator'],
                    backoff_model,
                    data['schemata'],
                    data['chord_vocab'],
                    history=data.get('history', ''))
    


def lattice_to_emissions(lattice, chord_map=None):
    """
    Gets an emission sequence in an appropriate format for the ngram-multi 
    HMM model from a chord lattice.
    
    @see: L{jazzparser.data.input.WeightedChordLabelInput}
    
    """
    emissions = []
    
    if chord_map is None:
        _map_chord = lambda c:c
    else:
        _map_chord = lambda c: chord_map[c]
    
    for timestep in lattice:
        time_emissions = []
        
        for (label, prob) in timestep:
            time_emissions.append((prob, (label.root, _map_chord(label.label))))
        
        emissions.append(time_emissions)
    return emissions
