"""Unsupervised EM training for HMMs that use 
L{jazzparser.utils.nltk.ngram.NgramModel} as their base implementation.
This is a generic implementation of the Baum-Welch algorithm for EM training 
of HMMs. C{BaumWelchTrainer} should be subclassed to override anything that 
needs to be customized for the model type.

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
from numpy import float64, sum as array_sum, zeros, log2, add as array_add
from multiprocessing import Pool

from jazzparser.utils.nltk.probability import logprob
from jazzparser.utils.nltk.ngram import NgramModel, DictionaryHmmModel
from jazzparser.utils.options import ModuleOption
from jazzparser.utils.system import get_host_info_string
from jazzparser.utils.strings import str_to_bool
from jazzparser import settings

# Small quantity added to every probability to ensure we never get zeros
ADD_SMALL = 1e-6

def sequence_updates(sequence, last_model, empty_arrays, array_ids, update_initial=True):
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
    
    """
    try:
        trans, ems, trans_denom, ems_denom = empty_arrays
        state_ids, em_ids = array_ids
        
        # Compute the forwards with seq_prob=True
        fwds,seq_logprob = last_model.normal_forward_probabilities(sequence, seq_prob=True)
        # gamma contains the state occupation probability for each state at each 
        #  timestep
        gamma = last_model.gamma_probabilities(sequence, forward=fwds)
        # xi contains the probability of every state transition at every timestep
        xi = last_model.compute_xi(sequence)
        
        label_dom = last_model.label_dom
        T = len(sequence)
        
        for time in range(T):
            for state in label_dom:
                state_i = state_ids[state]
                
                if time < T-1:
                    # Go through all possible pairs of states to update the 
                    #  transition distributions
                    for next_state in label_dom:
                        state_j = state_ids[next_state]
                        
                        ## Transition dist update ##
                        trans[state_i][state_j] += xi[time][state_i][state_j]
                
                ## Emission dist update ##
                ems[state_ids[state]][em_ids[sequence[time]]] += \
                                                    gamma[time][state_i]
        
        # Calculate the denominators by summing
        trans_denom = array_sum(trans, axis=1)
        ems_denom = array_sum(ems, axis=1)
                
        # Wrap this all up in a tuple to return to the master
        return (trans, ems, trans_denom, ems_denom, seq_logprob)
    except KeyboardInterrupt:
        return


