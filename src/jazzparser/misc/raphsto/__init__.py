"""Raphael and Stoddard's model for chord labelling from midi data.

An implementation of the models described in Function Harmonic Analysis Using 
Probabilistic Models, Raphael and Stoddard, 2004.

In the future, this should be fitted into the tagger framework. For now it's 
just a rough prototype, so I'm not bothering to work out how it will implement 
the tagger interface, etc.

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

import numpy, os, re
from numpy import ones, float64, sum as array_sum, zeros
import cPickle as pickle
from datetime import datetime

from jazzparser.utils.nltk.ngram import NgramModel
from jazzparser.utils.nltk.probability import mle_estimator, logprob, add_logs, \
                        sum_logs, prob_dist_to_dictionary_prob_dist, \
                        cond_prob_dist_to_dictionary_cond_prob_dist
from jazzparser import settings
from . import constants
from .midi import MidiHandler

from nltk.probability import ConditionalProbDist, FreqDist, \
            ConditionalFreqDist, DictionaryProbDist, \
            DictionaryConditionalProbDist, MutableProbDist

FILE_EXTENSION = "mdl"

def format_state(state, time=None):
    """
    Formats a state label tuple as a string for output.
    
    """
    tonic,mode,chord = state
    tonic_str = constants.TONIC_NAMES[tonic]
    mode_str = constants.MODE_NAMES[mode]
    chord_str = constants.CHORD_NAMES[chord]
    return "%s %s: %s" % (tonic_str, mode_str, chord_str)

def format_state_as_chord(state, time=None):
    """
    Formats a state label tuple, like L{format_state}, but produces a chord 
    name. This contains less information than the result of L{format_state},
    but is easier to read.
    
    """
    tonic,mode,chord = state
    scale_chord_root = constants.CHORD_NOTES[mode][chord][0]
    chord_root = (tonic+scale_chord_root) % 12
    # Work out the triad type of this chord
    triad_name = constants.TRIAD_TYPE_SYMBOLS[constants.SCALE_TRIADS[mode][chord]]
    return "%s%s" % (constants.TONIC_NAMES[chord_root], triad_name)

def format_state_as_raphsto(state, time=None):
    """
    State representation modeled on the original R&S model's labels that are 
    inserted into the example MIDI files.
    
    """
    tonic,mode,chord = state
    # First part is the roman numeral chord name
    roman_chord = constants.CHORD_NAMES[chord].ljust(4)
    # Then the key name
    tonic_name = constants.TONIC_NAMES[tonic].lower().ljust(2)
    # including mode
    mode_name = constants.MODE_SHORT_NAMES[mode]
    # Put the time if available
    if time is None:
        time = ""
    else:
        time = " ms = %d" % time
    # Work out the indentation on the basis of a line of fifths, starting at C
    line_of_fifths = [ 0, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10, 5 ]
    pos = line_of_fifths.index(tonic)
    padding = " " * (pos*2)
    return "%s%s(%s%s)%s" % (padding, roman_chord, tonic_name, mode_name, time)

def states_to_key_transition(state, previous_state):
    """
    Takes a state and previous state representation and returns the 
    (state, previous state) pair that is used by the model. This mapping 
    effectively implements the parameter tying of the first part of the 
    transition distribution.
    
    """
    tonic, mode, chord = state
    ptonic, pmode, pchord = previous_state
    return ( ((tonic-ptonic)%12, mode), pmode )

def raphsto_d(pitch_class, state):
    """
    The function described in the paper as d. Maps a pitch class to an 
    abstract representation that depends on the state.
    
    This gets called a bajillion times, so needs to be as efficient as 
    possible.
    
    """
    tonic, mode, chord = state
    # Get the pitch class relative to the tonic
    key_pitch_class = (pitch_class - tonic) % 12
    
    # Find where the note is in the chord denoted by the state
    try:
        chord_pos = constants.CHORD_NOTES[mode][chord].index(key_pitch_class)
    except ValueError:
        # Not in the chord
        # Try the scale
        scale = constants.SCALES[mode]
        if key_pitch_class in scale:
            # Not in chord, but in scale
            return 3
        else:
            # Not in chord or scale
            return 4
    else:
        if chord_pos == 0:
            # Root of chord
            return 0
        elif chord_pos == 1:
            # Third of chord
            return 1
        else:
            # Fifth of chord, or beyond (e.g. seventh)
            return 2


class RaphstoHmm(NgramModel):
    """
    Hidden Markov Model that implements the model described in the paper.
    
    States are in the form of a tuple (tonic,mode,chord) where tonic is in 
    \{0, ..., 11\}; mode is one of \{L{constants.MODE_MAJOR}, 
    L{constants.MODE_MINOR}\}; chord is one of \{L{constants.CHORD_I}, 
    ..., L{constants.CHORD_VII}\}.
    
    Emissions are in the form of a list of pairs (pc,r), where pc is a pitch 
    class (like C{tonic} above) and r is an onset time abstraction and is 
    one of \{0, ...,3\}.
    
    Unlike with NgramModel, the emission domain is the domain of values 
    from which each element of an emission is selected. In other words, 
    the actually domain of emissions is the powerset of C{emission_dom}.
    
    In the description of the model, r is described as a condition of the 
    emission distribution. Although the model is truly replicated here, the 
    interface suggests otherwise, since we treat the rythmic markers as if 
    they're part of the emissions. From a conceptual point of view, this makes 
    more sense and I think it's rather odd that the model doesn't treat them 
    this way.
    
    As for prior distributions (start state distribution), we ignore 
    the tonic of the first state - it doesn't make any sense to look 
    at it since the model is pitch-invariant throughout. We then 
    just use our marginalized chord distribution and assume that the 
    mode distribution is uniform (there are only two and it probably 
    won't make much difference).
    
    @note: B{mutable distributions}: if you use mutable distributions for 
    transition or emission distributions, make sure you invalidate the cache 
    by calling L{clear_cache} after updating the distributions. Various 
    caches are used to speed up retreival of probabilities. If you fail to 
    do this, you'll end up getting some values unpredictably from the old 
    distributions
    
    """
    V = {
        0 : 1,
        1 : 1,
        2 : 1,
        3 : 4,
        4 : 5
    }
    """ This is the function (mapping) described in the model as V. """
    LABEL_DOM = None
    
    def __init__(self, key_transition_dist, chord_transition_dist, \
                        emission_dist, chord_dist, model_name="default",
                        history="", description="", chord_set="scale+dom7"):
        # We override the init completely because we need a different set of 
        #  distributions
        
        # HMM model: order 2 ngram
        self.order = 2
        
        self.chord_set = chord_set
        
        # We define the domain for the distributions here, because they're fixed
        self.key_transition_dom = [(tonic,mode) for tonic in range(12) for mode in constants.MODES]
        self.chord_transition_dom = constants.CHORD_SETS[chord_set]
        self.emission_dom = [(pc,rhythm) for pc in range(12) for rhythm in range(4)]
        # The actual domain of the stored emission distribution is the domain 
        #  of the d-function (i.e. 0-4)
        self.emission_dist_dom = range(5)
        self.beat_dom = range(4)
        # This label_dom is not used for the distributions, since the 
        #  transition distribution is split up into two and has tied parameters
        # We still need to know all possible labels for decoding, though
        self.label_dom = self.get_label_dom(chord_set=chord_set)
        
        self.num_key_transitions = len(self.key_transition_dom)
        self.num_chord_transitions = len(self.chord_transition_dom)
        self.num_labels = len(self.label_dom)
        self.num_emissions = len(self.emission_dom)
        
        self.key_transition_dist = key_transition_dist
        self.chord_transition_dist = chord_transition_dist
        self.emission_dist = emission_dist
        self.chord_dist = chord_dist
        
        # We don't use backoff with this kind of model, so this is always None
        self.backoff_model = None
        
        # Name to save the model under
        self.model_name = model_name
        
        # Store a string with information about training, etc
        self.history = history
        # Store another string with an editable description
        self.description = description
        
        # Initialize the various caches
        # These will be filled as we access probabilities
        self.clear_cache()
    
    def label(self, handler):
        """
        Produces labels for the midi data using the model.
        
        Input is given in the form of a 
        L{jazzparser.misc.raphsto.midi.MidiHandler} instance.
        
        Uses Viterbi on the model to get a state sequence and returns a list 
        containing a (state,time) pair for each state change.
        
        """
        emissions,times = handler.get_emission_stream()
        # Decode using viterbi to get a list of states
        states = self.viterbi_decode(emissions)
        
        # Remove states that don't change from the previous
        last_state = None
        state_changes = []
        for state,time in zip(states,times):
            if state != last_state:
                state_changes.append((state,time))
                last_state = state
        return state_changes
        
    @classmethod
    def get_label_dom(cls, chord_set="scale+dom7"):
        if cls.LABEL_DOM is not None:
            # Use the predefined label domain (used by subclasses)
            return cls.LABEL_DOM
        else:
            # Define the label domain from the component domains
            return [(tonic,mode,chord) for tonic in range(12) \
                                       for mode in constants.MODES \
                                       for chord in constants.CHORD_SETS[chord_set]]
    
    @staticmethod
    def get_trainer():
        from .train import RaphstoBaumWelchTrainer
        return RaphstoBaumWelchTrainer
        
    def clear_cache(self):
        """
        Initializes or empties probability distribution caches.
        
        Make sure to call this if you change or update the distributions.
        
        """
        # Whole emission identity
        self._emission_cache = {}
        # Whole transition identity
        self._transition_cache = {}
        # Single note observation
        self._note_emission_cache = {}
        
    def add_history(self, string):
        """
        Adds a line to the end of this model's history string.
        
        """
        self.history += "%s: %s\n" % (datetime.now().isoformat(' '), string)
    
    def sequence_to_ngram(self, seq):
        if len(seq) > 1:
            raise RaphstoHmmError, "sequence_to_ngram() got a sequence with "\
                "more than one value. This shouldn't happen on an HMM"
        elif len(seq) == 0:
            return None
        else:
            return seq[0]
    
    def ngram_to_sequence(self, ngram):
        if ngram is None:
            return []
        else:
            return [ngram]
    
    def last_label_in_ngram(self, ngram):
        return ngram
        
    def backoff_ngram(self, ngram):
        raise RaphstoHmmError, "backoff_ngram() should never be called on "\
            "a RaphstoHmm, since we don't use backoff models"
            
    @staticmethod
    def train(*args, **kwargs):
        """
        We don't train a RaphstoHmm using the C{train} method, since our 
        training procedure is not the same as the superclass, so this would 
        be confusing, as this method would require completely different 
        input.
        
        We train our models by initializing in some way (usually hand-setting 
        of parameters), then using Baum-Welch on unlabelled data.
        
        This method will just raise a RaphstoHmmError.
        
        """
        raise RaphstoHmmError, "don't use train() to train a RaphstoHmm. "\
            "Instead initialize and then train unsupervisedly"
    
    @classmethod
    def initialize_chord_types(cls, probs, model_name="default", chord_set="scale+dom7"):
        """
        Creates a new model with the distributions initialized naively to 
        favour simple chord-types, as R&S do in the paper. They don't say 
        what values they use for C{probs}, except that they're high, medium 
        and low respectively.
        
        The transition distribution is initialized so that everything is 
        equiprobable.
        
        @type probs: 3-tuple of floats
        @param probs: probability mass to assign to (0.) chord notes, (1.) 
            scale notes and (2.) other notes. The three values should sum to
            1.0 (but will be normalized to if they don't)
        
        """
        prob_sum = sum(probs)
        probs = [p/prob_sum for p in probs]
        
        # Create a probability distribution for the emission 
        #  distribution
        dists = {}
        # Create the distribution for each possible r-value
        for r in range(4):
            probabilities = {}
            for d in [0,1,2]:
                probabilities[d] = probs[0]/3.0
            probabilities[3] = probs[1]
            probabilities[4] = probs[2]
            dists[r] = DictionaryProbDist(probabilities)
        emission_dist = DictionaryConditionalProbDist(dists)
        
        # These distributions will make everything equiprobable
        key_transition_counts = ConditionalFreqDist()
        chord_transition_counts = ConditionalFreqDist()
        chord_counts = {}
        # Get all possible labels
        label_dom = cls.get_label_dom(chord_set=chord_set)
        
        for label0 in label_dom:
            for label1 in label_dom:
                key,pkey = states_to_key_transition(label1, label0)
                # Give one count to the key transition corresponding to this state transition
                key_transition_counts[pkey].inc(key)
                # And one to the chord transition corresponding to this state transition
                if label0[0] == label1[0] and label0[1] == label1[1]:
                    # tonic = tonic', mode = mode'
                    chord_transition_counts[label0[2]].inc(label1[2])
                else:
                    chord_counts.setdefault(label1[2], 0)
                    chord_counts[label1[2]] += 1
        
        # Estimate distributions from these frequency distributions
        key_dist = ConditionalProbDist(key_transition_counts, mle_estimator, None)
        chord_trans_dist = ConditionalProbDist(chord_transition_counts, mle_estimator, None)
        chord_dist = DictionaryProbDist(chord_counts)
        # Sample these to get dictionary prob dists
        key_dist = cond_prob_dist_to_dictionary_cond_prob_dist(key_dist)
        chord_trans_dist = cond_prob_dist_to_dictionary_cond_prob_dist(chord_trans_dist)
        chord_dist = prob_dist_to_dictionary_prob_dist(chord_dist)
        
        model = cls(key_dist, \
                      chord_trans_dist, \
                      emission_dist, \
                      chord_dist, \
                      model_name=model_name,
                      chord_set=chord_set)
        model.add_history(\
            "Initialized model '%s' to chord type probabilities, using "\
            "parameters: %s, %s, %s" % (model_name, probs[0], probs[1], probs[2]))
        return model
                          
    @classmethod
    def initialize_existing_model(cls, old_model_name, model_name="default"):
        """
        Initializes a model using parameters from an already trained model.
        
        """
        # Load the trained model
        model = cls.load_model(old_model_name)
        # Change the model name and save it to a new file
        model.model_name = model_name
        # Continue the history from the old model and note the change of name
        model.add_history("Parameters from '%s' used as initialization for "\
            "model '%s'" % (old_model_name,model_name))
        model.save()
        # Now continue to use this model under its new name
        return model
        
    def set_chord_transition_probabilities(self, spec):
        """
        Sets the parameters of the chord transition distribution. This is used 
        in initialization. The parameters are extracted from a string: this is 
        so that it can be specified in a script option.
        
        The required format of the string is a comma-separated list of 
        parameters given as C0->C1-P, where C0 and C1 are chords (I, II, etc) 
        that are in the model's distribution and P is a float probability.
        Parameters not specified will be evenly distributed the remaining 
        probability mass.
        
        """
        params = {}
        param_re = re.compile(r'(?P<chord0>.+)->(?P<chord1>.+)-(?P<prob>.+)')
        chord_ids = dict((name,num) for (num,name) in constants.CHORD_NAMES.items())
        
        def _chord_id(name):
            # Get the id for the named chord
            if name not in chord_ids:
                raise RaphstoHmmParameterError, "unrecognised chord name '%s' "\
                    "in parameter spec: %s" % (name,spec)
            cid = chord_ids[name]
            if cid not in self.chord_transition_dom:
                raise RaphstoHmmParameterError, "chord %s is not used with this "\
                    "model (in parameter spec: %s)" % (name,spec)
            return cid
        
        for param_str in spec.split(","):
            # Pull out the bits of the parameter specification
            match = param_re.match(param_str.strip())
            if not match:
                raise RaphstoHmmParameterError, "could not parse parameter "\
                    "spec: %s (in: %s)" % (param_str, spec)
            parts = match.groupdict()
            chord0 = _chord_id(parts['chord0'])
            chord1 = _chord_id(parts['chord1'])
            try:
                prob = float(parts['prob'])
            except ValueError:
                raise RaphstoHmmParameterError, "not a valid probability: %s "\
                    "(in %s)" % (parts['prob'], spec)
            # Store the parameter value
            params.setdefault(chord0, {})[chord1] = prob
        
        # Set the values in the transition distribution
        dists = {}
        for chord0 in self.chord_transition_dom:
            dist_params = {}
            if chord0 not in params:
                # Not given in the spec: uniform distribution
                uniform_mass = 1.0 / len(self.chord_transition_dom)
                for chord1 in self.chord_transition_dom:
                    dist_params[chord1] = uniform_mass
            else:
                # Work out the prob mass to be distributed among unspecified parameters
                not_given = len(self.chord_transition_dom) - len(params[chord0])
                if not_given > 0:
                    given_mass = sum(params[chord0].values(), 0.0)
                    uniform_mass = (1.0 - given_mass) / not_given
                else:
                    uniform_mass = 0.0
                # Calculate the whole distribution
                for chord1 in self.chord_transition_dom:
                    if chord1 in params[chord0]:
                        dist_params[chord1] = params[chord0][chord1]
                    else:
                        dist_params[chord1] = uniform_mass
            dists[chord0] = DictionaryProbDist(dist_params)
        # Use this distribution instead of what's already there
        self.chord_transition_dist = DictionaryConditionalProbDist(dists)
        
        self.add_history("Set chord transition distribution using "\
            "parameters: %s" % spec)
        
    def retrain_unsupervised(self, *args, **kwargs):
        """
        Unsupervised training. Passes straight over to the 
        L{train.RaphstoBaumWelchTrainer}.
        
        @see: jazzparser.misc.raphsto.train.RaphstoBaumWelchTrainer
        
        """
        from .train import RaphstoBaumWelchTrainer
        trainer = RaphstoBaumWelchTrainer(self)
        trainer.train(*args, **kwargs)
        
    def transition_log_probability(self, state, previous_state):
        # If we're transitioning to None, the sequence is over
        # We only ask this probability when we know the sequence has finished, 
        #  so the probability of the end state is 1.0.
        if state is None:
            return 0.0
        cache_key = (state, previous_state)
        if cache_key not in self._transition_cache:
            tonic, mode, chord = state
            if previous_state is None:
                # Start state: prior state distribution
                # The tonic doesn't affect this: we ignore it and distribute 
                #  prob mass uniformly (divide by 12)
                # We also ignore the mode: we could train a mode 
                #  distribution, but at the moment we don't bother (divide by 2)
                chord_transition_prob = self.chord_dist.logprob(chord)
                self._transition_cache[cache_key] = chord_transition_prob - 24.0
            else:
                ptonic, pmode, pchord = previous_state
                # The first part is the key transition
                # p(t'-t, m' | m)
                key,pkey = states_to_key_transition(state, previous_state)
                key_transition_prob = self.key_transition_dist[pkey].logprob(key)
                # The second part is the chord transition
                if tonic == ptonic and mode == pmode:
                    # p(c' | c)
                    chord_transition_prob = self.chord_transition_dist[pchord].logprob(chord)
                else:
                    # p(c')
                    chord_transition_prob = self.chord_dist.logprob(chord)
                self._transition_cache[cache_key] = \
                                key_transition_prob + chord_transition_prob
        return self._transition_cache[cache_key]
        
    def emission_log_probability(self, emission, state):
        if len(emission) == 0:
            # No notes emitted
            # Not clear from paper what the probability of this should be
            # Give it zero for now
            return float('-inf')
        cache_key = (tuple(sorted(emission)), state)
        if cache_key not in self._emission_cache:
            prob = 0.0
            # Take the product of the probability for each note in the set
            for pc,beat in emission:
                # Get the value of the d function for this note
                d = raphsto_d(pc, state)
                
                note_cache_key = (beat, d)
                if note_cache_key not in self._note_emission_cache:
                    # Now get the probability of this d value, conditioned on the r value
                    # We divide by V, to spread the probability over other notes 
                    #  that share the same d value
                    self._note_emission_cache[note_cache_key] = \
                        self.emission_dist[beat].logprob(d) - RaphstoHmm.V[d]
                prob += self._note_emission_cache[note_cache_key]
            self._emission_cache[cache_key] = prob
        return self._emission_cache[cache_key]
        
    
    def forward_log_probabilities(self, sequence, normalize=True):
        """We override this to provide a faster implementation.
        
        It might also be possible to speed up the superclass' implementation 
        using numpy, but it's easier here because we know we're using an 
        HMM, not a higher-order ngram.
        
        This is based on the fwd prob calculation in NLTK's HMM implementation.
        
        Returns a numpy 2d array instead of a list of lists.
        
        """
        T = len(sequence)
        N = len(self.label_dom)
        alpha = numpy.zeros((T, N), numpy.float64)
        
        # Prepare the first column of the matrix: probs of all states in the 
        #  first timestep
        for i,state in enumerate(self.label_dom):
            alpha[0,i] = self.transition_log_probability(state, None) + \
                            self.emission_log_probability(sequence[0], state)
        
        # Iterate over the other timesteps
        for t in range(1, T):
            for j,sj in enumerate(self.label_dom):
                # Multiply each previous state's prob by the transition prob 
                #  to this state and sum them all together
                log_probs = [
                    alpha[t-1, i] + self.transition_log_probability(sj, si) \
                        for i,si in enumerate(self.label_dom)]
                # Also multiply this by the emission probability
                alpha[t, j] = sum_logs(log_probs) + \
                                self.emission_log_probability(sequence[t], sj)
        # Normalize by dividing all values by the total probability
        if normalize:
            for t in range(T):
                total = sum_logs(alpha[t,:])
                for j in range(N):
                    alpha[t,j] -= total
        return alpha
    
    def backward_log_probabilities(self, sequence, normalize=True):
        """We override this to provide a faster implementation.
        
        @see: forward_log_probability
        
        Returns a numpy 2d array instead of a list of lists.
        
        """
        T = len(sequence)
        N = len(self.label_dom)
        beta = numpy.zeros((T, N), numpy.float64)
        
        # Initialize
        beta[T-1, :] = numpy.log2(1.0/N)
        
        # Iterate backwards over the other timesteps
        for t in range(T-2, -1, -1):
            for i,si in enumerate(self.label_dom):
                # Multiply each next state's prob by the transition prob 
                #  from this state to that and the emission prob in that next 
                #  state
                log_probs = [
                    beta[t+1, j] + self.transition_log_probability(sj, si) + \
                        self.emission_log_probability(sequence[t+1], sj) \
                        for j,sj in enumerate(self.label_dom)]
                beta[t, i] = sum_logs(log_probs)
            # Normalize by dividing all values by the total probability
            if normalize:
                total = sum_logs(beta[t,:])
                for j in range(N):
                    beta[t,j] -= total
        return beta
    
    
    def normal_forward_probabilities(self, sequence):
        """If you want the normalized matrix of forward probabilities, it's 
        ok to use normal (non-log) probabilities and these can be computed 
        more quickly, since you don't need to sum logs (which is time 
        consuming).
        
        Returns the matrix, and also the vector of values that each timestep 
        was divided by to normalize (i.e. total probability of each timestep 
        over all states).
        Also returns the total log probability of the sequence.
        
        @return: (matrix,normalizing vector,log prob)
        
        """
        T = len(sequence)
        N = len(self.label_dom)
        alpha = numpy.zeros((T, N), numpy.float64)
        scale = numpy.zeros(T, numpy.float64)
        
        # Prepare the first column of the matrix: probs of all states in the 
        #  first timestep
        for i,state in enumerate(self.label_dom):
            alpha[0,i] = self.transition_probability(state, None) * \
                            self.emission_probability(sequence[0], state)
        # Normalize by dividing all values by the total probability
        total = sum(alpha[0,:])
        for i in range(N):
            alpha[0,i] /= total
        scale[0] = total
        
        # Iterate over the other timesteps
        for t in range(1, T):
            for j,sj in enumerate(self.label_dom):
                # Multiply each previous state's prob by the transition prob 
                #  to this state and sum them all together
                log_prob = sum(
                    (alpha[t-1, i] * self.transition_probability(sj, si) \
                        for i,si in enumerate(self.label_dom)), 0.0)
                # Also multiply this by the emission probability
                alpha[t, j] = log_prob * \
                                self.emission_probability(sequence[t], sj)
            # Normalize by dividing all values by the total probability
            total = sum(alpha[t,:])
            for j in range(N):
                alpha[t,j] /= total
            scale[t] = total
        
        # Multiply together the probability of each timestep to get the whole 
        # probability of the sequence
        log_prob = sum((logprob(total) for total in scale), 0.0)
        return alpha,scale,log_prob
    
    def normal_backward_probabilities(self, sequence):
        """
        @see: normal_forward_probabilities
        
        (except that this doesn't return the logprob)
        
        """
        T = len(sequence)
        N = len(self.label_dom)
        beta = numpy.zeros((T, N), numpy.float64)
        scale = numpy.zeros(T, numpy.float64)
        
        # Initialize
        beta[T-1, :] = 1.0/N
        scale[T-1] = 1.0
        
        # Iterate backwards over the other timesteps
        for t in range(T-2, -1, -1):
            for i,si in enumerate(self.label_dom):
                # Multiply each next state's prob by the transition prob 
                #  from this state to that and the emission prob in that next 
                #  state
                beta[t, i] = sum(
                    (beta[t+1, j] * self.transition_probability(sj, si) * \
                        self.emission_probability(sequence[t+1], sj) \
                        for j,sj in enumerate(self.label_dom)), 0.0)
            # Normalize by dividing all values by the total probability
            total = sum(beta[t,:])
            for j in range(N):
                beta[t,j] /= total
            scale[t] = total
        return beta,scale
    
    def compute_gamma(self, sequence, forward=None, backward=None):
        """
        Computes the gamma matrix used in Baum-Welch. This is the matrix 
        of state occupation probabilities for each timestep. It is computed 
        from the forward and backward matrices.
        
        These can be passed in as 
        arguments to avoid recomputing if you need to reuse them, but will 
        be computed from the model if not given. They are assumed to be 
        the matrices computed by L{normal_forward_probabilities} and 
        L{normal_backward_probabilities} (i.e. normalized, non-log 
        probabilities).
        
        """
        if forward is None:
            forward = self.normal_forward_probabilities(sequence)
        if backward is None:
            backward = self.normal_backward_probabilities(sequence)
        # T is the number of timesteps
        # N is the number of states
        T,N = forward.shape
        
        gamma = zeros((T,N), float64)
        for t in range(T):
            for i in range(N):
                gamma[t][i] = forward[t][i]*backward[t][i]
            denominator = array_sum(gamma[t])
            # Normalize
            for i in range(N):
                gamma[t][i] /= denominator
        return gamma
        
    def compute_xi(self, sequence, forward=None, backward=None):
        """
        Computes the xi matrix used by Baum-Welch. It is the matrix of joint 
        probabilities of occupation of pairs of conecutive states: 
        P(i_t, j_{t+1} | O).
        
        As with L{compute_gamma} forward and backward matrices can optionally 
        be passed in to avoid recomputing.
        
        """
        if forward is None:
            forward = self.normal_forward_probabilities(sequence)
        if backward is None:
            backward = self.normal_backward_probabilities(sequence)
        # T is the number of timesteps
        # N is the number of states
        T,N = forward.shape
        
        xi = zeros((T-1,N,N), float64)
        for t in range(T-1):
            total = 0.0
            # For each first state
            for i,statei in enumerate(self.label_dom):
                # and each second state
                for j,statej in enumerate(self.label_dom):
                    # get the probability of this pair of states given the emissions
                    prob = forward[t][i] * backward[t+1][j] * \
                            self.transition_probability(statej, statei) * \
                            self.emission_probability(sequence[t+1], statej)
                    xi[t][i][j] = prob
                    total += prob
            # Normalize all these probabilities
            for i in range(N):
                for j in range(N):
                    xi[t][i][j] /= total
        return xi
        
    def to_picklable_dict(self):
        """
        Produces a picklable representation of model as a dict.
        You can't just pickle the object directly because some of the 
        NLTK classes can't be pickled. You can pickle this dict and 
        reconstruct the model using NgramModel.from_picklable_dict(dict).
        
        """
        from jazzparser.utils.nltk.storage import object_to_dict
        return {
            'key_transition_dist' : object_to_dict(self.key_transition_dist),
            'chord_transition_dist' : object_to_dict(self.chord_transition_dist),
            'emission_dist' : object_to_dict(self.emission_dist),
            'chord_dist' : object_to_dict(self.chord_dist),
            'history' : self.history,
            'description' : self.description,
            'chord_set' : self.chord_set,
        }
        
    @classmethod
    def from_picklable_dict(cls, data, model_name="default"):
        """
        Reproduces an n-gram model that was converted to a picklable 
        form using to_picklable_dict.
        
        """
        from jazzparser.utils.nltk.storage import dict_to_object
        return cls(dict_to_object(data['key_transition_dist']),
                          dict_to_object(data['chord_transition_dist']),
                          dict_to_object(data['emission_dist']),
                          dict_to_object(data['chord_dist']),
                          model_name=model_name,
                          history=data.get('history', ''),
                          description=data.get('description', ''),
                          chord_set=data.get('chord_set', 'scale+dom7'))
    
    @classmethod
    def _get_model_dir(cls):
        return os.path.join(settings.MODEL_DATA_DIR, "raphsto")
        
    @classmethod
    def _get_filename(cls, model_name):
        return os.path.join(cls._get_model_dir(), "%s.%s" % (model_name, FILE_EXTENSION))
    def _get_my_filename(self):
        return type(self)._get_filename(self.model_name)
    _filename = property(_get_my_filename)
    
    @classmethod
    def list_models(cls):
        """
        Returns a list of the names of available models.
        
        """
        model_dir = cls._get_model_dir()
        if not os.path.exists(model_dir):
            return []
        model_ext = ".%s" % FILE_EXTENSION
        names = [name.rpartition(model_ext) for name in os.listdir(model_dir)]
        return [name for name,ext,right in names if ext == model_ext and len(right) == 0]
        
    def save(self):
        """
        Saves the model data to a file.
        
        """
        data = pickle.dumps(self.to_picklable_dict(), 2)
        filename = self._filename
        # Check the directory exists
        filedir = os.path.dirname(filename)
        if not os.path.exists(filedir):
            os.mkdir(filedir)
        f = open(filename, 'w')
        f.write(data)
        f.close()
        
    def delete(self):
        """
        Removes all the model's data.
        
        """
        fn = self._filename
        if os.path.exists(fn):
            os.remove(fn)
            
    @classmethod
    def load_model(cls, model_name):
        filename = cls._get_filename(model_name)
        # Load the model from a file
        if os.path.exists(filename):
            f = open(filename, 'r')
            model_data = f.read()
            model_data = pickle.loads(model_data)
            f.close()
        else:
            raise RaphstoModelLoadError, "the model '%s' has not been trained" % model_name
        return cls.from_picklable_dict(model_data, model_name=model_name)



class RaphstoHmmThreeChord(RaphstoHmm):
    """
    Modification of the Raphsto algorithm that allows it only to assign one 
    of three chords: I, IV and V. They say that secondary dominants are 
    treated using modulation, but in fact their model uses IIs, VIs, etc.
    This version forces these things to be handled using modulation.
    
    """
    def __init__(self, *args, **kwargs):
        kwargs['chord_set'] = 'three-chord'
        RaphstoHmm.__init__(self, *args, **kwargs)

    @classmethod
    def _get_model_dir(cls):
        # Use a different directory for these models
        return os.path.join(settings.MODEL_DATA_DIR, "raphsto3c")



class RaphstoHmmFourChord(RaphstoHmm):
    """
    Like L{RaphstoHmmThreeChord}, but also allows a minor secondary dominant 
    chord (II).
    
    """
    def __init__(self, *args, **kwargs):
        kwargs['chord_set'] = 'four-chord'
        RaphstoHmm.__init__(self, *args, **kwargs)

    @classmethod
    def _get_model_dir(cls):
        # Use a different directory for these models
        return os.path.join(settings.MODEL_DATA_DIR, "raphsto4c")
    
class RaphstoHmmUnigram(RaphstoHmm):
    """
    Like L{RaphstoHmm}, but always gives all state transitions equal 
    probability, so that it is effectively a unigram model.
    
    Train with L{jazzparser.misc.raphsto.train.RaphstoBaumWelchUnigramTrainer}.
    
    """
    def __init__(self, *args, **kwargs):
        super(RaphstoHmmUnigram, self).__init__(*args, **kwargs)
        # Precompute the uniform transition probability
        self._uniform_transition = 1.0 / len(self.label_dom)
        self._uniform_transition_log = - logprob(len(self.label_dom))

    def transition_log_probability(self, state, previous_state):
        # If we're transitioning to None, the sequence is over
        if state is None:
            return 0.0
        else:
            return self._uniform_transition_log
            
    def transition_probability(self, state, previous_state):
        if state is None:
            return 1.0
        else:
            return self._uniform_transition
    
    @staticmethod
    def get_trainer():
        from .train import RaphstoBaumWelchUnigramTrainer
        return RaphstoBaumWelchUnigramTrainer

    @classmethod
    def _get_model_dir(cls):
        # Use a different directory for these models
        return os.path.join(settings.MODEL_DATA_DIR, "raphstouni")

class RaphstoHmmError(Exception):
    pass

class RaphstoHmmParameterError(Exception):
    pass

class RaphstoModelLoadError(Exception):
    pass
        
class RaphstoModelSaveError(Exception):
    pass

MODEL_TYPES = {
    'standard' : RaphstoHmm,
    'three-chord' : RaphstoHmmThreeChord,
    'four-chord' : RaphstoHmmFourChord,
    'unigram' : RaphstoHmmUnigram,
}
