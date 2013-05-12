"""Unsupervised EM training for chordclass HMM tagging model.

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

import numpy, os, signal
from numpy import ones, float64, sum as array_sum, zeros, log2, \
                        add as array_add, subtract as array_subtract
import cPickle as pickle
from multiprocessing import Pool

from jazzparser.utils.nltk.probability import mle_estimator, logprob, add_logs, \
                        sum_logs, prob_dist_to_dictionary_prob_dist, \
                        cond_prob_dist_to_dictionary_cond_prob_dist
from jazzparser.utils.options import ModuleOption
from jazzparser.utils.system import get_host_info_string
from jazzparser.utils.strings import str_to_bool
from jazzparser import settings
from jazzparser.taggers.segmidi.chordclass.hmm import ChordClassHmm
from jazzparser.taggers.segmidi.midi import midi_to_emission_stream

from nltk.probability import ConditionalProbDist, FreqDist, \
            ConditionalFreqDist, DictionaryProbDist, \
            DictionaryConditionalProbDist, MutableProbDist

# Small quantity added to every probability to ensure we never get zeros
ADD_SMALL = 1e-10

def _sequence_updates(sequence, last_model, label_dom, schema_ids, 
        emission_cond_ids, update_initial=True, catch_interrupt=False):
    """
    Evaluates the forward/backward probability matrices for a 
    single sequence under the model that came from the previous 
    iteration and returns matrices that contain the updates 
    to be made to the distributions during this iteration.
    
    This is wrapped up in a function so it can be run in 
    parallel for each sequence. Once all sequences have been 
    evaluated, the results are combined and model updated.
    
    @type update_initial: bool
    @param update_initial: usually you want to update all distributions, 
        including the initial state distribution. If update_initial=False, 
        the initial state distribution updates won't be made for this sequence. 
        We want this when the sequence is actually a non-initial fragment of 
        a longer sequence
    @type catch_interrupt: bool
    @param catch_interrupt: catch KeyboardInterrupt exceptions and return 
        None. This is useful behaviour when calling this in a process pool, 
        since it allows the parent process to handle the interrupt, but should 
        be set to False (default) if calling directly.
    
    """
    try:
        # Get the sizes we'll need for the matrix
        num_schemata = len(last_model.schemata)
        num_root_changes = 12
        num_chord_classes = len(last_model.chord_classes)
        num_emission_conds = len(emission_cond_ids)
        num_emissions = 12
        
        T = len(sequence)
        
        state_ids = dict([(state,id) for (id,state) in \
                                        enumerate(last_model.label_dom)])
        
        # Local versions of the matrices store the accumulated values 
        #  for just this sequence (so we can normalize before adding 
        #  to the global matrices)
        # The numerators
        schema_trans = zeros((num_schemata,num_schemata+1), float64)
        root_trans = zeros((num_schemata,num_schemata,num_root_changes), float64)
        ems = zeros((num_emission_conds,num_emissions), float64)
        sinit = zeros(num_schemata, float64)
        
        # Compute the forward and backward probabilities
        # These are normalized, but that makes no difference to the outcome of 
        #  compute_gamma and compute_xi
        alpha,scale,seq_logprob = last_model.normal_forward_probabilities(sequence, array=True)
        beta,scale = last_model.normal_backward_probabilities(sequence, array=True)
        # gamma contains the state occupation probability for each state at each 
        #  timestep
        gamma = last_model.compute_gamma(sequence, forward=alpha, backward=beta)
        # xi contains the probability of every state transition at every timestep
        xi = last_model.compute_xi(sequence, forward=alpha, backward=beta)
        
        # Update the initial state distribution if requested
        if update_initial:
            for state in label_dom:
                schema, root, chord_class = state
                schema_i = schema_ids[schema]
                # Add this contribution to the sum of the states with this schema
                sinit[schema_i] += gamma[0][state_ids[state]]
        
        for time in range(T):
            for state in label_dom:
                schema, root, chord_class = state
                schema_i = schema_ids[schema]
                state_i = state_ids[state]
                
                if time < T-1:
                    # Go through all possible pairs of states to update the 
                    #  transition distributions
                    for next_state in label_dom:
                        next_schema, next_root, next_chord_class = next_state
                        schema_j = schema_ids[next_schema]
                        state_j = state_ids[next_state]
                        
                        ## Transition dist update ##
                        root_change = (next_root - root) % 12
                        schema_trans[schema_i][schema_j] += \
                                                    xi[time][state_i][state_j]
                        root_trans[schema_i][schema_j][root_change] += \
                                                    xi[time][state_i][state_j]
                else:
                    # Final state: update the probs of transitioning to end
                    schema_trans[schema_i][num_schemata] += gamma[T-1][state_i]
                
                ## Emission dist update ##
                # Add the state occupation probability to the emission numerator 
                #  for every note
                for pc,beat in sequence[time]:
                    # Take the pitch class relative to the root
                    rel_pc = (pc - root) % 12
                    ems[emission_cond_ids[(chord_class,beat)]][rel_pc] += \
                                                gamma[time][state_i]
        
        # Calculate the denominators
        schema_trans_denom = array_sum(schema_trans, axis=1)
        root_trans_denom = array_sum(root_trans, axis=2)
        ems_denom = array_sum(ems, axis=1)
        # This should come to 1.0
        sinit_denom = array_sum(sinit)
                
        # Wrap this all up in a tuple to return to the master
        return (schema_trans, root_trans, ems, sinit, \
                schema_trans_denom, root_trans_denom, ems_denom, sinit_denom, \
                seq_logprob)
    except KeyboardInterrupt:
        if catch_interrupt:
            return
        else:
            raise
## End of pool operation _sequence_updates


class ChordClassBaumWelchTrainer(object):
    """
    Class with methods to retrain a chordclass model using the Baum-Welch 
    EM algorithm.
    
    Module options must be processed already - we do that in the 
    ChordClassTaggerModel, not here.
    
    @todo: Inherit from the 
    L{jazzparser.utils.nltk.ngram.baumwelch.BaumWelchTrainer}. Currently, 
    the generic trainer duplicates a lot of this code, since it was based on 
    it.
    
    """
    # These will be included in the training options
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
        ModuleOption('split', filter=int, 
            help_text="Limits the length of inputs by splitting them into "\
                "fragments of at most this length. The initial state "\
                "distribution will only be updated for the initial fragments.",
            usage="split=X, where X is an int"),
        ModuleOption('truncate', filter=int, 
            help_text="Limits the length of inputs by truncating them to this "\
                "number of timesteps. Truncation is applied before splitting.",
            usage="truncate=X, where X is an int"),
        ModuleOption('save_intermediate', filter=str_to_bool, 
            help_text="Save the model between iterations",
            usage="save_intermediate=B, where B is 'true' or 'false' "\
                "(default true)", 
            default=True),
        ModuleOption('trainprocs', filter=int, 
            help_text="Number of processes to spawn during training. Use -1 "\
                "to spawn a process for every sequence.",
            usage="trainprocs=P, where P is an integer", 
            default=1),
    ]
    
    def __init__(self, model, options={}):
        self.model = model
        self.options = options
    
    def train(self, emissions, logger=None, save_callback=None):
        """
        Performs unsupervised training using Baum-Welch EM.
        
        This is performed on a model that has already been initialized. 
        You might, for example, create such a model using 
        L{jazzparser.taggers.segmidi.chordclass.hmm.ChordClassHmm.initialize_chord_classes}.
        
        This is based on the training procedure in NLTK for HMMs:
        C{nltk.tag.hmm.HiddenMarkovModelTrainer.train_unsupervised}.
        
        @type emissions: L{jazzparser.data.input.MidiTaggerTrainingBulkInput} or 
            list of L{jazzparser.data.input.Input}s
        @param emissions: training MIDI data
        @type logger: logging.Logger
        @param logger: a logger to send progress logging to
        
        """
        if logger is None:
            from jazzparser.utils.loggers import create_dummy_logger
            logger = create_dummy_logger()
            
        self.model.add_history("Beginning Baum-Welch training on %s" % get_host_info_string())
        self.model.add_history("Training on %d MIDI sequences (with %s segments)" % \
            (len(emissions), ", ".join("%d" % len(seq) for seq in emissions)))
        logger.info("Beginning Baum-Welch training on %s" % get_host_info_string())
        
        # Get some options out of the module options
        max_iterations = self.options['max_iterations']
        convergence_logprob = self.options['convergence_logprob']
        split_length = self.options['split']
        truncate_length = self.options['truncate']
        save_intermediate = self.options['save_intermediate']
        processes = self.options['trainprocs']
        
        # Make a mutable distribution for each of the distributions 
        #  we'll be updating
        emission_mdist = cond_prob_dist_to_dictionary_cond_prob_dist(
                                    self.model.emission_dist, mutable=True)
        schema_trans_mdist = cond_prob_dist_to_dictionary_cond_prob_dist(
                                    self.model.schema_transition_dist, mutable=True)
        root_trans_mdist = cond_prob_dist_to_dictionary_cond_prob_dist(
                                    self.model.root_transition_dist, mutable=True)
        init_state_mdist = prob_dist_to_dictionary_prob_dist(
                                    self.model.initial_state_dist, mutable=True)
        
        # Get the sizes we'll need for the matrices
        num_schemata = len(self.model.schemata)
        num_root_changes = 12
        num_chord_classes = len(self.model.chord_classes)
        if self.model.metric:
            num_emission_conds = num_chord_classes * 4
        else:
            num_emission_conds = num_chord_classes
        num_emissions = 12
        
        # Enumerations to use for the matrices, so we know what they mean
        schema_ids = dict([(sch,i) for (i,sch) in enumerate(self.model.schemata+[None])])
        if self.model.metric:
            rs = range(4)
        else:
            rs = [0]
        emission_cond_ids = dict([(cc,i) for (i,cc) in enumerate(\
                sum([[
                    (str(cclass.name),r) for r in rs] for cclass in self.model.chord_classes], 
                []))])
        
        # Construct a model using these mutable distributions so we can 
        #  evaluate using them
        model = ChordClassHmm(schema_trans_mdist, 
                           root_trans_mdist, 
                           emission_mdist, 
                           self.model.emission_number_dist, 
                           init_state_mdist, 
                           self.model.schemata, 
                           self.model.chord_class_mapping,
                           self.model.chord_classes, 
                           metric=self.model.metric,
                           illegal_transitions=self.model.illegal_transitions,
                           fixed_root_transitions=self.model.fixed_root_transitions)
        
        def _save():
            if save_callback is None:
                logger.error("Could not save model, as no callback was given")
            else:
                # If the writing fails, wait till I've had a chance to sort it 
                #  out and then try again. This happens when my AFS token runs 
                #  out
                while True:
                    try:
                        save_callback()
                    except (IOError, OSError), err:
                        print "Error writing model to disk: %s. " % err
                        raw_input("Press <enter> to try again... ")
                    else:
                        break
        
        ########## Data preprocessing
        # Preprocess the inputs so they're ready for the model training
        emissions = [midi_to_emission_stream(seq, 
                                             metric=self.model.metric, 
                                             remove_empty=False)[0] \
                        for seq in emissions]
        logger.info("%d input sequences" % len(emissions))
        # Truncate long streams
        if truncate_length is not None:
            logger.info("Truncating sequences to max %d timesteps" % \
                                                            truncate_length)
            emissions = [stream[:truncate_length] for stream in emissions]
        # Split up long streams if requested
        # After this, each stream is a tuple (first,stream), where first 
        #  indicates whether the stream segment begins a song
        if split_length is not None:
            logger.info("Splitting sequences into max %d-sized chunks" % \
                                                                split_length)
            split_emissions = []
            # Split each stream
            for emstream in emissions:
                input_ems = emstream
                splits = []
                first = True
                # Take bits of length split_length until we're under the max
                while len(input_ems) >= split_length:
                    # Overlap the splits by one so we get all transitions
                    splits.append((first, input_ems[:split_length]))
                    input_ems = input_ems[split_length-1:]
                    first = False
                # Get the last short one
                if len(input_ems):
                    splits.append((first, input_ems))
                split_emissions.extend(splits)
        else:
            # All streams begin a song
            split_emissions = [(True,stream) for stream in emissions]
        logger.info("Sequence lengths after preprocessing: %s" % 
                " ".join([str(len(em[1])) for em in split_emissions]))
        ##########
        
        # Train the emission number distribution on this data to start with
        # This doesn't get updated by the iterative steps, because it's not 
        #  dependent on chord classes
        model.train_emission_number_distribution(emissions)
        logger.info("Trained emission number distribution")
        # Save the model with this
        if save_intermediate:
            _save()
        
        ###############
        # TODO: remove this section - it's for debugging
        if False:
            from jazzparser.prototype.baumwelch import TempBaumWelchTrainer
            temptrainer = TempBaumWelchTrainer(model, self.options)
            temptrainer.train(split_emissions, logger=logger)
            return
        ###############
        
        # Special case of -1 for number of sequences
        # No point in creating more processes than there are sequences
        if processes == -1 or processes > len(split_emissions):
            processes = len(split_emissions)
        
        iteration = 0
        last_logprob = None
        try:
            while iteration < max_iterations:
                logger.info("Beginning iteration %d" % iteration)
                current_logprob = 0.0
            
                ### Matrices in which to accumulate new probability estimates
                # trans contains new transition numerator probabilities
                # TODO: update this...
                # trans[s][s'][dr] = Sum_{t_n=t_(n+1), m_n=m_(n+1),c_n=c,c_(n+1)=c'} 
                #                  alpha(x_n).beta(x_(n+1)).
                #                   p(x_(n+1)|x_n).p(y_(n+1)|x_(n+1))
                schema_trans = zeros((num_schemata,num_schemata+1), float64)
                root_trans = zeros((num_schemata,num_schemata,num_root_changes), float64)
                # ems contains the new emission numerator probabilities
                # TODO: update this...
                # ems[r][d] = Sum_{d(y_n^k, x_n)=d, r_n^k=r}
                #                  alpha(x_n).beta(x_n) / 
                #                    Sum_{x'_n} (alpha(x'_n).beta(x'_n))
                ems = zeros((num_emission_conds,num_emissions), float64)
                # sinit contains the initial state numerator probabilities
                sinit = zeros(num_schemata, float64)
                # And these are the denominators
                schema_trans_denom = zeros(num_schemata, float64)
                root_trans_denom = zeros((num_schemata,num_schemata), float64)
                ems_denom = zeros(num_emission_conds, float64)
                # It may seem silly to use a matrix for this, but it allows 
                #  us to update it in the callback
                sinit_denom = zeros(1, float64)
                
                def _training_callback(result):
                    """
                    Callback for the _sequence_updates processes that takes 
                    the updates from a single sequence and adds them onto 
                    the global update accumulators.
                    
                    """
                    if result is None:
                        # Process cancelled: do no updates
                        logger.warning("Child process was cancelled")
                        return
                    # _sequence_updates() returns all of this as a tuple
                    (schema_trans_local, root_trans_local, ems_local, sinit_local, \
                     schema_trans_denom_local, root_trans_denom_local, \
                     ems_denom_local, sinit_denom_local, \
                     seq_logprob) = result
                    
                    # Add these probabilities from this sequence to the 
                    #  global matrices
                    # We don't need to scale these using the seq prob because 
                    #  they're already normalized
                    
                    # Emission numerator
                    array_add(ems, ems_local, ems)
                    # Transition numerator
                    array_add(schema_trans, schema_trans_local, schema_trans)
                    array_add(root_trans, root_trans_local, root_trans)
                    # Initial state numerator
                    array_add(sinit, sinit_local, sinit)
                    # Denominators
                    array_add(ems_denom, ems_denom_local, ems_denom)
                    array_add(schema_trans_denom, schema_trans_denom_local, schema_trans_denom)
                    array_add(root_trans_denom, root_trans_denom_local, root_trans_denom)
                    array_add(sinit_denom, sinit_denom_local, sinit_denom)
                ## End of _training_callback
                
                # Only use a process pool if there's more than one sequence
                if processes > 1:
                    # Create a process pool to use for training
                    logger.info("Creating a pool of %d processes" % processes)
                    #  catch them at this level
                    pool = Pool(processes=processes)
                    
                    async_results = []
                    try:
                        for seq_i,(first,sequence) in enumerate(split_emissions):
                            logger.info("Iteration %d, sequence %d" % (iteration, seq_i))
                            T = len(sequence)
                            if T == 0:
                                continue
                            
                            # Fire off a new call to the process pool for every sequence
                            async_results.append(
                                    pool.apply_async(_sequence_updates, 
                                                        (sequence, model, 
                                                            self.model.label_dom, 
                                                            schema_ids, 
                                                            emission_cond_ids), 
                                                        { 'update_initial' : first,
                                                          'catch_interrupt' : True },
                                                        callback=_training_callback) )
                        pool.close()
                        # Wait for all the workers to complete
                        pool.join()
                    except KeyboardInterrupt:
                        # If Ctl+C is fired during the processing, we exit here
                        logger.info("Keyboard interrupt was received during EM "\
                            "updates")
                        raise
                    
                    # Call get() on every AsyncResult so that any exceptions in 
                    #  workers get raised
                    for res in async_results:
                        # If there was an exception in _sequence_update, it 
                        #  will get raised here
                        res_tuple = res.get()
                        # Add this sequence's logprob into the total for all sequences
                        current_logprob += res_tuple[-1]
                else:
                    if len(split_emissions) == 1:
                        logger.info("One sequence: not using a process pool")
                    else:
                        logger.info("Not using a process pool: training %d "\
                            "emission sequences sequentially" % \
                            len(split_emissions))
                    
                    for seq_i,(first,sequence) in enumerate(split_emissions):
                        if len(sequence) > 0:
                            logger.info("Iteration %d, sequence %d" % (iteration, seq_i))
                            updates = _sequence_updates(
                                                sequence, model,
                                                self.model.label_dom,
                                                schema_ids, emission_cond_ids,
                                                update_initial=first)
                            _training_callback(updates)
                            # Update the overall logprob
                            current_logprob += updates[-1]
                
                
                ######## Model updates
                # Update the model's probabilities from the accumulated values
                
                # Emission distribution
                for cond_tup in model.emission_dist.conditions():
                    cond_id = emission_cond_ids[cond_tup]
                    # Divide each numerator by the denominator
                    denom = ems_denom[cond_id]
                    
                    for pc in range(12):
                        # Convert to log probs for update and divide by denom
                        prob = logprob(ems[cond_id][pc] + ADD_SMALL) - \
                                                logprob(denom + 12*ADD_SMALL)
                        model.emission_dist[cond_tup].update(pc, prob)
                
                # Transition distribution
                num_trans_samples = len(self.model.schemata)
                # Dist conditioned on current schema
                for schema in self.model.schemata:
                    schema_i = schema_ids[schema]
                    schema_denom = schema_trans_denom[schema_i]
                    
                    # Observe next schema and change of root
                    for next_schema in self.model.schemata:
                        schema_j = schema_ids[next_schema]
                        # Convert to log probs for update and divide by denom
                        prob = \
                            logprob(schema_trans[schema_i][schema_j] \
                                + ADD_SMALL) - \
                            logprob(schema_denom + (num_trans_samples+1)*ADD_SMALL)
                        model.schema_transition_dist[schema].update(
                                                next_schema, prob)
                        
                        root_denom = root_trans_denom[schema_i][schema_j]
                        
                        for root_change in range(12):
                            # Convert to log probs for update and divide by denom
                            prob = \
                                logprob(root_trans[schema_i][schema_j][root_change] \
                                    + ADD_SMALL) - \
                                logprob(root_denom + 12*ADD_SMALL)
                            model.root_transition_dist[(schema,next_schema)].update(
                                                    root_change, prob)
                    
                    # Also transition to the final state
                    prob = \
                        logprob(schema_trans[schema_i][num_schemata] \
                            + ADD_SMALL) - \
                        logprob(schema_denom + (num_trans_samples+1)*ADD_SMALL)
                    model.schema_transition_dist[schema].update(None, prob)
                
                # Initial state distribution
                denom = sinit_denom[0]
                num_samples = len(self.model.schemata)
                for schema in self.model.schemata:
                    schema_i = schema_ids[schema]
                    
                    # Convert to log probs for update and divide by denom
                    prob = \
                        logprob(sinit[schema_i] + ADD_SMALL) - \
                            logprob(denom + num_samples*ADD_SMALL)
                    model.initial_state_dist.update(schema, prob)
                
                # Clear the model's cache so we get the new probabilities
                model.clear_cache()
                
                logger.info("Training data log prob: %s" % current_logprob)
                if last_logprob is not None and current_logprob < last_logprob:
                    # Drop in log probability
                    # This should never happen if all's working correctly
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
                self.update_model(model)
                
                # Only save if we've been asked to save between iterations
                if save_intermediate:
                    _save()
        except KeyboardInterrupt:
            # Interrupted during training
            self.model.add_history("Baum-Welch training interrupted after %d "\
                                    "iterations" % iteration)
            logger.warn("Baum-Welch training interrupted")
            raise
        except Exception, err:
            # Some other error during training
            self.model.add_history("Error during Baum-Welch training. Exiting "\
                                    "after %d iterations" % iteration)
            logger.error("Error during training: %s" % err)
            raise
        
        self.model.add_history("Completed Baum-Welch training (%d iterations)" \
                                    % iteration)
        logger.info("Completed Baum-Welch training (%d iterations)" % iteration)
        # Update the distribution's parameters with those we've trained
        self.update_model(model)
        # Always save the model now that we're done
        _save()
        return
    
    def update_model(self, model):
        """
        Replaces the distributions of the saved model with those of the given 
        model and saves it.
        
        """
        # Replicate the distributions of the source model so that we get 
        #  non-mutable distributions to store
        self.model.schema_transition_dist = \
            cond_prob_dist_to_dictionary_cond_prob_dist(model.schema_transition_dist)
        self.model.root_transition_dist = \
            cond_prob_dist_to_dictionary_cond_prob_dist(model.root_transition_dist)
        self.model.emission_dist = \
            cond_prob_dist_to_dictionary_cond_prob_dist(model.emission_dist)
        self.model.initial_state_dist = prob_dist_to_dictionary_prob_dist(
                model.initial_state_dist)
