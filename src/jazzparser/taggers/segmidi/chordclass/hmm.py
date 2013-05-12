"""HMM that underlies the chordclass MIDI tagger.

This is based on the model proposed by Raphael & Stoddard for harmonic analysis.
See L{jazzparser.misc.raphsto} for the pure implementation of their model,
which this builds on.

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

import numpy, os, re, math, warnings
from numpy import ones, float64, sum as array_sum, zeros
import cPickle as pickle
from datetime import datetime

from jazzparser.utils.nltk.ngram import NgramModel
from jazzparser.utils.nltk.probability import mle_estimator, logprob, add_logs, \
                        sum_logs, prob_dist_to_dictionary_prob_dist, \
                        cond_prob_dist_to_dictionary_cond_prob_dist, \
                        prob_dist_to_dictionary_prob_dist
from jazzparser.utils.base import group_pairs
from jazzparser.taggers.models import TaggerModel
from jazzparser import settings
from jazzparser.utils.midi import note_ons

from nltk.probability import ConditionalProbDist, FreqDist, \
            ConditionalFreqDist, DictionaryProbDist, \
            DictionaryConditionalProbDist, MutableProbDist

class ChordClassHmm(NgramModel):
    """
    Hidden Markov Model based on the model described in the paper. The 
    structure of this model was descibed in my 2nd year review.
    
    States are in the form of a tuple C{(schema,root)} where C{schema} is the 
    name of a lexical schema from the jazz grammar and C{root} is a pitch 
    class root.
    
    Emissions are in the form of a list of pairs (pc,r), where pc is a pitch 
    class (like C{root} above) and r is an onset time abstraction. The 
    metrical model (the r part) can be disabled.
    
    An additional distribution is stored over the number of notes emitted.
    This needs to be included in the computation of the emission probability 
    for a set of notes for it to form a valid probability distribution. 
    For simplicity, we don't condition this on the chord class.
    We also need a maximum number of possible notes that can be emitted 
    C{max_notes} so that this is a finite distribution.
    
    Unlike with NgramModel, the emission domain is the domain of values 
    from which each element of an emission is selected. In other words, 
    the actual domain of emissions is the infinite set of combinations 
    of the values in C{emission_dom} (in fact finite because of C{max_notes})
    
    As for prior distributions (start state distribution), we ignore 
    the root of the first state - it doesn't make any sense to look 
    at it since the model is pitch-invariant throughout.
    
    @note: B{mutable distributions}: if you use mutable distributions for 
    transition or emission distributions, make sure you invalidate the cache 
    by calling L{clear_cache} after updating the distributions. Various 
    caches are used to speed up retreival of probabilities. If you fail to 
    do this, you'll end up getting some values unpredictably from the old 
    distributions
    
    @todo: Make this inherit from 
    L{jazzparser.utils.nltk.ngram.DictionaryHmmModel} so that we can use a 
    specialization of the 
    L{jazzparser.utils.nltk.ngram.baumwelch.BaumWelchTrainer} with it.
    
    """
    def __init__(self, schema_transition_dist, root_transition_dist, 
                        emission_dist, emission_number_dist, 
                        initial_state_dist,
                        schemata, chord_class_mapping, 
                        chord_classes, history="", description="", 
                        metric=False,
                        illegal_transitions=[],
                        fixed_root_transitions={}):
        warnings.warn("DEPRECATED: The chord class tagger was never really "\
            "finished properly, so is deprecated")
        # We override the init completely because we need a different set of 
        #  distributions
        
        # HMM model: order 2 ngram
        self.order = 2
        self.metric = metric
        if metric:
            self.r_values = range(4)
        else:
            self.r_values = [0]
        
        # We define the domain for the distributions here, because they're fixed
        self.root_transition_dom = list(range(12))
        self.schemata = schemata
        self.emission_dom = list(range(12))
        self.max_notes = max(emission_number_dist.samples())
        # Possible state labels - schemata
        self.label_dom = sum(\
            [[(schema,root,cclass) for cclass in chord_class_mapping[schema]] \
                        for schema in schemata for root in range(12)], [])
        
        self.num_labels = len(self.label_dom)
        self.num_emissions = len(self.emission_dom)
        
        self.schema_transition_dist = schema_transition_dist
        self.root_transition_dist = root_transition_dist
        self.emission_dist = emission_dist
        self.initial_state_dist = initial_state_dist
        self.emission_number_dist = emission_number_dist
        
        self.chord_class_mapping = chord_class_mapping
        self.chord_classes = chord_classes
        self.num_chord_classes = dict(\
            [(schema, len(chord_class_mapping[schema])) for schema in schemata])
        
        # Transition probabilities will be scaled to redistribution the 
        #  prob mass from illegal transitions
        self.illegal_transitions = illegal_transitions
        self.fixed_root_transitions = fixed_root_transitions
        
        # We don't use backoff with this kind of model, so this is always None
        self.backoff_model = None
        # Store a string with information about training, etc
        self.history = history
        # Store another string with an editable description
        self.description = description
        # Initialize the various caches
        # These will be filled as we access probabilities
        self.clear_cache()
        
    def clear_cache(self):
        """
        Initializes or empties probability distribution caches.
        
        Make sure to call this if you change or update the distributions.
        
        """
        # Whole emission-state identity
        self._emission_cache = {}
        # Class-dependent emission identity
        self._emission_class_cache = {}
        # Whole transition identity
        self._transition_cache = {}
        
        # Recompute the probability scalers
        illegal_prob = dict([(label, 0.0) for label in self.schemata])
        for label0,label1 in self.illegal_transitions:
            # Sum up the probability of illegal transitions, which will be 
            #  treated as 0
            illegal_prob[label0] += self.schema_transition_dist[label0].prob(label1)
        self._schema_prob_scalers = {}
        for label in self.schemata:
            # Compute what to scale the other probabilities by
            self._schema_prob_scalers[label] = - logprob(1.0 - illegal_prob[label])
        
    def add_history(self, string):
        """ Adds a line to the end of this model's history string. """
        self.history += "%s: %s\n" % (datetime.now().isoformat(' '), string)
    
    def sequence_to_ngram(self, seq):
        """ Needed for the generic Ngram stuff. """
        if len(seq) > 1:
            raise ValueError, "sequence_to_ngram() got a sequence with "\
                "more than one value. This shouldn't happen on an HMM"
        elif len(seq) == 0:
            return None
        else:
            return seq[0]
    
    def ngram_to_sequence(self, ngram):
        """ Needed for the generic Ngram stuff. """
        if ngram is None:
            return []
        else:
            return [ngram]
    
    def last_label_in_ngram(self, ngram):
        """ Needed for the generic Ngram stuff. """
        return ngram
        
    def backoff_ngram(self, ngram):
        """ Needed for the generic Ngram stuff. """
        raise NotImplementedError, "backoff_ngram() should never be called, "\
            "since we don't use backoff models"
            
    @staticmethod
    def train(*args, **kwargs):
        """
        We don't train these HMMs using the C{train} method, since our 
        training procedure is not the same as the superclass, so this would 
        be confusing, as this method would require completely different 
        input.
        
        We train our models by initializing in some way (usually hand-setting 
        of parameters), then using Baum-Welch on unlabelled data.
        
        This method will just raise an error.
        
        """
        raise NotImplementedError, "don't use train() to train a ChordClassHmm. "\
            "Instead initialize and then train unsupervisedly"
    
    @classmethod
    def initialize_chord_classes(cls, tetrad_prob, max_notes, grammar, \
            illegal_transitions=[], fixed_root_transitions={}, metric=False):
        """
        Creates a new model with the distributions initialized naively to 
        favour simple chord-types, in a similar way to what R&S do in the paper. 
        
        The transition distribution is initialized so that everything is 
        equiprobable.
        
        @type tetrad_prob: float
        @param tetrad_prob: prob of a note in the tetrad. This prob is 
            distributed over the notes of the tetrad. The remaining prob 
            mass is distributed over the remaining notes. You'll want this 
            to be >0.33, so that tetrad notes are more probable than others.
        @type max_notes: int
        @param max_notes: maximum number of notes that can be generated in 
            each emission. Usually best to set to something high, like 100 - 
            it's just to make the distribution finite.
        @type grammar: L{jazzparser.grammar.Grammar}
        @param grammar: grammar from which to take the chord class definitions
        @type metric: bool
        @param metric: if True, creates a model with a metrical component 
            (dependence on metrical position). Default False
        
        """
        # Only use chord classes that are used by some morph item in the lexicon
        classes = [ccls for ccls in grammar.chord_classes.values() if ccls.used]
        
        # Create a probability distribution for the emission distribution
        dists = {}
        
        # Create the distribution for each possible r-value if we're creating 
        #  a metrical model
        if metric:
            r_vals = range(4)
        else:
            r_vals = [0]
        # Separate emission distribution for each chord class
        for ccls in classes:
            for r in r_vals:
                probabilities = {}
                # We assign two different probabilities: in tetrad or out
                # Don't assume the tetrad has 4 notes!
                in_tetrad_prob = tetrad_prob / len(ccls.notes)
                out_tetrad_prob = (1.0 - tetrad_prob) / (12 - len(ccls.notes))
                # Give a probability to every pitch class
                for d in range(12):
                    if d in ccls.notes:
                        probabilities[d] = in_tetrad_prob
                    else:
                        probabilities[d] = out_tetrad_prob
                dists[(ccls.name,r)] = DictionaryProbDist(probabilities)
        emission_dist = DictionaryConditionalProbDist(dists)
        
        # Take the state labels from the lexical entries in the grammar
        # Include only tonic categories that were generated from lexical 
        #  expansion rules - i.e. only tonic repetition categories
        schemata = grammar.midi_families.keys()
        
        # Check that the transition constraint specifications refer to existing 
        #  schemata
        for labels in illegal_transitions:
            for label in labels:
                if label not in schemata:
                    raise ValueError, "%s, given in illegal transition "\
                        "specification, is not a valid schema in the grammar" \
                        % label
        for labels in fixed_root_transitions:
            for label in labels:
                if label not in schemata:
                    raise ValueError, "%s, given in fixed root transition "\
                        "specification, is not a valid schema in the grammar" \
                        % label
        
        # Build from the grammar a mapping from lexical schemata (POSs) to 
        #  chord classes
        chord_class_mapping = {}
        for morph in grammar.morphs:
            if morph.pos in schemata:
                chord_class_mapping.setdefault(morph.pos, []).append(str(morph.chord_class.name))
        # Make sure that every label appears in the mapping
        for label in schemata:
            if label not in chord_class_mapping:
                chord_class_mapping[label] = []
        
        # Initialize transition distribution so every transition is equiprobable
        schema_transition_counts = ConditionalFreqDist()
        root_transition_counts = ConditionalFreqDist()
        for label0 in schemata:
            for label1 in schemata:
                # Increment the count once for each chord class associated 
                #  with this schema: schemata with 2 chord classes get 2 
                #  counts
                for cclass in chord_class_mapping[label1]:
                    schema_transition_counts[label0].inc(label1)
                    for root_change in range(12):
                        # Give one count to the root transition corresponding to this state transition
                        root_transition_counts[(label0,label1)].inc(root_change)
            # Give a count to finishing in this state
            schema_transition_counts[label0].inc(None)
        # Estimate distribution from this frequency distribution
        schema_trans_dist = ConditionalProbDist(schema_transition_counts, mle_estimator, None)
        root_trans_dist = ConditionalProbDist(root_transition_counts, mle_estimator, None)
        # Sample this to get dictionary prob dists
        schema_trans_dist = cond_prob_dist_to_dictionary_cond_prob_dist(schema_trans_dist)
        root_trans_dist = cond_prob_dist_to_dictionary_cond_prob_dist(root_trans_dist)
        
        # Do the same with the initial states (just schemata, not roots)
        initial_state_counts = FreqDist()
        for label in schemata:
            initial_state_counts.inc(label)
        initial_state_dist = mle_estimator(initial_state_counts, None)
        initial_state_dist = prob_dist_to_dictionary_prob_dist(initial_state_dist)
        
        # Also initialize the notes number distribution to uniform
        emission_number_counts = FreqDist()
        for i in range(max_notes):
            emission_number_counts.inc(i)
        emission_number_dist = mle_estimator(emission_number_counts, None)
        emission_number_dist = prob_dist_to_dictionary_prob_dist(emission_number_dist)
        
        # Create the model
        model = cls(schema_trans_dist, 
                      root_trans_dist, 
                      emission_dist, 
                      emission_number_dist, 
                      initial_state_dist, 
                      schemata, 
                      chord_class_mapping, 
                      classes, 
                      metric=metric, 
                      illegal_transitions=illegal_transitions,
                      fixed_root_transitions=fixed_root_transitions)
        model.add_history(\
            "Initialized model to chord type probabilities, using "\
            "tetrad probability %s. Metric: %s" % \
            (tetrad_prob, metric))
        
        return model
        
    def train_transition_distribution(self, inputs, grammar, contprob=0.3):
        """
        Train the transition distribution parameters in a supervised manner, 
        using chord corpus input.
        
        This is used as an initialization step to set transition parameters 
        before running EM on unannotated data.
        
        @type inputs: L{jazzparser.data.input.AnnotatedDbBulkInput}
        @param inputs: annotated chord training data
        @type contprob: float or string
        @param contprob: probability mass to reserve for staying on the 
            same state (self transitions). Use special value 'learn' to 
            learn the probabilities from the durations
        
        """
        self.add_history(
                "Training transition probabilities using %d annotated chord "\
                "sequences" % len(inputs))
        learn_cont = contprob == "learn"
        
        # Prepare the label sequences that we'll train on
        if learn_cont:
            # Repeat values with a duration > 1
            sequences = []
            for seq in inputs:
                sequence = []
                last_cat = None
                for chord,cat in zip(seq, seq.categories):
                    # Put it in once for each duration
                    for i in range(chord.duration):
                        sequence.append((chord,cat))
                sequences.append(sequence)
        else:
            sequences = [list(zip(sequence, sequence.categories)) for \
                                    sequence in inputs]
        
        # Prepare a list of transformations to apply to the categories
        label_transform = {}
        # First include all the categories we want to keep as they were
        for schema in self.schemata:
            label_transform[schema] = (schema, 0)
        # Then include any transformations the grammar defines
        for pos,mapping in grammar.equiv_map.items():
            label_transform[pos] = (mapping.target.pos, mapping.root)
        
        # Apply the transformation to all the training data
        training_samples = []
        for chord_cats in sequences:
            seq_samples = []
            for chord,cat in chord_cats:
                # Transform the label if it has a transformation
                if cat in label_transform:
                    use_cat, alter_root = label_transform[cat]
                else:
                    use_cat, alter_root = cat, 0
                root = (chord.root + alter_root) % 12
                seq_samples.append((str(use_cat), root))
            training_samples.append(seq_samples)
        
        training_data = sum([
            [(cat0, cat1, (root1 - root0) % 12)
                    for ((cat0,root0),(cat1,root1)) in \
                        group_pairs(seq_samples)] \
                for seq_samples in training_samples], [])
        
        # Count up the observations
        schema_transition_counts = ConditionalFreqDist()
        root_transition_counts = ConditionalFreqDist()
        for (label0, label1, root_change) in training_data:
            # Only use counts for categories the model's looking for
            if label0 in self.schemata and label1 in self.schemata:
                schema_transition_counts[label0].inc(label1)
                root_transition_counts[(label0,label1)].inc(root_change)
        
        # Transition probability to final state (end of sequence)
        for sequence in training_samples:
            # Inc the count of going from the label the sequence ends on to 
            #  the final state
            schema_transition_counts[sequence[-1][0]].inc(None)
            
        # Use Laplace (plus one) smoothing
        # We don't use the laplace_estimator because we want the conversion 
        #  to a dict prob dist to get all the labels, not just to discount 
        #  the ones it's seen
        for label0 in self.schemata:
            for label1 in self.schemata:
                for root_change in range(12):
                    # Exclude self-transition for now, unless we're learning it
                    if learn_cont or not (label0 == label1 and root_change == 0):
                        schema_transition_counts[label0].inc(label1)
                        root_transition_counts[(label0,label1)].inc(root_change)
                # We don't add a count for going to the final state: we don't 
                #  want to initialize it with too much weight
        
        # Estimate distribution from this frequency distribution
        schema_trans_dist = cond_prob_dist_to_dictionary_cond_prob_dist(\
                ConditionalProbDist(schema_transition_counts, mle_estimator, None), \
                    mutable=True, samples=self.schemata+[None])
        root_trans_dist = cond_prob_dist_to_dictionary_cond_prob_dist(\
                ConditionalProbDist(root_transition_counts, mle_estimator, None), \
                    mutable=True, samples=range(12))
        
        if not learn_cont:
            # Discount all probabilities to allow for self-transition probs
            discount = logprob(1.0 - contprob)
            self_prob = logprob(contprob)
            for label0 in self.schemata:
                # Give saved prob mass to self-transitions
                trans_dist[label0].update((label0, 0), self_prob)
                
                # Discount all other transitions to allow for this
                for label1 in self.schemata:
                    for root_change in range(12):
                        if not (label0 == label1 and root_change == 0):
                            # Discount non self transitions
                            trans_dist[label0].update((label1, root_change), \
                                trans_dist[label0].logprob((label1, root_change)) + \
                                discount)
        
        # Recreate the dict prob dist so it's not mutable any more
        schema_trans_dist = cond_prob_dist_to_dictionary_cond_prob_dist(schema_trans_dist)
        root_trans_dist = cond_prob_dist_to_dictionary_cond_prob_dist(root_trans_dist)
        
        ## Now for the initial distribution
        # Count up the observations
        initial_counts = FreqDist()
        for sequence in training_samples:
            initial_counts.inc(sequence[0][0])
        # Use Laplace (plus one) smoothing
        #for label in self.schemata:
        #    initial_counts.inc(label)
        
        # Estimate distribution from this frequency distribution
        initial_dist = prob_dist_to_dictionary_prob_dist(\
                    mle_estimator(initial_counts, None), samples=self.schemata)
        
        # Replace the model's transition distributions
        self.schema_transition_dist = schema_trans_dist
        self.root_transition_dist = root_trans_dist
        self.initial_state_dist = initial_dist
        # Invalidate the cache
        self.clear_cache()
    
    def train_emission_number_distribution(self, inputs):
        """
        Trains the distribution over the number of notes emitted from a 
        chord class. It's not conditioned on the chord class, so the only 
        training data needed is a segmented MIDI corpus.
        
        @type inputs: list of lists
        @param inputs: training data. The same format as is produced by 
            L{jazzparser.taggers.segmidi.midi.midi_to_emission_stream}
        
        """
        self.add_history(
            "Training emission number probabilities using %d MIDI segments"\
            % len(inputs))
        
        emission_number_counts = FreqDist()
        for sequence in inputs:
            for segment in sequence:
                notes = len(segment)
                # There should very rarely be more than the max num of notes
                if notes <= self.max_notes:
                    emission_number_counts.inc(notes)
        
        # Apply simple laplace smoothing
        for notes in range(self.max_notes):
            emission_number_counts.inc(notes)
        
        # Make a prob dist out of this
        emission_number_dist = prob_dist_to_dictionary_prob_dist(\
                    mle_estimator(emission_number_counts, None))
        self.emission_number_dist = emission_number_dist
        
    def transition_log_probability(self, state, previous_state):
        # Look this transition up in the cache
        if (previous_state, state) not in self._transition_cache:
            if state is None:
                # Final state
                # This is represented in the distribution as the schema 
                #  transition to None (and has no dependence on root)
                label,root,cclass = previous_state
                prob = self.schema_transition_dist[label].logprob(None) + \
                        self._schema_prob_scalers[label]
                return prob
            
            if previous_state is None:
                # Initial state: take from a different distribution
                label,root,cclass = state
                # All roots should be equiprobable: divide by 12
                # All chord classes are equiprobable: divide by number of classes
                return self.initial_state_dist.logprob(label) \
                            - math.log(12.0, 2) \
                            - math.log(self.num_chord_classes[label], 2)
                
            # Split up the states
            (label0,root0,cclass),(label1,root1,cclass) = (previous_state, state)
            root_change = (root1 - root0) % 12
            
            # Check whether this is in the list of forbidden transitions
            if (label0,label1) in self.illegal_transitions:
                return float('-inf')
            # Check whether this label transition has a forced root change
            if (label0,label1) in self.fixed_root_transitions:
                # If this is the right root transition, it has probability 1
                if self.fixed_root_transitions[(label0,label1)] == root_change:
                    root_prob = 0.0
                else:
                    # Otherwise the transition has 0 prob
                    return float('-inf')
            else:
                root_prob = self.root_transition_dist[(label0,label1)].logprob(\
                                                                root_change)
            
            # We ignore the chord class, so have to split the probability over 
            #  the possible chord classes in state
            prob = \
                self.schema_transition_dist[label0].logprob(label1) + \
                    self._schema_prob_scalers[label0] + \
                root_prob - \
                    math.log(self.num_chord_classes[label1], 2)
            # Store the probability in the cache for later use
            self._transition_cache[(previous_state,state)] = prob
            return prob
        else:
            return self._transition_cache[(previous_state,state)]
        
    def emission_log_probability(self, emission, state):
        """
        Gives the probability P(emission | label). Returned as a base 2
        log.
        
        The emission should be a list of emitted notes.
        
        Each note should be 
        given as a tuple (pc,beat), where pc is the pitch class of the note 
        and beat is the beat specifier for the metrical model. If the model 
        is non-metric, you may set to beat always to 0, as it will be ignored 
        and assumed to be 0.
        
        """
        # The thickest of all caches, this simply looks to see if we've 
        #  previously computed the prob of exactly the same emission from 
        #  the same state
        cache_key = (tuple(sorted(emission)), state)
        
        if cache_key not in self._emission_cache:
            # Condition the emission probs only on the chord class (and root)
            label, root, chord_class = state
            # Get P(emission | chord_class, root)
            prob = self.chord_class_emission_log_probability(emission, 
                                                         chord_class, 
                                                         root)
            self._emission_cache[cache_key] = prob
        return self._emission_cache[cache_key]
        
    def chord_class_emission_log_probability(self, emission, chord_class, root):
        """
        The standard emission probability is P(emission | state). This instead 
        returns P(emission | chord class). The emission is given in the same 
        way as to L{emission_log_probability}.
        
        The root number is also required. For L{emission_log_probability}, 
        this is included in the state label.
        
        """
        # Prepare the emissions
        # We sort them so that they can be used as a cache key
        if not self.metric:
            # If this is a non-metric model, we always set beat to 0 to 
            #  ignore it
            notes = sorted([((pc-root) % 12, 0) for (pc,beat) in emission])
        else:
            # Otherwise, we use the given beat value
            notes = sorted([((pc-root) % 12, beat) for (pc,beat) in emission])
        
        # See if we have this emission in the cache
        # This takes advantage of the fact that the same emission will be 
        #  looked up several times for each chord class
        cache_key = (chord_class,tuple(notes))

        if cache_key not in self._emission_class_cache:
            prob = 0.0
            for beat in self.r_values:
                # Get the notes that occur in this beat
                beat_notes = [rel_pc for (rel_pc,notebeat) in notes \
                                if notebeat == beat]
                # Get the probability of generating this number of notes
                prob += self.emission_number_dist.logprob(len(beat_notes))
                # Compute the probability of generating the notes given this 
                #  chord class
                # Take the product of the probability for each note in the set
                for rel_pc in beat_notes:
                    prob += self.emission_dist[(chord_class,beat)].logprob(rel_pc)
            self._emission_class_cache[cache_key] = prob
        else:
            prob = self._emission_class_cache[cache_key]
        return prob
    
    def forward_log_probabilities(self, sequence, normalize=True, array=False):
        """We override this to provide a faster implementation.
        
        It might also be possible to speed up the superclass' implementation 
        using numpy, but it's easier here because we know we're using an 
        HMM, not a higher-order ngram.
        
        This is based on the fwd prob calculation in NLTK's HMM implementation.
        
        @type array: bool
        @param array: if True, returns a numpy 2d array instead of a list of 
            dicts.
        
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
                    
        if not array:
            # Convert this into a list of dicts
            matrix = []
            for t in range(T):
                timestep = {}
                for (i,label) in enumerate(self.label_dom):
                    timestep[label] = alpha[t,i]
                matrix.append(timestep)
            return matrix
        else:
            return alpha
    
    def backward_log_probabilities(self, sequence, normalize=True, array=False):
        """We override this to provide a faster implementation.
        
        @see: forward_log_probability
        
        @type array: bool
        @param array: if True, returns a numpy 2d array instead of a list of 
            dicts.
        
        """
        T = len(sequence)
        N = len(self.label_dom)
        beta = numpy.zeros((T, N), numpy.float64)
        
        # Initialize with the probabilities of transitioning to the final state
        for i,si in enumerate(self.label_dom):
            beta[T-1, i] = self.transition_log_probability(None, si)
        
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
                    
        if not array:
            # Convert this into a list of dicts
            matrix = []
            for t in range(T):
                timestep = {}
                for (i,label) in enumerate(self.label_dom):
                    timestep[label] = beta[t,i]
                matrix.append(timestep)
            return matrix
        else:
            return beta
    
    
    def normal_forward_probabilities(self, sequence, array=False):
        """If you want the normalized matrix of forward probabilities, it's 
        ok to use normal (non-log) probabilities and these can be computed 
        more quickly, since you don't need to sum logs (which is time 
        consuming).
        
        Returns the matrix, and also the vector of values that each timestep 
        was divided by to normalize (i.e. total probability of each timestep 
        over all states).
        Also returns the total log probability of the sequence.
        
        @type array: bool
        @param array: if True, returns a numpy 2d array instead of a list of 
            dicts.
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
        total = array_sum(alpha[0,:])
        alpha[0,:] /= total
        scale[0] = total
        
        # Iterate over the other timesteps
        for t in range(1, T):
            for j,sj in enumerate(self.label_dom):
                # Multiply each previous state's prob by the transition prob 
                #  to this state and sum them all together
                prob = sum(
                    (alpha[t-1, i] * self.transition_probability(sj, si) \
                        for i,si in enumerate(self.label_dom)), 0.0)
                # Also multiply this by the emission probability
                alpha[t, j] = prob * \
                                self.emission_probability(sequence[t], sj)
            # Normalize by dividing all values by the total probability
            total = array_sum(alpha[t,:])
            alpha[t,:] /= total
            scale[t] = total
        
        # Multiply together the probability of each timestep to get the whole 
        # probability of the sequence
        # This gets the same result as if we did:
        #  alpha = model.forward_log_probabilities(sequence, normalize=False, array=True)
        #  log_prob = sum_logs(alpha[T-1,:])
        log_prob = sum((logprob(total) for total in scale), 0.0)
        
        if not array:
            # Convert this into a list of dicts
            matrix = []
            for t in range(T):
                timestep = {}
                for (i,label) in enumerate(self.label_dom):
                    timestep[label] = alpha[t,i]
                matrix.append(timestep)
            return matrix,scale,log_prob
        else:
            return alpha,scale,log_prob
    
    def normal_backward_probabilities(self, sequence, array=False):
        """
        @see: normal_forward_probabilities
        
        (except that this doesn't return the logprob)
        
        @type array: bool
        @param array: if True, returns a numpy 2d array instead of a list of 
            dicts.
        
        """
        T = len(sequence)
        N = len(self.label_dom)
        beta = numpy.zeros((T, N), numpy.float64)
        scale = numpy.zeros(T, numpy.float64)
        
        # Initialize with the probabilities of transitioning to the final state
        for i,si in enumerate(self.label_dom):
            beta[T-1, i] = self.transition_probability(None, si)
        # Normalize
        total = array_sum(beta[T-1, :])
        beta[T-1,:] /= total
        
        # Initialize
        scale[T-1] = total
        
        # Iterate backwards over the other timesteps
        for t in range(T-2, -1, -1):
            # To speed things up, calculate all the t+1 emission probabilities 
            #  first, instead of calculating them all for every t state
            em_probs = [
                self.emission_probability(sequence[t+1], sj) \
                    for sj in self.label_dom]
            
            for i,si in enumerate(self.label_dom):
                # Multiply each next state's prob by the transition prob 
                #  from this state to that and the emission prob in that next 
                #  state
                beta[t, i] = sum(
                    (beta[t+1, j] * self.transition_probability(sj, si) * \
                        em_probs[j] \
                            for j,sj in enumerate(self.label_dom)), 0.0)
            # Normalize by dividing all values by the total probability
            total = array_sum(beta[t,:])
            beta[t,:] /= total
            scale[t] = total
            
        if not array:
            # Convert this into a list of dicts
            matrix = []
            for t in range(T):
                timestep = {}
                for (i,label) in enumerate(self.label_dom):
                    timestep[label] = beta[t,i]
                matrix.append(timestep)
            return matrix,scale
        else:
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
            forward = self.normal_forward_probabilities(sequence, array=True)[0]
        if backward is None:
            backward = self.normal_backward_probabilities(sequence, array=True)[0]
        # T is the number of timesteps
        # N is the number of states
        T,N = forward.shape
        
        # Multiply forward and backward elementwise to get unnormalised gamma
        gamma = forward * backward
        # Sum the values in each timestep to get the normalizing denominator
        denominators = array_sum(gamma, axis=1)
        # Divide all the values in each timestep by each denominator
        gamma = (gamma.transpose() / denominators).transpose()
        
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
            forward = self.normal_forward_probabilities(sequence, array=True)
        if backward is None:
            backward = self.normal_backward_probabilities(sequence, array=True)
        # T is the number of timesteps
        # N is the number of states
        T,N = forward.shape
        
        xi = zeros((T-1,N,N), float64)
        for t in range(T-1):
            total = 0.0
            # To avoid getting the same em prob many times, precompute the 
            #  emission probs for all states at the next time step
            em_probs = [
                self.emission_probability(sequence[t+1], statej) \
                    for statej in self.label_dom]
            
            # For each first state
            for i,statei in enumerate(self.label_dom):
                # and each second state
                for j,statej in enumerate(self.label_dom):
                    # get the probability of this pair of states given the emissions
                    prob = forward[t][i] * backward[t+1][j] * \
                            self.transition_probability(statej, statei) * \
                            em_probs[j]
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
            'schema_transition_dist' : object_to_dict(self.schema_transition_dist),
            'root_transition_dist' : object_to_dict(self.root_transition_dist),
            'emission_dist' : object_to_dict(self.emission_dist),
            'emission_number_dist' : object_to_dict(self.emission_number_dist),
            'initial_state_dist' : object_to_dict(self.initial_state_dist),
            'schemata' : self.schemata,
            'history' : self.history,
            'description' : self.description,
            'chord_class_mapping' : self.chord_class_mapping,
            'chord_classes' : self.chord_classes,
            'illegal_transitions' : self.illegal_transitions,
            'fixed_root_transitions' : self.fixed_root_transitions,
        }
        
    @classmethod
    def from_picklable_dict(cls, data):
        """
        Reproduces an n-gram model that was converted to a picklable 
        form using to_picklable_dict.
        
        """
        from jazzparser.utils.nltk.storage import dict_to_object
        return cls(dict_to_object(data['schema_transition_dist']),
                    dict_to_object(data['root_transition_dist']),
                    dict_to_object(data['emission_dist']),
                    dict_to_object(data['emission_number_dist']),
                    dict_to_object(data['initial_state_dist']),
                    data['schemata'],
                    data['chord_class_mapping'],
                    data['chord_classes'],
                    history=data.get('history', ''),
                    description=data.get('description', ''),
                    illegal_transitions=data.get('illegal_transitions', []),
                    fixed_root_transitions=data.get('fixed_root_transitions', {}))
