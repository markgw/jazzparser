"""Unsupervised EM training for Raphael and Stoddard's chord labelling model.

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


import numpy, os
from numpy import ones, float64, sum as array_sum, zeros, log2, add as array_add
import cPickle as pickle
from multiprocessing import Pool

from jazzparser.utils.nltk.probability import mle_estimator, logprob, add_logs, \
                        sum_logs, prob_dist_to_dictionary_prob_dist, \
                        cond_prob_dist_to_dictionary_cond_prob_dist
from jazzparser.utils.options import ModuleOption
from jazzparser.utils.system import get_host_info_string
from jazzparser import settings
from . import constants, RaphstoHmm, RaphstoHmmThreeChord, RaphstoHmmFourChord, \
                        RaphstoHmmUnigram, RaphstoHmmParameterError

from nltk.probability import ConditionalProbDist, FreqDist, \
            ConditionalFreqDist, DictionaryProbDist, \
            DictionaryConditionalProbDist, MutableProbDist

# Small quantity added to every probability to ensure we never get zeros
ADD_SMALL = 1e-6

def _sequence_updates(sequence, last_model, label_dom, state_ids, mode_ids, \
                        chord_ids, beat_ids, d_ids, d_func):
    """
    Evaluates the forward/backward probability matrices for a 
    single sequence under the model that came from the previous 
    iteration and returns matrices that contain the updates 
    to be made to the distributions during this iteration.
    
    This is wrapped up in a function so it can be run in 
    parallel for each sequence. Once all sequences have been 
    evaluated, the results are combined and model updated.
    
    """
    num_chords = len(chord_ids)
    num_beats = len(beat_ids)
    num_modes = len(mode_ids)
    num_ds = len(d_ids)
    num_ktrans = 12
    
    # Local versions of the matrices store the accumulated values 
    #  for just this sequence (so we can normalize before adding 
    #  to the global matrices)
    # The numerators
    ctrans_local = zeros((num_chords,num_chords), float64)
    ems_local = zeros((num_beats,num_ds), float64)
    ktrans_local = zeros((num_modes,num_ktrans,num_modes), float64)
    uni_chords_local = zeros(num_chords, float64)
    
    # Compute the forward and backward probabilities
    alpha,scale,seq_logprob = last_model.normal_forward_probabilities(sequence)
    beta,scale = last_model.normal_backward_probabilities(sequence)
    # gamma contains the state occupation probability for each state at each 
    #  timestep
    gamma = last_model.compute_gamma(sequence, alpha, beta)
    # xi contains the probability of every state transition at every timestep
    xi = last_model.compute_xi(sequence, alpha, beta)
    
    T = len(sequence)
    
    for time in range(T):
        for state in label_dom:
            tonic,mode,chord = state
            state_i = state_ids[state]
            mode_i = mode_ids[mode]
            
            if time < T-1:
                # Go through all possible pairs of states to update the 
                #  transition distributions
                for next_state in label_dom:
                    ntonic,nmode,nchord = next_state
                    state_j = state_ids[next_state]
                    mode_j = mode_ids[nmode]
                    
                    ## Key transition dist update ##
                    tonic_change = (ntonic - tonic) % 12
                    ktrans_local[mode_i][tonic_change][mode_j] += \
                                                    xi[time][state_i][state_j]
                    
                    ## Chord transition dist update ##
                    chord_i, chord_j = chord_ids[chord], chord_ids[nchord]
                    if tonic == ntonic and mode == nmode:
                        # Add to chord transition dist for this chord pair
                        ctrans_local[chord_i][chord_j] += xi[time][state_i][state_j]
                    else:
                        uni_chords_local[chord_j] += xi[time][state_i][state_j]
            
            ## Emission dist update ##
            # Add the state occupation probability to the emission numerator 
            #  for every note
            for pc,beat in sequence[time]:
                beat_i = beat_ids[beat]
                d = d_func(pc, state)
                d_i = d_ids[d]
                
                ems_local[beat_i][d_i] += gamma[time][state_i]
    
    # Calculate the denominators
    ctrans_denom_local = array_sum(ctrans_local, axis=1)
    ems_denom_local = array_sum(ems_local, axis=1)
    ktrans_denom_local = array_sum(array_sum(ktrans_local, axis=2), axis=1)
    uni_chords_denom_local = array_sum(uni_chords_local)
            
    # Wrap this all up in a tuple to return to the master
    return (ktrans_local, ctrans_local, ems_local, \
            uni_chords_local, \
            ktrans_denom_local, ctrans_denom_local, \
            ems_denom_local, uni_chords_denom_local, \
            seq_logprob)
## End of pool operation _sequence_updates


class RaphstoBaumWelchTrainer(object):
    """
    Class with methods to retrain a Raphsto model using the Baum-Welch 
    EM algorithm.
    
    """
    OPTIONS = [
        ModuleOption('max_iterations', filter=int, 
            help_text="Number of training iterations to give up after "\
                "if we don't reach convergence before.",
            usage="max_iterations=N, where N is an integer", default=100),
        ModuleOption('convergence_logprob', filter=float, 
            help_text="Difference in overall log probability of the "\
                "training data made by one iteration after which we "\
                "consider the training to have converged.",
            usage="convergence_logprob=X, where X is a small floating "\
                "point number (e.g. 1e-3)", default=1e-3),
    ]
    MODEL_TYPES = [
        RaphstoHmm,
        RaphstoHmmThreeChord,
        RaphstoHmmFourChord
    ]
    # Only models of these types may be trained with this trainer
    
    def __init__(self, model, options={}):
        self.model = model
        # Check this model is of one of the types we can train
        if type(model) not in self.MODEL_TYPES:
            raise RaphstoHmmParameterError, "trainer %s cannot train a model "\
                "of type %s" % (type(self).__name__, type(model).__name__)
        
        self.options = ModuleOption.process_option_dict(options, self.OPTIONS)
        self.model_cls = type(model)
    
    def train(self, emissions, max_iterations=None, \
                    convergence_logprob=None, logger=None, processes=1,
                    save=True, save_intermediate=False):
        """
        Performs unsupervised training using Baum-Welch EM.
        
        This is an instance method, because it is performed on a model 
        that has already been initialized. You might, for example, 
        create such a model using C{initialize_chord_types}.
        
        This is based on the training procedure in NLTK for HMMs:
        C{nltk.tag.hmm.HiddenMarkovModelTrainer.train_unsupervised}.
        
        @type emissions: list of lists of emissions
        @param emissions: training data. Each element is a list of 
            emissions representing a sequence in the training data.
            Each emission is an emission like those used for 
            L{jazzparser.misc.raphsto.RaphstoHmm.emission_log_probability}, 
            i.e. a list of note 
            observations
        @type max_iterations: int
        @param max_iterations: maximum number of iterations to allow 
            for EM (default 100). Overrides the corresponding 
            module option
        @type convergence_logprob: float
        @param convergence_logprob: maximum change in log probability 
            to consider convergence to have been reached (default 1e-3). 
            Overrides the corresponding module option
        @type logger: logging.Logger
        @param logger: a logger to send progress logging to
        @type processes: int
        @param processes: number processes to spawn. A pool of this 
            many processes will be used to compute distribution updates 
            for sequences in parallel during each iteration.
        @type save: bool
        @param save: save the model at the end of training
        @type save_intermediate: bool
        @param save_intermediate: save the model after each iteration. Implies 
            C{save}
        
        """
        from . import raphsto_d
        if logger is None:
            from jazzparser.utils.loggers import create_dummy_logger
            logger = create_dummy_logger()
        
        if save_intermediate:
            save = True
            
        # No point in creating more processes than there are sequences
        if processes > len(emissions):
            processes = len(emissions)
        
        self.model.add_history("Beginning Baum-Welch training on %s" % get_host_info_string())
        self.model.add_history("Training on %d sequences (with %s chords)" % \
            (len(emissions), ", ".join("%d" % len(seq) for seq in emissions)))
        
        # Use kwargs if given, otherwise module options
        if max_iterations is None:
            max_iterations = self.options['max_iterations']
        if convergence_logprob is None:
            convergence_logprob = self.options['convergence_logprob']
        
        # Enumerate the chords
        chord_ids = dict((crd,num) for (num,crd) in \
                                    enumerate(self.model.chord_transition_dom))
        num_chords = len(chord_ids)
        # Enumerate the states
        state_ids = dict((state,num) for (num,state) in \
                                    enumerate(self.model.label_dom))
        
        # Enumerate the beat values (they're probably consecutive ints, but 
        #  let's not rely on it)
        beat_ids = dict((beat,num) for (num,beat) in \
                                    enumerate(self.model.beat_dom))
        num_beats = len(beat_ids)
        # Enumerate the d-values (d-function's domain)
        d_ids = dict((d,num) for (num,d) in \
                                    enumerate(self.model.emission_dist_dom))
        num_ds = len(d_ids)
        
        # Enumerate the modes
        mode_ids = dict((m,num) for (num,m) in enumerate(constants.MODES))
        num_modes = len(mode_ids)
        # The number of key transitions is always 12
        num_ktrans = 12
        
        # Make a mutable distribution for each of the distributions 
        #  we'll be updating
        emission_mdist = DictionaryConditionalProbDist(
                    dict((s, MutableProbDist(self.model.emission_dist[s], 
                                             self.model.emission_dist_dom))
                        for s in self.model.emission_dist.conditions()))
        key_mdist = DictionaryConditionalProbDist(
                    dict((s, MutableProbDist(self.model.key_transition_dist[s], 
                                             self.model.key_transition_dom))
                        for s in self.model.key_transition_dist.conditions()))
        chord_mdist = DictionaryConditionalProbDist(
                dict((s, MutableProbDist(self.model.chord_transition_dist[s], 
                                         self.model.chord_transition_dom))
                    for s in self.model.chord_transition_dist.conditions()))
        chord_uni_mdist = MutableProbDist(self.model.chord_dist, 
                                          self.model.chord_transition_dom)
        
        # Construct a model using these mutable distributions so we can 
        #  evaluate using them
        model = self.model_cls(key_mdist, 
                           chord_mdist, 
                           emission_mdist, 
                           chord_uni_mdist, 
                           chord_set=self.model.chord_set)
        
        iteration = 0
        last_logprob = None
        while iteration < max_iterations:
            logger.info("Beginning iteration %d" % iteration)
            current_logprob = 0.0
        
            ### Matrices in which to accumulate new probability estimates
            # ctrans contains new chord transition numerator probabilities
            # ctrans[c][c'] = Sum_{t_n=t_(n+1), m_n=m_(n+1),c_n=c,c_(n+1)=c'} 
            #                  alpha(x_n).beta(x_(n+1)).
            #                   p(x_(n+1)|x_n).p(y_(n+1)|x_(n+1))
            ctrans = zeros((num_chords,num_chords), float64)
            # ems contains the new emission numerator probabilities
            # ems[r][d] = Sum_{d(y_n^k, x_n)=d, r_n^k=r}
            #                  alpha(x_n).beta(x_n) / 
            #                    Sum_{x'_n} (alpha(x'_n).beta(x'_n))
            ems = zeros((num_beats,num_ds), float64)
            # ktrans contains new key transition numerator probabilities
            # ktrans[m][dt][m'] = Sum_{t_(n+1)-t_n=dt,m_(n+1)=m',m_n=m}
            #                  alpha(x_n).beta(x_(n+1)).
            #                  p(x_(n+1)|x_n).p(y_(n+1)|x_(n+1))
            ktrans = zeros((num_modes,num_ktrans,num_modes), float64)
            # uni_chords contains the new chord numerator probabilities (q_c^1, 
            #  the one not conditioned on the previous chord)
            uni_chords = zeros(num_chords, float64)
            # And these are the denominators
            ctrans_denom = zeros(num_chords, float64)
            ems_denom = zeros(num_beats, float64)
            ktrans_denom = zeros(num_modes, float64)
            # It may seem silly to use a matrix for this, but it allows 
            #  us to update it in the callback
            uni_chords_denom = zeros(1, float64)
            
            def _training_callback(result):
                """
                Callback for the _sequence_updates processes that takes 
                the updates from a single sequence and adds them onto 
                the global update accumulators.
                
                """
                # _sequence_updates() returns all of this as a tuple
                (ktrans_local, ctrans_local, ems_local, uni_chords_local, \
                 ktrans_denom_local, ctrans_denom_local, ems_denom_local, \
                 uni_chords_denom_local, \
                 seq_logprob) = result
                
                # Add these probabilities from this sequence to the 
                #  global matrices
                # Emission numerator
                array_add(ems, ems_local, ems)
                # Key transition numerator
                array_add(ktrans, ktrans_local, ktrans)
                # Chord transition numerator
                array_add(ctrans, ctrans_local, ctrans)
                # Unconditioned chord numerator
                array_add(uni_chords, uni_chords_local, uni_chords)
                # Denominators
                array_add(ems_denom, ems_denom_local, ems_denom)
                array_add(ktrans_denom, ktrans_denom_local, ktrans_denom)
                array_add(ctrans_denom, ctrans_denom_local, ctrans_denom)
                array_add(uni_chords_denom, uni_chords_denom_local, uni_chords_denom)
            ## End of _training_callback
            
            
            # Only use a process pool if there's more than one sequence
            if processes > 1:
                # Create a process pool to use for training
                logger.info("Creating a pool of %d processes" % processes)
                pool = Pool(processes=processes)
                
                async_results = []
                for seq_i,sequence in enumerate(emissions):
                    logger.info("Iteration %d, sequence %d" % (iteration, seq_i))
                    T = len(sequence)
                    if T == 0:
                        continue
                    
                    # Fire off a new call to the process pool for every sequence
                    async_results.append(
                            pool.apply_async(_sequence_updates, 
                                                (sequence, model, 
                                                    self.model.label_dom, 
                                                    state_ids, mode_ids, chord_ids, 
                                                    beat_ids, d_ids, raphsto_d), 
                                                callback=_training_callback) )
                pool.close()
                # Wait for all the workers to complete
                pool.join()
                
                # Call get() on every AsyncResult so that any exceptions in 
                #  workers get raised
                for res in async_results:
                    # If there was an exception in _sequence_update, it 
                    #  will get raised here
                    res_tuple = res.get()
                    # Add this sequence's logprob into the total for all sequences
                    current_logprob += res_tuple[8]
            else:
                logger.info("One sequence: not using a process pool")
                sequence = emissions[0]
                
                if len(sequence) > 0:
                    updates = _sequence_updates(
                                        sequence, model,
                                        self.model.label_dom,
                                        state_ids, mode_ids, chord_ids, 
                                        beat_ids, d_ids, raphsto_d)
                    _training_callback(updates)
                    # Update the overall logprob
                    current_logprob = updates[8]
            
            # Update the model's probabilities from the accumulated values
            for beat in self.model.beat_dom:
                denom = ems_denom[beat_ids[beat]]
                for d in self.model.emission_dist_dom:
                    if denom == 0.0:
                        # Zero denominator
                        prob = - logprob(len(d_ids))
                    else:
                        prob = logprob(ems[beat_ids[beat]][d_ids[d]] + ADD_SMALL) - logprob(denom + len(d_ids)*ADD_SMALL)
                    model.emission_dist[beat].update(d, prob)
            
            for mode0 in mode_ids.keys():
                mode_i = mode_ids[mode0]
                denom = ktrans_denom[mode_ids[mode0]]
                for key in range(num_ktrans):
                    for mode1 in mode_ids.keys():
                        mode_j = mode_ids[mode1]
                        if denom == 0.0:
                            # Zero denominator: use a uniform distribution
                            prob = - logprob(num_ktrans*num_modes)
                        else:
                            prob = logprob(ktrans[mode_i][key][mode_j] + ADD_SMALL) - logprob(denom + num_ktrans*num_modes*ADD_SMALL)
                        model.key_transition_dist[mode0].update(
                                (key,mode1), prob)
            
            for chord0 in chord_ids.keys():
                chord_i = chord_ids[chord0]
                denom = ctrans_denom[chord_i]
                for chord1 in chord_ids.keys():
                    chord_j = chord_ids[chord1]
                    if denom == 0.0:
                        # Zero denominator: use a uniform distribution
                        prob = - logprob(num_chords)
                    else:
                        prob = logprob(ctrans[chord_i][chord_j] + ADD_SMALL) - logprob(denom + num_chords*ADD_SMALL)
                    model.chord_transition_dist[chord0].update(chord1, prob)
            for chord in chord_ids.keys():
                prob = logprob(uni_chords[chord_ids[chord]] + ADD_SMALL) - logprob(uni_chords_denom[0] + len(chord_ids)*ADD_SMALL)
                model.chord_dist.update(chord, prob)
            
            # Clear the model's cache so we get the new probabilities
            model.clear_cache()
            
            logger.info("Training data log prob: %s" % current_logprob)
            if last_logprob is not None and current_logprob < last_logprob:
                logger.error("Log probability dropped by %s" % \
                                (last_logprob - current_logprob))
            if last_logprob is not None:
                logger.info("Log prob change: %s" % \
                                (current_logprob - last_logprob))
            # Check whether the log probability has converged
            if iteration > 0 and \
                    abs(current_logprob - last_logprob) < convergence_logprob:
                # Don't iterate any more
                logger.info("Distribution has converged: ceasing training")
                break
            
            iteration += 1
            last_logprob = current_logprob
            
            # Update the main model
            # Only save if we've been asked to save between iterations
            self.update_model(model, save=save_intermediate)
        
        self.model.add_history("Completed Baum-Welch training")
        # Update the distribution's parameters with those we've trained
        self.update_model(model, save=save)
        return
    
    def update_model(self, model, save=True):
        """
        Replaces the distributions of the saved model with those of the given 
        model and saves it.
        
        @type save: bool
        @param save: save the model. Otherwise just updates the distributions.
        
        """
        self.model.key_transition_dist = \
            cond_prob_dist_to_dictionary_cond_prob_dist(
                model.key_transition_dist)
        self.model.chord_transition_dist = \
            cond_prob_dist_to_dictionary_cond_prob_dist(
                model.chord_transition_dist)
        self.model.emission_dist = \
            cond_prob_dist_to_dictionary_cond_prob_dist(model.emission_dist)
        self.model.chord_dist = prob_dist_to_dictionary_prob_dist(
                model.chord_dist)
        if save:
            self.model.save()


########################## Unigram model ############################

def _sequence_updates_uni(sequence, last_model, label_dom, state_ids, \
            beat_ids, d_ids, d_func):
    """Same as L{_sequence_updates}, modified for unigram models. """
    num_beats = len(beat_ids)
    num_ds = len(d_ids)
    num_ktrans = 12
    
    # Local versions of the matrices store the accumulated values 
    #  for just this sequence (so we can normalize before adding 
    #  to the global matrices)
    # The numerators
    ems_local = zeros((num_beats,num_ds), float64)
    
    # Compute the forward and backward probabilities
    alpha,scale,seq_logprob = last_model.normal_forward_probabilities(sequence)
    beta,scale = last_model.normal_backward_probabilities(sequence)
    # gamma contains the state occupation probability for each state at each 
    #  timestep
    gamma = last_model.compute_gamma(sequence, alpha, beta)
    # xi contains the probability of every state transition at every timestep
    xi = last_model.compute_xi(sequence, alpha, beta)
    
    T = len(sequence)
    
    for time in range(T):
        for state in label_dom:
            tonic,mode,chord = state
            state_i = state_ids[state]
            # We don't update the transition distribution here, because it's fixed
            
            ## Emission dist update ##
            # Add the state occupation probability to the emission numerator 
            #  for every note
            for pc,beat in sequence[time]:
                beat_i = beat_ids[beat]
                d = d_func(pc, state)
                d_i = d_ids[d]
                
                ems_local[beat_i][d_i] += gamma[time][state_i]
    
    # Calculate the denominators
    ems_denom_local = array_sum(ems_local, axis=1)
            
    # Wrap this all up in a tuple to return to the master
    return (ems_local, ems_denom_local, seq_logprob)
## End of pool operation _sequence_updates_uni

class RaphstoBaumWelchUnigramTrainer(RaphstoBaumWelchTrainer):
    """
    Class with methods to retrain a Raphsto model using the Baum-Welch 
    EM algorithm.
    Special trainer to train unigram models. That is, it doesn't update 
    the transition distribution.
    
    """
    MODEL_TYPES = [
        RaphstoHmmUnigram,
    ]
    # Model types which may be trained by this trainer: override the superclass'
    
    def train(self, emissions, max_iterations=None, \
                    convergence_logprob=None, logger=None, processes=1,
                    save=True, save_intermediate=False):
        """
        Performs unsupervised training using Baum-Welch EM.
        
        This is an instance method, because it is performed on a model 
        that has already been initialized. You might, for example, 
        create such a model using C{initialize_chord_types}.
        
        This is based on the training procedure in NLTK for HMMs:
        C{nltk.tag.hmm.HiddenMarkovModelTrainer.train_unsupervised}.
        
        @type emissions: list of lists of emissions
        @param emissions: training data. Each element is a list of 
            emissions representing a sequence in the training data.
            Each emission is an emission like those used for 
            L{jazzparser.misc.raphsto.RaphstoHmm.emission_log_probability}, 
            i.e. a list of note 
            observations
        @type max_iterations: int
        @param max_iterations: maximum number of iterations to allow 
            for EM (default 100). Overrides the corresponding 
            module option
        @type convergence_logprob: float
        @param convergence_logprob: maximum change in log probability 
            to consider convergence to have been reached (default 1e-3). 
            Overrides the corresponding module option
        @type logger: logging.Logger
        @param logger: a logger to send progress logging to
        @type processes: int
        @param processes: number processes to spawn. A pool of this 
            many processes will be used to compute distribution updates 
            for sequences in parallel during each iteration.
        @type save: bool
        @param save: save the model at the end of training
        @type save_intermediate: bool
        @param save_intermediate: save the model after each iteration. Implies 
            C{save}
        
        """
        from . import raphsto_d
        if logger is None:
            from jazzparser.utils.loggers import create_dummy_logger
            logger = create_dummy_logger()
        
        if save_intermediate:
            save = True
            
        # No point in creating more processes than there are sequences
        if processes > len(emissions):
            processes = len(emissions)
        
        self.model.add_history("Beginning Baum-Welch unigram training on %s" % get_host_info_string())
        self.model.add_history("Training on %d sequences (with %s chords)" % \
            (len(emissions), ", ".join("%d" % len(seq) for seq in emissions)))
        
        # Use kwargs if given, otherwise module options
        if max_iterations is None:
            max_iterations = self.options['max_iterations']
        if convergence_logprob is None:
            convergence_logprob = self.options['convergence_logprob']
        
        # Enumerate the states
        state_ids = dict((state,num) for (num,state) in \
                                    enumerate(self.model.label_dom))
        
        # Enumerate the beat values (they're probably consecutive ints, but 
        #  let's not rely on it)
        beat_ids = dict((beat,num) for (num,beat) in \
                                    enumerate(self.model.beat_dom))
        num_beats = len(beat_ids)
        # Enumerate the d-values (d-function's domain)
        d_ids = dict((d,num) for (num,d) in \
                                    enumerate(self.model.emission_dist_dom))
        num_ds = len(d_ids)
        
        # Make a mutable distribution for the emission distribution we'll 
        #  be updating
        emission_mdist = DictionaryConditionalProbDist(
                    dict((s, MutableProbDist(self.model.emission_dist[s], 
                                             self.model.emission_dist_dom))
                        for s in self.model.emission_dist.conditions()))
        # Create dummy distributions to fill the places of the transition 
        #  distribution components
        key_mdist = DictionaryConditionalProbDist({})
        chord_mdist = DictionaryConditionalProbDist({})
        chord_uni_mdist = MutableProbDist({}, [])
        
        # Construct a model using these mutable distributions so we can 
        #  evaluate using them
        model = self.model_cls(key_mdist, 
                               chord_mdist,
                               emission_mdist, 
                               chord_uni_mdist,
                               chord_set=self.model.chord_set)
        
        iteration = 0
        last_logprob = None
        while iteration < max_iterations:
            logger.info("Beginning iteration %d" % iteration)
            current_logprob = 0.0
            
            # ems contains the new emission numerator probabilities
            # ems[r][d] = Sum_{d(y_n^k, x_n)=d, r_n^k=r}
            #                  alpha(x_n).beta(x_n) / 
            #                    Sum_{x'_n} (alpha(x'_n).beta(x'_n))
            ems = zeros((num_beats,num_ds), float64)
            # And these are the denominators
            ems_denom = zeros(num_beats, float64)
            
            def _training_callback(result):
                """
                Callback for the _sequence_updates processes that takes 
                the updates from a single sequence and adds them onto 
                the global update accumulators.
                
                """
                # _sequence_updates() returns all of this as a tuple
                (ems_local, ems_denom_local, seq_logprob) = result
                
                # Add these probabilities from this sequence to the 
                #  global matrices
                # Emission numerator
                array_add(ems, ems_local, ems)
                # Denominators
                array_add(ems_denom, ems_denom_local, ems_denom)
            ## End of _training_callback
            
            
            # Only use a process pool if there's more than one sequence
            if processes > 1:
                # Create a process pool to use for training
                logger.info("Creating a pool of %d processes" % processes)
                pool = Pool(processes=processes)
                
                async_results = []
                for seq_i,sequence in enumerate(emissions):
                    logger.info("Iteration %d, sequence %d" % (iteration, seq_i))
                    T = len(sequence)
                    if T == 0:
                        continue
                    
                    # Fire off a new call to the process pool for every sequence
                    async_results.append(
                            pool.apply_async(_sequence_updates_uni, 
                                                (sequence, model, 
                                                    self.model.label_dom, 
                                                    state_ids, 
                                                    beat_ids, d_ids, raphsto_d), 
                                                callback=_training_callback) )
                pool.close()
                # Wait for all the workers to complete
                pool.join()
                
                # Call get() on every AsyncResult so that any exceptions in 
                #  workers get raised
                for res in async_results:
                    # If there was an exception in _sequence_update, it 
                    #  will get raised here
                    res_tuple = res.get()
                    # Add this sequence's logprob into the total for all sequences
                    current_logprob += res_tuple[2]
            else:
                logger.info("One sequence: not using a process pool")
                sequence = emissions[0]
                
                if len(sequence) > 0:
                    updates = _sequence_updates_uni(
                                        sequence, model,
                                        self.model.label_dom,
                                        state_ids, 
                                        beat_ids, d_ids, raphsto_d)
                    _training_callback(updates)
                    # Update the overall logprob
                    current_logprob = updates[2]
            
            # Update the model's probabilities from the accumulated values
            for beat in self.model.beat_dom:
                denom = ems_denom[beat_ids[beat]]
                for d in self.model.emission_dist_dom:
                    if denom == 0.0:
                        # Zero denominator
                        prob = - logprob(len(d_ids))
                    else:
                        prob = logprob(ems[beat_ids[beat]][d_ids[d]] + ADD_SMALL) - logprob(denom + len(d_ids)*ADD_SMALL)
                    model.emission_dist[beat].update(d, prob)
            
            # Clear the model's cache so we get the new probabilities
            model.clear_cache()
            
            logger.info("Training data log prob: %s" % current_logprob)
            if last_logprob is not None and current_logprob < last_logprob:
                logger.error("Log probability dropped by %s" % \
                                (last_logprob - current_logprob))
            if last_logprob is not None:
                logger.info("Log prob change: %s" % \
                                (current_logprob - last_logprob))
            # Check whether the log probability has converged
            if iteration > 0 and \
                    abs(current_logprob - last_logprob) < convergence_logprob:
                # Don't iterate any more
                logger.info("Distribution has converged: ceasing training")
                break
            
            iteration += 1
            last_logprob = current_logprob
            
            # Update the main model
            # Only save if we've been asked to save between iterations
            self.update_model(model, save=save_intermediate)
        
        self.model.add_history("Completed Baum-Welch unigram training")
        # Update the distribution's parameters with those we've trained
        self.update_model(model, save=save)
        return
    
    def update_model(self, model, save=True):
        """
        Replaces the distributions of the saved model with those of the given 
        model and saves it.
        
        @type save: bool
        @param save: save the model. Otherwise just updates the distributions.
        
        """
        self.model.emission_dist = \
            cond_prob_dist_to_dictionary_cond_prob_dist(model.emission_dist)
        if save:
            self.model.save()
    
