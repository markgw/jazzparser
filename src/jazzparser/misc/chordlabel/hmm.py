"""An HMM midi chord labeler.

An HMM midi chord labeler based on the audio chord labeler of Ni, Mcvicar, 
Santos-Rodriguez and De Bie, MIREX 2011, Harmony Progression (HP).

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

import numpy, os, re, math
from datetime import datetime
from numpy import ones, float64, sum as array_sum, zeros
import cPickle as pickle

from jazzparser.utils.nltk.ngram import DictionaryHmmModel
from jazzparser.utils.nltk.probability import logprob, add_logs, \
                        sum_logs, prob_dist_to_dictionary_prob_dist, \
                        cond_prob_dist_to_dictionary_cond_prob_dist, \
                        prob_dist_to_dictionary_prob_dist, mle_estimator, \
                        laplace_estimator
from jazzparser.utils.options import ModuleOption, choose_from_list, new_file_option
from jazzparser.utils.strings import str_to_bool
from jazzparser import settings
from jazzparser.data.input import detect_input_type, \
                        MidiTaggerTrainingBulkInput, DbBulkInput
from jazzparser.data.parsing import keys_for_sequence
from jazzparser.utils.loggers import create_dummy_logger

from nltk.probability import ConditionalProbDist, FreqDist, \
            ConditionalFreqDist, DictionaryProbDist, \
            DictionaryConditionalProbDist, MutableProbDist

from .chord_vocabs import CHORD_VOCABS, get_mapping
from .midi import midi_to_emission_stream
from .data import ChordLabel
from .baumwelch import HPBaumWelchTrainer
from . import ModelTrainError, ModelLoadError

FILE_EXTENSION = "mdl"

class HPChordLabeler(DictionaryHmmModel):
    """
    HMM based on that of I{Harmony Progression Analyzer for MIREX 2011}, by 
    Ni, Mcvicar, Santos-Rodriguez, De Bie. Their audio labeling model is 
    here adapted to MIDI labeling.
    
    The state labels are triples: C{(key,root,label)}. C{key} is the ET key 
    (C=0, C#=1, etc). C{root} is the chord root: e.g. C{root=7} denotes chord 
    root G. The chord root is not relative to the key, though the probabilities 
    stored in the distributions are.
    
    """
    TRAINING_OPTIONS = [
        # Initialization options
        ModuleOption('chordprob', filter=float,
            help_text="Initialization of the emission distribution.",
            usage="ccprob=P, P is a probability. Prob P is distributed "\
                "over the pitch classes that are in the chord.",
            required=True),
        ModuleOption('maxnotes', filter=int,
            help_text="Maximum number of notes that can be generated from a "\
                "a state. Limit is required to make the distribution finite.",
            usage="maxnotes=N, N is an integer",
            default=100),
        ModuleOption('vocab', filter=choose_from_list(CHORD_VOCABS.keys()),
            help_text="Chord vocabulary for the model to use",
            usage="vocab=V, V is one of %s" % ", ".join("'%s'" % v for v in CHORD_VOCABS.keys()),
            required=True),
        ModuleOption('split', filter=int, 
            help_text="Limits the length of midi inputs by splitting them into "\
                "fragments of at most this length.",
            usage="split=X, where X is an int"),
        ModuleOption('truncate', filter=int, 
            help_text="Limits the length of midi inputs by truncating them to "\
                "this number of timesteps. Truncation is applied before "\
                "splitting.",
            usage="truncate=X, where X is an int"),
    ] + HPBaumWelchTrainer.OPTIONS
    LABELING_OPTIONS = [
        ModuleOption('n', filter=int, 
            help_text="Number of best labels to consider for each timestep",
            usage="decoden=N, where N is an integer",
            default=10),
        ModuleOption('nokey', filter=str_to_bool, 
            help_text="Don't distinguish between keys: removed labels that  "\
                "are duplicate if you ignore their key and return all chords "\
                "with a key of 0. Probabilities are not summed: only the "\
                "highest is returned",
            usage="nokey=B, where B is 'true' or 'false'",
            default=False),
        ModuleOption('viterbi', filter=str_to_bool, 
            help_text="Use Viterbi decoding, instead of forward-backward. Only "\
                "one label will be returned for each chord, but it's likey "\
                "to be a more coherent sequence",
            usage="viterbi=B, where B is 'true' or 'false'",
            default=False),
    ]
    
    def __init__(self, initial_key_dist, initial_chord_dist, 
                    key_transition_dist, chord_transition_dist, 
                    emission_dist, note_number_dist, 
                    chord_vocab, max_notes, chord_corpus_mapping, 
                    history="", description="", name="default"):
        self.order = 2
        self.backoff_model = None
        
        self.emission_dom = range(12)
        self.num_emissions = 12
        self.chord_vocab = chord_vocab
        self.chord_types = list(sorted(chord_vocab.keys()))
        self.chord_corpus_mapping = chord_corpus_mapping
        # Possible chord tags (root and label)
        self.chord_dom = [(root,label) for root in range(12) \
                                       for label in self.chord_types]
        self.label_dom = [(key,root,label) for key in range(12) \
                                           for root in range(12) \
                                           for label in self.chord_types]
        self.num_labels = len(self.label_dom)
        
        self.initial_key_dist = initial_key_dist
        self.initial_chord_dist = initial_chord_dist
        self.key_transition_dist = key_transition_dist
        self.chord_transition_dist = chord_transition_dist
        self.note_number_dist = note_number_dist
        self.emission_dist = emission_dist
        self.max_notes = max_notes
        
        # Store a string with information about training, etc
        self.history = history
        # Store another string with an editable description
        self.description = description
        
        self.model_name = name
        
        # Initialize the various caches
        # These will be filled as we access probabilities
        self.clear_cache()
    
    def copy(self, mutable=False):
        """
        Creates a complete copy of the model, optionally making the 
        distributions mutable.
        
        """
        # Copy all the distributions
        initial_key_dist = prob_dist_to_dictionary_prob_dist(
                            self.initial_key_dist, mutable=mutable)
        initial_chord_dist = prob_dist_to_dictionary_prob_dist(
                            self.initial_chord_dist, mutable=mutable)
        key_transition_dist = prob_dist_to_dictionary_prob_dist(
                            self.key_transition_dist, mutable=mutable)
        chord_transition_dist = cond_prob_dist_to_dictionary_cond_prob_dist(
                            self.chord_transition_dist, mutable=mutable)
        emission_dist = cond_prob_dist_to_dictionary_cond_prob_dist(
                            self.emission_dist, mutable=mutable)
        note_number_dist = prob_dist_to_dictionary_prob_dist(
                            self.note_number_dist, mutable=mutable)
        
        return HPChordLabeler(initial_key_dist, 
                              initial_chord_dist,
                              key_transition_dist,
                              chord_transition_dist,
                              emission_dist,
                              note_number_dist, 
                              self.chord_vocab, 
                              self.max_notes,
                              self.chord_corpus_mapping, 
                              history = self.history,
                              description = self.description,
                              name = self.model_name)
        
    def clear_cache(self):
        """
        Initializes or empties probability distribution caches.
        
        Make sure to call this if you change or update the distributions.
        
        No caches used thus far, so this does nothing for now, except call 
        the super method.
        
        """
        self._small_transition_matrix_cache = None
        self._small_transition_matrix_cache_trans = None
        return DictionaryHmmModel.clear_cache(self)
        
    def add_history(self, string):
        """ Adds a line to the end of this model's history string. """
        self.history += "%s: %s\n" % (datetime.now().isoformat(' '), string)
    
    def get_mapping_to_corpus(self):
        """
        Returns a dict mapping the labels of this model's vocabulary to the 
        chord types of the chord corpus.
        
        """
        return get_mapping(self.chord_corpus_mapping, reverse=True)
        
    def get_mapping_from_corpus(self):
        """
        Returns a dict mapping the chord types of the chord corpus to this 
        model's chord labels.
        
        """
        return get_mapping(self.chord_corpus_mapping)
    
    def map_to_corpus(self, sequence):
        """
        Postprocesses the sequence, which should be a sequence in the form 
        it comes out from the labeler, to apply the corpus mapping associated 
        with this labeler. The result should be a chord sequence that uses 
        the chord corpus chord types.
        
        """
        mapping = self.get_mapping_to_corpus()
        labels = [
            [(ChordLabel(lab.root, mapping[lab.label], lab.key), prob) \
                for (lab,prob) in chords] \
                    for chords in sequence]
        return labels
    
    @classmethod
    def initialize_chords(cls, chord_prob, max_notes, chord_vocab, 
                                                chord_mapping, name="default"):
        """
        Creates a new model with the distributions initialized naively to 
        favour simple chord-types, in a similar way to what R&S do in their 
        paper. 
        
        The transition distributions are initialized so that everything is 
        equiprobable.
        
        @type chord_prob: float
        @param chord_prob: prob of a note in the chord. This prob is 
            distributed over the notes of the chord. The remaining prob 
            mass is distributed over the remaining notes. You'll want this 
            to be big enough that chord notes are more probable than others.
        @type max_notes: int
        @param max_notes: maximum number of notes that can be generated in 
            each emission. Usually best to set to something high, like 100 - 
            it's just to make the distribution finite.
        @type chord_vocab: dict
        @param chord_vocab: a vocabularly of chord types. Mapping from string 
            chord labels to a list of ints representing the notes, relative 
            to the root that are contained in the chord.
        
        """
        # Condition emission distribution on chord label
        dists = {}
        for label,chord in chord_vocab.items():
            probs = {}
            for note in range(12):
                if note in chord:
                    # Assign the share of the chord prob to this note
                    probs[note] = chord_prob / len(chord)
                else:
                    # Assign a share of the remaining prob to this
                    probs[note] = (1.0 - chord_prob) / (12 - len(chord))
            dists[label] = DictionaryProbDist(probs)
        emission_dist = DictionaryConditionalProbDist(dists)
        
        # Work out the state label domain
        label_dom = [(key,root,label) for key in range(12) \
                                      for root in range(12) \
                                      for label in list(sorted(chord_vocab.keys()))]
        # Create all the distributions that will be uniform
        initial_key_probs = {}
        key_transition_probs = {}
        initial_chord_probs = {}
        chord_transition_probs = {}
        # Initialize transition distributions so every transition is equiprobable
        for pitch in range(12):
            # Each initial key (0-12) is equiprobable
            initial_key_probs[pitch] = 1.0/12
            # Each key transition (0-12) is equiprobable
            key_transition_probs[pitch] = 1.0/12
            # Each pair of chord label and root, relative to key, is equiprobable
            num_chords = 12*len(chord_vocab)
            for label in chord_vocab:
                initial_chord_probs[(pitch,label)] = 1.0/num_chords
                # Each chord transition is equiprobable
                chord_transition_probs[(pitch,label)] = 1.0/(num_chords+1)
            # Include the transition to the final state
            chord_transition_probs[None] = 1.0/(num_chords+1)
        
        initial_key_dist = DictionaryProbDist(initial_key_probs)
        key_transition_dist = DictionaryProbDist(key_transition_probs)
        initial_chord_dist = DictionaryProbDist(initial_chord_probs)
        
        # Use the same (uniform) chord distribution for each previous chord
        chord_transition_dists = {}
        for pitch in range(12):
            for label in chord_vocab:
                chord_transition_dists[(pitch,label)] = DictionaryProbDist(
                                                chord_transition_probs.copy())
        chord_transition_dist = DictionaryConditionalProbDist(
                                                        chord_transition_dists)
        
        # Also initialize the notes number distribution to uniform
        note_number_prob = 1.0 / max_notes
        note_number_probs = {}
        for i in range(max_notes):
            note_number_probs[i] = note_number_prob
        note_number_dist = DictionaryProbDist(note_number_probs)
        
        # Create the model
        model = cls(initial_key_dist,
                    initial_chord_dist, 
                    key_transition_dist, 
                    chord_transition_dist, 
                    emission_dist, 
                    note_number_dist, 
                    chord_vocab,
                    max_notes,
                    chord_mapping, 
                    name=name)
        model.add_history(\
            "Initialized model to chord type probabilities, using "\
            "chord probability %s" % chord_prob)
        return model
        
    def train_transition_distribution(self, inputs, input_keys, 
                                                            chord_mapping=None):
        """
        Train the transition distribution parameters in a supervised manner, 
        using chord corpus input.
        
        This is used as an initialization step to set transition parameters 
        before running EM on unannotated data.
        
        @type inputs: L{jazzparser.data.input.AnnotatedDbBulkInput}
        @param inputs: annotated chord training data
        @type input_keys: list of lists of ints
        @param input_keys: the key associated with each chord. Should contain 
            a key list for each input sequence and each should be the length 
            of the chord sequence
        @type chord_mapping: dict
        @param chord_mapping: a mapping from the chord labels of the corpus to 
            those we will use for this model, so that we can use the training 
            data. See L{jazzparser.misc.chordlabel.chord_vocabs} for mappings 
            and use C{get_mapping} to prepare a dict from them. This doesn't 
            have to be the same as the mapping stored in the model 
            (C{model.chord_corpus_mapping}) and won't overwrite it. If not 
            given, the model's corpus mapping will be used
        
        """
        self.add_history(
                "Training transition probabilities using %d annotated chord "\
                "sequences" % len(inputs))
        
        if chord_mapping is None:
            chord_mapping = self.get_mapping_from_corpus()
        
        # Prepare the label sequences that we'll train on
        sequences = []
        for seq in inputs:
            sequence = []
            for chord in seq.chords:
                sequence.append((chord.root, chord.type, chord.duration))
            sequences.append(sequence)
        
        # Apply the mapping to the chord data
        sequences = [ \
            [(root, chord_mapping.get(label, label), duration) for \
                (root, label, duration) in sequence] for sequence in sequences]
        
        # Repeat values with a duration > 1
        rep_sequences = []
        for seq in sequences:
            sequence = []
            for root,label,duration in seq:
                # Put it in once for each duration
                for i in range(duration):
                    sequence.append((root,label))
            rep_sequences.append(sequence)
        
        # Count up the observations
        initial_chord_counts = FreqDist()
        key_transition_counts = FreqDist()
        chord_transition_counts = ConditionalFreqDist()
        
        for sequence,seq_keys in zip(rep_sequences, input_keys):
            # Count the initial events
            root0, label0 = sequence[0]
            key0 = seq_keys[0][1]
            initial_chord_counts.inc(((root0-key0)%12,label0))
            # Don't count the initial key distribution: leave that uniform
            
            last_relroot = (root0 - key0) % 12
            last_label = label0
            last_key = key0
            
            for (root,label),(chord,key) in zip(sequence[1:], seq_keys[1:]):
                key_change = (key - last_key) % 12
                key_transition_counts.inc(key_change)
                
                # Take the root relative to the key we're in
                relroot = (root-key) % 12
                chord_transition_counts[(last_relroot,last_label)].inc(\
                                                            (relroot,label))
                
                last_key = key
                last_relroot = relroot
                last_label = label
            # Note the transition to the final state from this last state
            chord_transition_counts[(last_relroot,last_label)].inc(None)
        
        # Build the correct domains of these distributions
        possible_chords = [(root,label) for root in range(12) for label in \
                                        list(sorted(self.chord_vocab.keys()))]
        
        # Estimate the prob dists from these counts
        initial_chord_dist = prob_dist_to_dictionary_prob_dist(\
                                laplace_estimator(initial_chord_counts, \
                                        len(possible_chords)),
                                    samples=possible_chords)
        key_transition_dist = prob_dist_to_dictionary_prob_dist(\
                                laplace_estimator(key_transition_counts, 12),
                                    samples=range(12))
        chord_transition_dist = cond_prob_dist_to_dictionary_cond_prob_dist(\
                                ConditionalProbDist(chord_transition_counts,
                                    laplace_estimator, len(possible_chords)+1),
                                        conditions=possible_chords,
                                        samples=possible_chords+[None])
        
        # Replace the model's transition distributions
        self.initial_chord_dist = initial_chord_dist
        self.key_transition_dist = key_transition_dist
        self.chord_transition_dist = chord_transition_dist
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
    
    @staticmethod
    def train(data, name, logger=None, options={}, chord_data=None):
        """
        Initializes and trains an HMM in a supervised fashion using the given 
        training data.
        
        """
        if len(data) == 0:
            raise ModelTrainError, "empty training data set"
            
        # Prepare a dummy logger if none was given
        if logger is None:
            logger = create_dummy_logger()
        
        # Process the options dict
        options = HPChordLabeler.process_training_options(options)
        
        # Work out what kind of input data we've got
        # It should be a bulk input type: check what type the first input is
        input_type = detect_input_type(data[0], allowed=['segmidi', 'db-annotated'])
        
        logger.info(">>> Beginning training of HP chord labeler model '%s'" % name)
        # If we got midi tagger training data, it may include chord data as well
        if isinstance(data, MidiTaggerTrainingBulkInput) and \
                                                data.chords is not None:
            if chord_data is None:
                # Use the chord data in the input data
                logger.info("Midi training data; chord corpus data available")
                chord_inputs = data.chords
            else:
                # Use the chord data that was given explicitly
                chord_inputs = chord_data
            midi_inputs = data
        elif isinstance(data, DbBulkInput):
            logger.info("Only chord corpus training data")
            # This was only chord input, no midi data
            chord_inputs = data
            midi_inputs = None
        else:
            chord_inputs = chord_data
            # Presumably this is another form of midi training data
            midi_inputs = data
            logger.info("Midi training data; no chord data was included")
        
        # Get the chord vocab from the options
        logger.info("Model chord vocabulary: %s" % options['vocab'])
        vocab, vocab_mapping = CHORD_VOCABS[options['vocab']]
        
        # Initialize a model according to the chord types
        logger.info("Initializing emission distributions to favour chord "\
                    "notes with chord probability %s" % (options['chordprob']))
        model = HPChordLabeler.initialize_chords(options['chordprob'], \
                                            options['maxnotes'], vocab, \
                                            vocab_mapping, name=name)
        
        # If we have chord training data, use this to train the transition dist
        if chord_inputs is not None:
            logger.info("Training using chord data")
            
            # Construct the trees implicit in the annotations to get the 
            #  key of every chord
            logger.info("Preparing key data for annotated chord sequences")
            input_keys = [keys_for_sequence(dbinput) for dbinput in chord_inputs]
            
            # Run the supervised training of the transition distribution
            logger.info("Training transition distribution on chord sequences")
            model.train_transition_distribution(chord_inputs, input_keys)
            
        if midi_inputs is not None:
            logger.info("Training using midi data")
            
            # Preprocess the midi inputs so they're ready for the model training
            emissions = [midi_to_emission_stream(seq, 
                                                 remove_empty=False)[0] \
                            for seq in midi_inputs]
            
            # Use the midi data to train emission number dist
            logger.info("Training emission number distribution")
            model.train_emission_number_distribution(emissions)
            
            ####### EM unsupervised training on the midi data
            # Pull out the options to pass to the trainer
            # These are a subset of the model training options
            bw_opt_names = [opt.name for opt in HPBaumWelchTrainer.OPTIONS]
            bw_opts = dict([(name,val) for (name,val) in options.items() \
                                            if name in bw_opt_names])
            # Create a Baum-Welch trainer
            trainer = HPBaumWelchTrainer(model, bw_opts)
            # Do the Baum-Welch training
            model = trainer.train(emissions, logger=logger)
        logger.info("Training complete")
        
        return model
    
    
    ################## Probabilities ###################
    def transition_log_probability(self, state, previous_state):
        if state is None:
            # Final state
            # This is represented in the distribution as the chord 
            #  transition to None (and has no dependence on root)
            key0,root0,label0 = previous_state
            chord_root = (root0-key0) % 12
            return self.chord_transition_dist[(chord_root,label0)].logprob(None)
        
        if previous_state is None:
            # Initial state: take from a different distribution
            key,root,label = state
            chord_root = (root-key) % 12
            return self.initial_chord_dist.logprob((chord_root,label)) + \
                    self.initial_key_dist.logprob(key)
            
        # Split up the states
        (key0,root0,label0),(key1,root1,label1) = (previous_state, state)
        key_change = (key1 - key0) % 12
        chord_root0 = (root0-key0) % 12
        chord_root1 = (root1-key1) % 12
        
        # Multiply together the probability of the key change and the chord 
        #  transition
        key_prob = self.key_transition_dist.logprob(key_change)
        chord_prob = self.chord_transition_dist[(chord_root0,label0)].logprob(\
                                                        (chord_root1,label1))
        
        return key_prob + chord_prob
        
    def emission_log_probability(self, emission, state):
        """
        Gives the probability P(emission | label). Returned as a base 2
        log.
        
        The emission should be a list of emitted notes as integer pitch classes.
        
        """
        # Condition the emission probs only on the chord class (and root)
        key, root, label = state
        
        # Get the probability of generating this number of notes
        prob = self.note_number_dist.logprob(len(emission))
        
        # Multiply together the probabilities of each note
        for note in emission:
            # Take the note relative to the chord root
            pc = (note - root) % 12
            prob += self.emission_dist[label].logprob(pc)
        
        return prob
    
    def get_emission_matrix(self, sequence):
        """
        We override this to make it faster by taking advantage of where we 
        know states share probabilities
        
        """
        T = len(sequence)
        N = len(self.label_dom)
        
        ems = numpy.zeros((T, N), numpy.float64)
        
        # Set the probability for every timestep...
        for t,emission in enumerate(sequence):
            # Compute the emission probability for each root/label combo
            # We know that the key makes no difference to this
            chord_ems = {}
            for root in range(12):
                for label in self.chord_vocab:
                    chord_ems[(root,label)] = \
                        self.emission_probability(emission, (0,root,label))
            # ...given each state
            for i,(key,root,label) in enumerate(self.label_dom):
                ems[t,i] = chord_ems[(root,label)]
        return ems
    
    def get_small_emission_matrix(self, sequence):
        """
        Instead of building the emission matrix for every state, just 
        includes probabilities for (root,label) pairs, decomposed into 
        2 dimensions. This is useful for the forward-backward calculations.
        
        """
        ems = numpy.zeros((len(sequence), 12, len(self.chord_types)), numpy.float64)
        # Set the probability for every timestep...
        for t,emission in enumerate(sequence):
            # Compute the emission probability for each root/label combo
            # We know that the key makes no difference to this
            chord_ems = {}
            for root in range(12):
                for c,label in enumerate(self.chord_types):
                    ems[t,root,c] = \
                        self.emission_probability(emission, (0,root,label))
        return ems
        
    def get_small_transition_matrix(self, transpose=False):
        """
        Decomposed version of just the chord part of the transition 
        probabilities, for forward-backward calculations.
        
        """
        if transpose:
            if self._small_transition_matrix_cache_trans is None:
                # Compute the matrix from scratch, as we've not done it yet
                C = len(self.chord_types)
                chords = self.chord_types
                trans = numpy.zeros((12,12,C,12,12,C), numpy.float64)
                
                # Fill the matrix
                for key0 in range(12):
                    for root0 in range(12):
                        for c0,chord0 in enumerate(chords):
                            for key1 in range(12):
                                for root1 in range(12):
                                    for c1,chord1 in enumerate(chords):
                                        trans[key0, root0, c0, \
                                              key1, root1, c1] = \
                                                self.transition_probability(
                                                    (key1,root1,chord1), 
                                                    (key0,root0,chord0))
                
                self._small_transition_matrix_cache_trans = trans
            return self._small_transition_matrix_cache_trans
        else:
            if self._small_transition_matrix_cache is None:
                # Compute the matrix from scratch, as we've not done it yet
                C = len(self.chord_types)
                chords = self.chord_types
                trans = numpy.zeros((12,12,C,12,12,C), numpy.float64)
                
                # Fill the matrix
                for key0 in range(12):
                    for root0 in range(12):
                        for c0,chord0 in enumerate(chords):
                            for key1 in range(12):
                                for root1 in range(12):
                                    for c1,chord1 in enumerate(chords):
                                        trans[key1, root1, c1, \
                                              key0, root0, c0] = \
                                                self.transition_probability(
                                                    (key1,root1,chord1), 
                                                    (key0,root0,chord0))
                
                self._small_transition_matrix_cache = trans
            return self._small_transition_matrix_cache
    
    def normal_forward_probabilities(self, sequence, seq_prob=False, decomposed=False):
        """
        Specialized version of this to make it faster.
        
        @note: verified that this gets identical results to the superclass
        
        @param seq_prob: return the log probability of the whole sequence 
            as well as the array (tuple of (array,logprob)).
        @return: 2D Numpy array.
            The first dimension represents timesteps, the second the states.
        
        """
        from numpy import newaxis
        N = len(sequence)
        states = self.label_dom
        S = len(states)
        chords = self.chord_types
        C = len(chords)
        
        # Prepare the transition and emission matrices
        ems = self.get_small_emission_matrix(sequence)
        trans = self.get_small_transition_matrix()
        # Initialize an empty matrix
        # The dims of the matrix are (time, key, root, label)
        forward_matrix = numpy.zeros((N,12,12,C), numpy.float64)
        # Create an array for the total logprobs
        coefficients = numpy.zeros((N,), numpy.float64)
        
        # First fill in the first columns with transitions from None
        for root in range(12):
            for c,chord in enumerate(chords):
                for key in range(12):
                    # Fill in with the (None-padded) transition probability
                    forward_matrix[0,key,root,c] = self.transition_probability(
                                                    (key,root,chord), None)
        # Multiply in the emission probabilities
        # These get broadcast over the last dim, key
        forward_matrix[0] = forward_matrix[0] * ems[0]
        # Normalize
        coefficients[0] = logprob(numpy.sum(forward_matrix[0]))
        forward_matrix[0] /= numpy.sum(forward_matrix[0])
        
        for time in range(1, N):
            # Multiply in the transition matrix to get the new state probabilities
            trans_step = forward_matrix[time-1] * trans
            # DIMS: key, root, label, key[-1], root[-1], label[-1]
            for i in range(3):
                # Sum over previous states
                trans_step = numpy.sum(trans_step, axis=-1)
            # Multiply in the emission probabilities
            # This broadcasts over keys, since emissions don't care about key
            forward_matrix[time] = trans_step * ems[time]
            # Normalize the timestep
            coefficients[time] = logprob(numpy.sum(forward_matrix[time]))
            forward_matrix[time] /= numpy.sum(forward_matrix[time])
        
        if not decomposed:
            # Reshape the array so it has only two dimensions
            # The dimensions are ordered in the same way as the components of the 
            #  labels, so we just reshape
            forward_matrix = forward_matrix.reshape(N, 12*12*C)
        
        if seq_prob:
            return forward_matrix, numpy.sum(coefficients)
        else:
            return forward_matrix
    
    def normal_backward_probabilities(self, sequence, decomposed=False):
        """
        Specialized version of this to make it faster.
        
        @note: verified that this gets identical results to the superclass
        
        @param seq_prob: return the log probability of the whole sequence 
            as well as the array (tuple of (array,logprob)).
        @return: 2D Numpy array.
            The first dimension represents timesteps, the second the states.
        
        """
        N = len(sequence)
        states = self.label_dom
        chords = self.chord_types
        C = len(chords)
        
        # Prepare the transition and emission matrices
        trans_back = self.get_small_transition_matrix(transpose=True)
        ems = self.get_small_emission_matrix(sequence)
        # Initialize an empty matrix
        backward_matrix = numpy.zeros((N,12,12,C), numpy.float64)
        
        # First fill in the last column with transitions to None
        for root in range(12):
            for c,chord in enumerate(chords):
                for key in range(12):
                    # Fill in with the transition probability to the final state
                    backward_matrix[N-1,key,root,c] = \
                            self.transition_probability(None, (key,root,chord))
        # Normalize
        backward_matrix[N-1] /= numpy.sum(backward_matrix[N-1])
        
        # Work backwards, filling in the matrix
        for time in range(N-2, -1, -1):
            # The transition matrix is reversed so we have backwards transitions
            # Then we multiply in the emission probabilities, broadcast over 
            #  the first index so we broadcast over keys
            # Summing over the first three axes sums over possible next states 
            # To speed up the computations, we keep the whole lot transposed
            trans_step = (trans_back * backward_matrix[time+1]) * ems[time+1]
            for i in range(3):
                trans_step = numpy.sum(trans_step, axis=-1)
            backward_matrix[time] = trans_step
            # Normalize over the timestep
            backward_matrix[time] /= numpy.sum(backward_matrix[time])
        
        if decomposed:
            return backward_matrix
        else:
            # Reshape the array so it has only two dimensions
            # Dimensions are ordered in same way as the components of the labels
            return backward_matrix.reshape(N, 12*12*C)
    
    def compute_decomposed_xi(self, sequence, forward=None, backward=None, 
                        emission_matrix=None, transition_matrix=None):
        from numpy import newaxis
        
        if forward is None:
            forward = self.normal_forward_probabilities(sequence, decomposed=True)
        if backward is None:
            backward = self.normal_backward_probabilities(sequence, decomposed=True)
        # T is the number of timesteps
        # N is the number of states
        T = forward.shape[0]
        C = len(self.chord_types)
        # Create the empty array to fill
        xi = numpy.zeros((T-1,12,12,C,12,12,C), numpy.float64)
        
        # Precompute all the emission probabilities
        if emission_matrix is None:
            emission_matrix = self.get_small_emission_matrix(sequence)
        # And transition probabilities: we'll need these many times over
        if transition_matrix is None:
            transition_matrix = self.get_small_transition_matrix(transpose=True)
        
        # Do it without logs - much faster
        for t in range(T-1):
            total = 0.0
            # Add axies to the forward probabilities to represent the next state
            fwd_trans = forward[t,:,:,:, newaxis,newaxis,newaxis]
            # Compute the xi values by multiplying the arrays together
            xi[t] = transition_matrix * fwd_trans * backward[t+1] * \
                        emission_matrix[t+1]
            # Normalize all the probabilities
            # Sum all the probs for the timestep and divide them all by total
            xi[t] /= array_sum(xi[t])
        
        return xi
    
    ################## Labeling ###################
    def label(self, midi, options={}, corpus=False):
        """
        Decodes the model with the given midi data to produce a chord labeling. 
        This is in the form of a set of possible chord labels for each midi 
        segment, each with a probability.
        
        @type options: dict
        @param options: labeling options: see L{HPChordLabeler.LABELING_OPTIONS}
        @type midi: L{jazzparser.data.input.SegmentedMidiInput}
        @param midi: the midi data to label
        @type corpus: bool
        @param corpus: if True, applies the corpus mapping associated with 
            the model to the labels so that the returned labels are corpus 
            labels instead of those used by the labeler
        
        """
        options = HPChordLabeler.process_labeling_options(options)
        N = options['n']
        
        # Preprocess the midi data to get an emission stream
        emissions = midi_to_emission_stream(midi, remove_empty=False)[0]
        
        if corpus:
            # Prepare the corpus mapping to apply to every chord label
            cmap = self.get_mapping_to_corpus()
            def _labmap(lab):
                return cmap[lab]
        else:
            def _labmap(lab):
                return lab
        
        if options['viterbi']:
            states = self.viterbi_decode(emissions)
            
            # A list of one top label for each timestep
            top_tags = [[
                        (ChordLabel(root,
                                    _labmap(label),
                                    None if options['nokey'] else key,
                                    label), 1.0)] \
                                            for (key,root,label) in states]
        else:
            gamma = self.compute_gamma(emissions)
            
            # Match up the elements in the array with their labels
            T = gamma.shape[0]
            probabilities = []
            for t in range(T):
                timeprobs = {}
                for i,label in enumerate(self.label_dom):
                    timeprobs[label] = gamma[t,i]
                probabilities.append(timeprobs)
            
            # Get just the top N labels for each timestep
            top_tags = []
            for time,probs in enumerate(probabilities):
                ranked = list(reversed(sorted(\
                        [(prob,(key,root,_labmap(label),label)) for \
                                ((key,root,label),prob) in probs.items()])))
                
                if options['nokey']:
                    # Ignore key and remove repeated labels
                    filtered = []
                    seen = []
                    for prob,(key,root,label,mlabel) in ranked:
                        if (root,label) not in seen:
                            filtered.append((prob,(None,root,label,mlabel)))
                            seen.append((root,label))
                    ranked = filtered
                
                # Cut off after the top N
                ranked = ranked[:N]
                # Convert all these tuples to chord label objects
                ranked = [(ChordLabel(root,label,key,mlabel),prob) for (prob,(key,root,label,mlabel)) in ranked]
                top_tags.append(ranked[:N])
        
        return top_tags
    
    def label_lattice(self, *args, **kwargs):
        """
        Decodes the model and produces a lattice of the top probability 
        chord labels.
        
        This is just L{label} with some extra wrapping to produce a 
        L{jazzparser.data.input.WeightedChordLabelInput} for the lattice.
        
        """
        from jazzparser.data.input import WeightedChordLabelInput
        
        # Use label() to get the labels
        top_tags = self.label(*args, **kwargs)
        
        return WeightedChordLabelInput(top_tags)
    
    ################## Storage ####################
    def to_picklable_dict(self):
        """ Produces a picklable representation of model as a dict. """
        from jazzparser.utils.nltk.storage import object_to_dict
        
        # We could store mutable distributions, but it's nicer to convert 
        #  them to unmutable ones before storing
        def _object_to_dict(obj):
            if type(obj) == MutableProbDist:
                # Convert to a normal dict prob dist
                obj = prob_dist_to_dictionary_prob_dist(obj)
            return object_to_dict(obj)
        
        return {
            'initial_key_dist' : _object_to_dict(self.initial_key_dist),
            'initial_chord_dist' : _object_to_dict(self.initial_chord_dist),
            'key_transition_dist' : _object_to_dict(self.key_transition_dist),
            'note_number_dist' : _object_to_dict(self.note_number_dist),
            'chord_transition_dist' : _object_to_dict(self.chord_transition_dist),
            'emission_dist' : _object_to_dict(self.emission_dist),
            'chord_vocab' : self.chord_vocab,
            'chord_corpus_mapping' : self.chord_corpus_mapping, 
            'max_notes' : self.max_notes,
            'history' : self.history,
            'description' : self.description,
        }
        
    @classmethod
    def from_picklable_dict(cls, data, name):
        """
        Reproduces an model that was converted to a picklable 
        form using to_picklable_dict.
        
        """
        from jazzparser.utils.nltk.storage import dict_to_object
        
        return cls(dict_to_object(data['initial_key_dist']),
                    dict_to_object(data['initial_chord_dist']),
                    dict_to_object(data['key_transition_dist']),
                    dict_to_object(data['chord_transition_dist']),
                    dict_to_object(data['emission_dist']),
                    dict_to_object(data['note_number_dist']),
                    data['chord_vocab'],
                    data['max_notes'],
                    data['chord_corpus_mapping'],
                    history=data.get('history', ''),
                    description=data.get('description', ''),
                    name=name)
    
    @classmethod
    def _get_model_dir(cls):
        return os.path.join(settings.MODEL_DATA_DIR, "hp_chords")
    @classmethod
    def __get_filename(cls, model_name):
        return os.path.join(cls._get_model_dir(), "%s.%s" % (model_name, FILE_EXTENSION))
    def __get_my_filename(self):
        return type(self).__get_filename(self.model_name)
    _filename = property(__get_my_filename)
    
    @staticmethod
    def process_training_options(opts):
        """ Verifies and processes the training option values. """
        return ModuleOption.process_option_dict(opts, HPChordLabeler.TRAINING_OPTIONS)
    
    @staticmethod
    def process_labeling_options(opts):
        """ Verifies and processes the labeling option values (dict). """
        return ModuleOption.process_option_dict(opts, HPChordLabeler.LABELING_OPTIONS)
    
    @classmethod
    def list_models(cls):
        """ Returns a list of the names of available models. """
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
        # Convert to picklable data
        data = self.to_picklable_dict()
        data = pickle.dumps(data, 2)
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
        Removes all the model's data. It is assumed that the model 
        will not be used at all after this has been called.
        
        """
        fn = self._filename
        if os.path.exists(fn):
            os.remove(fn)
            
    @classmethod
    def load_model(cls, model_name):
        filename = cls.__get_filename(model_name)
        # Load the model from a file
        if os.path.exists(filename):
            f = open(filename, 'r')
            model_data = f.read()
            model_data = pickle.loads(model_data)
            f.close()
        else:
            raise ModelLoadError, "the model '%s' has not been trained" % model_name
        return cls.from_picklable_dict(model_data, model_name)
    
    ############### Output ##############
    def _get_readable_params(self):
        text = ""
        
        # General information about the model
        text += "HMM with %d states\n" % len(self.label_dom)
        text += "\nChord vocab:\n   %s\n" % "\n   ".join(chord for chord in self.chord_vocab)
        
        # Emission distribution
        text += "\nEmission dist:\n"
        for label in self.chord_vocab:
            text += "  %s:\n" % label
            probs = reversed(sorted(
                        [(self.emission_dist[label].prob(root),root) for \
                            root in range(12)]))
            for (prob,root) in probs:
                text += "    %d: %s\n" % (root, prob)
        
        # Initial key distribution
        text += "\nInitial key dist:\n"
        for key in range(12):
            text += "   %d: %s\n" % (key, self.initial_key_dist.prob(key))
            
        # Initial chord distribution
        text += "\nInitial chord dist:\n"
        for label in self.chord_vocab:
            text += "  %s:\n" % label
            for root in range(12):
                text += "    %d: %s\n" % (root, self.initial_chord_dist.prob((root,label)))
        
        # Key change distribution
        text += "\nKey change dist:\n"
        for change in range(12):
            text += "  %d: %s\n" % (change, self.key_transition_dist.prob(change))
        
        # Chord transition distribution
        text += "\nChord transition dist:\n"
        for label0 in self.chord_vocab:
            for root0 in range(12):
                text += "  %s, %d ->\n" % (label0, root0)
                for label1 in self.chord_vocab:
                    for root1 in range(12):
                        text += "    %s, %d: %s\n" % (label1, root1, \
                                self.chord_transition_dist[(root0,label0)].prob(\
                                        (root1,label1)))
                text += "    End: %s\n" % \
                            self.chord_transition_dist[(root0,label0)].prob(None)
        return text
    readable_parameters = property(_get_readable_params)
