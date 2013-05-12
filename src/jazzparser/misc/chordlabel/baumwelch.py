"""Baum-Welch EM trainer for the chord labeling model.

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

from jazzparser.utils.nltk.probability import logprob
from jazzparser.utils.options import ModuleOption
from jazzparser.utils.strings import str_to_bool
from jazzparser.utils.base import ExecutionTimer

from jazzparser.utils.nltk.ngram.baumwelch import BaumWelchTrainer

# Small quantity added to every probability to ensure we never get zeros
ADD_SMALL = 1e-6

def sequence_updates(sequence, last_model, empty_arrays, array_ids, 
                                                        update_initial=True):
    """
    Evaluates the forward/backward probability matrices for a 
    single sequence under the model that came from the previous 
    iteration and returns matrices that contain the updates 
    to be made to the distributions during this iteration.
    
    This is wrapped up in a function so it can be run in 
    parallel for each sequence. Once all sequences have been 
    evaluated, the results are combined and model updated.
    
    @type update_initial: bool
    @param update_initial: if update_initial=False, 
        the initial state distribution updates won't be made for this sequence
    
    """
    try:
        (initial_keys, initial_chords, key_trans, chord_trans, ems, 
            initial_keys_denom, initial_chords_denom, key_trans_denom, 
            chord_trans_denom, ems_denom) = empty_arrays
        chord_ids, chord_type_ids = array_ids
        
        # Compute the forwards with seq_prob=True
        fwds,seq_logprob = last_model.normal_forward_probabilities(sequence, seq_prob=True)
        # gamma contains the state occupation probability for each state at each 
        #  timestep
        gamma = last_model.gamma_probabilities(sequence, forward=fwds)
        # xi contains the probability of every state transition at every timestep
        xi = last_model.compute_xi(sequence)
        
        label_dom = last_model.label_dom
        # Enumerate the label dom
        state_ids = dict([(state,id) for (id,state) in enumerate(label_dom)])
        T = len(sequence)
        
        for time in range(T):
            for state in label_dom:
                keyi, rooti, labeli = state
                state_i = state_ids[state]
                chord_i = chord_ids[((rooti-keyi)%12, labeli)]
                
                if time == 0:
                    # Update initial distributions
                    initial_keys[keyi] += gamma[time][state_i]
                    initial_chords[chord_i] += gamma[time][state_i]
                
                if time == T-1:
                    # Last timestep
                    # Update the transition dists for transitions to final state
                    chord_trans[chord_i][-1] += gamma[time][state_i]
                else:
                    # Go through all possible pairs of states to update the 
                    #  transition distributions
                    for next_state in label_dom:
                        keyj, rootj, labelj = next_state
                        state_j = state_ids[next_state]
                        chord_j = chord_ids[((rootj-keyj)%12, labelj)]
                        key_change = (keyj - keyi) % 12
                        
                        ## Transition dist updates ##
                        key_trans[key_change] += xi[time][state_i][state_j]
                        chord_trans[chord_i][chord_j] += xi[time][state_i][state_j]
                
                ## Emission dist update ##
                for note in sequence[time]:
                    pc = (note-rooti) % 12
                    ems[chord_type_ids[labeli]][pc] += gamma[time][state_i]
            
        # Calculate the denominators by summing
        initial_keys_denom[0] = array_sum(initial_keys)
        initial_chords_denom[0] = array_sum(initial_chords)
        key_trans_denom[0] = array_sum(key_trans)
        chord_trans_denom = array_sum(chord_trans, axis=1)
        ems_denom = array_sum(ems, axis=1)
        
        # Wrap this all up in a tuple to return to the master
        return (initial_keys, initial_chords, key_trans, chord_trans, ems, 
            initial_keys_denom, initial_chords_denom, key_trans_denom, 
            chord_trans_denom, ems_denom, seq_logprob)
    except KeyboardInterrupt:
        return

class HPBaumWelchTrainer(BaumWelchTrainer):
    """
    Baum-Welch training for L{jazzparser.misc.chordlabel.HPChordLabeler} 
    models.
    
    """
    OPTIONS = BaumWelchTrainer.OPTIONS + [
        ModuleOption('initkey', filter=str_to_bool, 
            help_text="Train the initial key distribution. The default "\
                "behaviour will leave the distribution alone (probably inited "\
                "to uniform): suitable if the training data is transposed into "\
                "a common key. If your data has keys, set to true",
            usage="initkey=B, where B is 'true' or 'false' "\
                "(default true)", 
            default=False),
    ]
    
    def record_history(self, line):
        """
        Stores a line in the history of the model to keep a record of training 
        steps.
        
        """
        self.model.add_history(line)
    
    sequence_updates = staticmethod(sequence_updates)
    
    def create_mutable_model(self, model):
        return model.copy(mutable=True)
    
    def get_empty_arrays(self):
        num_chords = len(self.model.chord_dom)
        num_chord_types = len(self.model.chord_vocab)
        
        # Accumulators
        initial_keys = zeros((12,), float64)
        initial_chords = zeros((num_chords,), float64)
        key_trans = zeros((12,), float64)
        chord_trans = zeros((num_chords, num_chords+1), float64)
        ems = zeros((num_chord_types, 12), float64)
        
        # Denominator accumulators
        initial_keys_denom = zeros((1,), float64)
        initial_chords_denom = zeros((1,), float64)
        key_trans_denom = zeros((1,), float64)
        chord_trans_denom = zeros((num_chords,), float64)
        ems_denom = zeros((num_chord_types,), float64)
        
        return (initial_keys, initial_chords, key_trans, chord_trans, ems, 
                initial_keys_denom, initial_chords_denom, key_trans_denom, 
                chord_trans_denom, ems_denom)
    
    def get_array_indices(self):
        chord_ids = dict([(chord,id) for (id,chord) in \
                                        enumerate(self.model.chord_dom+[None])])
        chord_type_ids = dict([(ctype,id) for (id,ctype) in \
                                    enumerate(self.model.chord_vocab.keys())])
        return (chord_ids, chord_type_ids)
    
    def sequence_updates_callback(self, result):
        if result is None:
            # Process cancelled: do no updates
            return
        
        # The members of the result tuple (apart from the logprob at the end) 
        #  should match up with the array they're to be added to in global_arrays
        for local_array,global_array in zip(result[:10], self.global_arrays):
            # Add the arrays together and store the result in the global array
            array_add(global_array, local_array, global_array)
    
    def update_model(self, arrays, array_ids):
        """
        Replaces the distributions of the saved model with the probabilities 
        taken from the arrays of updates. self.model is expected to be 
        made up of mutable distributions when this is called.
        
        """
        (initial_keys, initial_chords, key_trans, chord_trans, ems, 
            initial_keys_denom, initial_chords_denom, key_trans_denom, 
            chord_trans_denom, ems_denom) = arrays
        chord_ids, chord_type_ids = array_ids
        
        num_chords = len(self.model.chord_dom)
        num_emissions = len(self.model.emission_dom)
        num_chord_types = len(self.model.chord_vocab)
        
        # Initial keys distribution
        # Only update this distribution if asked to: often we should leave it
        if self.options['initkey']:
            for key in range(12):
                prob = logprob(initial_keys[key] + ADD_SMALL) - \
                        logprob(initial_keys_denom[0] + ADD_SMALL*12)
                self.model.initial_key_dist.update(key, prob)
        
        # Initial chords distribution
        for chord in self.model.chord_dom:
            chordi = chord_ids[chord]
            
            prob = logprob(initial_chords[chordi] + ADD_SMALL) - \
                    logprob(initial_chords_denom[0] + ADD_SMALL*num_chords)
            self.model.initial_chord_dist.update(chord, prob)
            
        # Key transition distribution
        for key in range(12):
            prob = logprob(key_trans[key] + ADD_SMALL) - \
                    logprob(key_trans_denom[0] + ADD_SMALL*12)
            self.model.key_transition_dist.update(key, prob)
        
        # Chord transition distribution
        for chord0 in self.model.chord_dom:
            chordi = chord_ids[chord0]
            
            for chord1 in self.model.chord_dom+[None]:
                chordj = chord_ids[chord1]
                
                prob = logprob(chord_trans[chordi][chordj] + ADD_SMALL) - \
                       logprob(chord_trans_denom[chordi] + ADD_SMALL*num_chords)
                self.model.chord_transition_dist[chord0].update(chord1, prob)
        
        # Emission distribution
        for label in self.model.chord_vocab:
            labeli = chord_type_ids[label]
            
            for pitch in range(12):
                prob = logprob(ems[labeli][pitch] + ADD_SMALL) - \
                        logprob(ems_denom[labeli] + ADD_SMALL*num_chord_types)
                self.model.emission_dist[label].update(pitch, prob)
    
    def save(self):
        # If the writing fails, wait till I've had a chance to sort it 
        #  out and then try again. This happens when my AFS token runs 
        #  out
        while True:
            try:
                self.model.save()
            except (IOError, OSError), err:
                print "Error writing model to disk: %s. " % err
                raw_input("Press <enter> to try again... ")
            else:
                # Saved normally
                break