class BaumWelchTrainer(object):
    """
    Class with methods to retrain an HMM using the Baum-Welch EM algorithm.
    
    Note that although the default implementation is for a plain 
    L{jazzparser.utils.nltk.ngram.NgramModel}, Baum-Welch training only makes 
    sense if the model is an HMM. It will therefore complain if the order is 
    not 2 and if there's a backoff model.
    
    Module options must be processed externally. This allows them to be 
    combined with other options as appropriate. The options defined here 
    are a standard set of options for generic training and should be processed 
    before the trainer is instantiated.
    
    This is designed as a generic implementation of the algorithm. To use it 
    for a special kind of model (e.g. one with a non-standard transition 
    distribution), you need to override certain methods to make them 
    appropriate to the model:
        - C{create_mutable_model}
        - C{update_model}
        - C{sequence_updates}
        - C{get_empty_arrays}
        - C{sequence_updates_callback}
        - C{get_array_indices}
    
    The generic version of the trainer can be used to train a 
    DictionaryHmmModel. Subclasses are used to train other model types.
    
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
        
        # Do some checks on the model to make sure it's suitable for training
        if not isinstance(model, NgramModel):
            raise BaumWelchTrainingError, "BaumWelchTrainer can only be used "\
                "to train an instance of a subclass of NgramModel, not %s" % \
                type(model).__name__
        if model.order != 2:
            raise BaumWelchTrainingError, "can only train a bigram model with "\
                "Baum-Welch. Got model of order %d" % model.order
        if model.backoff_model is not None:
            raise BaumWelchTrainingError, "model to be retrained has a backoff "\
                "model, but we can't train that using Baum-Welch"
        
    @classmethod
    def process_option_dict(cls, options):
        """
        Verifies and processes the training option values. Returns the 
        processed dict.
        
        """
        return ModuleOption.process_option_dict(options, cls.OPTIONS)
    
    def record_history(self, line):
        """
        Stores a line in the history of the model or wherever else it is 
        appropriate to keep a record of training steps.
        
        Default implementation does nothing, but subclasses may want to 
        store this information.
        
        """
        return
    
    sequence_updates = staticmethod(sequence_updates)
    """
    This should be overridden by subclasses, but not by defining a static 
    method on the class, since the function must be picklable. For this, it 
    needs to be a top-level function. Then you can set the sequence_updates 
    attribute to point to it (using staticmethod), as we have done in the 
    default implementation.
    
    """
    
    def create_mutable_model(self, model):
        """
        Creates a mutable version of the given model. This mutable version 
        will be the model that receives updates during training, as defined 
        by L{update_model}.
        
        """
        return DictionaryHmmModel.from_ngram_model(model, mutable=True)
    
    def get_empty_arrays(self):
        """
        Creates empty arrays to hold the accumulated probabilities during 
        training. The sizes will depend on self.model.
        
        """
        num_states = len(self.model.label_dom)
        trans = zeros((num_states, num_states), float64)
        trans_denom = zeros((num_states, ), float64)
        
        num_ems = len(self.model.emission_dom)
        ems = zeros((num_states, num_ems), float64)
        ems_denom = zeros((num_states, ), float64)
        return (trans, ems, trans_denom, ems_denom)
    
    def get_array_indices(self):
        """
        Returns a tuple of the dicts that map labels, emissions, etc to the 
        indices of arrays to which they correspond. These will need to be 
        different for non-standard models.
        
        """
        state_ids = dict([(state,id) for (id,state) in \
                                        enumerate(self.model.label_dom)])
        em_ids = dict([(em,id) for (id,em) in \
                                    enumerate(self.model.emission_dom)])
        return (state_ids, em_ids)
    
    def sequence_updates_callback(self, result):
        """
        Callback for the sequence_updates processes that takes 
        the updates from a single sequence and adds them onto 
        the global update accumulators.
        
        The accumulators are stored as self.global_arrays.
        
        """
        if result is None:
            # Process cancelled: do no updates
            logger.warning("Child process was cancelled")
            return
        
        # sequence_updates() returns all of this as a tuple
        (trans_local, ems_local, \
         trans_denom_local, ems_denom_local, \
         seq_logprob) = result
        # Get the global arrays that we're updating
        (trans, ems, 
         trans_denom, ems_denom) = self.global_arrays
        
        # Add these probabilities from this sequence to the 
        #  global matrices
        # Emission numerator
        array_add(ems, ems_local, ems)
        # Transition numerator
        array_add(trans, trans_local, trans)
        # Denominators
        array_add(ems_denom, ems_denom_local, ems_denom)
        array_add(trans_denom, trans_denom_local, trans_denom)
    
    def update_model(self, arrays, array_ids):
        """
        Replaces the distributions of the saved model with the probabilities 
        taken from the arrays of updates. self.model is expected to be 
        made up of mutable distributions when this is called.
        
        """
        trans, ems, trans_denom, ems_denom = arrays
        state_ids, em_ids = array_ids
        num_states = len(self.model.label_dom)
        num_emissions = len(self.model.emission_dom)
        
        for state in self.model.label_dom:
            # Get the transition denominator for going from this state
            state_i = state_ids[state]
            denom = trans_denom[state_i]
            
            for next_state in self.model.label_dom:
                state_j = state_ids[next_state]
                # Update the probability of this transition
                prob = logprob(trans[state_i][state_j] + ADD_SMALL) - \
                        logprob(trans_denom[state_i] + num_states*ADD_SMALL)
                self.model.label_dist[(state,)].update(next_state, prob)
            
            for emission in self.model.emission_dom:
                # Update the probability of this emission
                prob = logprob(ems[state_i][em_ids[emission]] + ADD_SMALL) - \
                        logprob(ems_denom[state_i] + num_emissions*ADD_SMALL)
                self.model.emission_dist[state].update(emission, prob)
    
    def save(self):
        """
        Saves the model in self.model to disk. This may be called at the end 
        of each iteration and will be called at the end of the whole training 
        process.
        
        By default, does nothing. You don't have to put something in here, 
        but you'll need to override this if you want the model to be saved 
        during training before it gets return at the end.
        
        """
        return
    
    def train(self, emissions, logger=None):
        """
        Performs unsupervised training using Baum-Welch EM.
        
        This is performed as a retraining step on a model that has already 
        been initialized. 
        
        This is based on the training procedure in NLTK for HMMs:
        C{nltk.tag.hmm.HiddenMarkovModelTrainer.train_unsupervised}.
        
        @type emissions: list of lists of emissions
        @param emissions: training data. Each element is a list of 
            emissions representing a sequence in the training data.
            Each emission is an emission like those used for 
            C{emission_log_probability} on the model
        @type logger: logging.Logger
        @param logger: a logger to send progress logging to
        
        """
        if logger is None:
            from jazzparser.utils.loggers import create_dummy_logger
            logger = create_dummy_logger()
            
        self.record_history("Beginning Baum-Welch training on %s" % get_host_info_string())
        self.record_history("Training on %d inputs (with %s segments)" % \
            (len(emissions), ", ".join("%d" % len(seq) for seq in emissions)))
        logger.info("Beginning Baum-Welch training on %s" % get_host_info_string())
        
        # Get some options out of the module options
        max_iterations = self.options['max_iterations']
        convergence_logprob = self.options['convergence_logprob']
        split_length = self.options['split']
        truncate_length = self.options['truncate']
        save_intermediate = self.options['save_intermediate']
        processes = self.options['trainprocs']
        
        # Make a mutable version of the model that we can update each iteration
        self.model = self.create_mutable_model(self.model)
        # Getting the array id mappings
        array_ids = self.get_array_indices()
        
        ########## Data preprocessing
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
                input_ems = list(emstream)
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
                    # Try to avoid having a small bit that's split off at the end
                    if len(splits) and len(input_ems) <= split_length / 5:
                        # Add these to the end of the last split
                        # This will make it slightly longer than requested
                        splits[-1][1].extend(input_ems)
                    else:
                        splits.append((first, input_ems))
                split_emissions.extend(splits)
        else:
            # All streams begin a song
            split_emissions = [(True,stream) for stream in emissions]
        logger.info("Sequence lengths after preprocessing: %s" % 
                " ".join([str(len(em[1])) for em in split_emissions]))
        ##########
        
        # Special case of -1 for number of sequences
        # No point in creating more processes than there are sequences
        if processes == -1 or processes > len(split_emissions):
            processes = len(split_emissions)
        
        iteration = 0
        last_logprob = None
        while iteration < max_iterations:
            logger.info("Beginning iteration %d" % iteration)
            current_logprob = 0.0
            
            # Build a tuple of the arrays that will be updated by each sequence
            self.global_arrays = self.get_empty_arrays()
            
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
                        
                        def _notifier_closure(seq_index):
                            def _notifier(res):
                                logger.info("Sequence %d finished" % seq_index)
                            return _notifier
                        # Create some empty arrays for the updates to go into
                        empty_arrays = self.get_empty_arrays()
                        # Fire off a new call to the process pool for every sequence
                        async_results.append(
                                pool.apply_async(self.sequence_updates, 
                                                 (sequence, self.model, empty_arrays, array_ids), 
                                                 { 'update_initial' : first },
                                                 _notifier_closure(seq_i)) )
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
                    # If there was an exception in sequence_updates, it 
                    #  will get raised here
                    res_tuple = res.get()
                    # Run the callback on the results from this process
                    # It might seem sensible to do this using the callback 
                    #  arg to apply_async, but then the callback must be 
                    #  picklable and it doesn't buy us anything really
                    self.sequence_updates_callback(res_tuple)
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
                        # Create some empty arrays for the updates to go into
                        empty_arrays = self.get_empty_arrays()
                        updates = self.sequence_updates(
                                            sequence, self.model,
                                            empty_arrays, array_ids,
                                            update_initial=first)
                        self.sequence_updates_callback(updates)
                        # Update the overall logprob
                        current_logprob += updates[-1]
            
            ######## Model updates
            # Update the main model
            self.update_model(self.global_arrays, array_ids)
            
            # Clear the model's cache so we get the new probabilities
            self.model.clear_cache()
            
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
            
            # Only save if we've been asked to save between iterations
            if save_intermediate:
                self.save()
        
        self.record_history("Completed Baum-Welch training")
        # Always save the model now that we're done
        self.save()
        return self.model


class BaumWelchTrainingError(Exception):
    pass
