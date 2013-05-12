"""Ngram model supertagger, making use NLTK's probability models.

This provides the tagger interface routines for an ngram tagger. It is 
backed by the ngram models defined in L{jazzparser.utils.nltk.ngram}, 
which use NLTK's probability handling classes.

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
import cPickle as pickle
import random
from jazzparser.taggers.models import ModelTagger, ModelLoadError, \
                TaggerModel, TaggingModelError, ModelSaveError
from jazzparser.taggers import process_chord_input
from jazzparser.taggers.chordmap import get_chord_mapping_module_option, \
                            get_chord_mapping
from jazzparser.data import Chord
from jazzparser.data.db_mirrors import Chord as DbChord

from jazzparser.utils.nltk.probability import ESTIMATORS, laplace_estimator, get_estimator_name
from jazzparser.utils.options import ModuleOption, choose_from_list, \
                                        choose_from_dict
from jazzparser.utils.base import group_pairs, load_optional_package, load_from_optional_package
from jazzparser.utils.probabilities import batch_sizes, beamed_batch_sizes

from nltk.probability import FreqDist

def observation_from_chord_pair(crd1, crd2, chordmap):
    if crd2 is None:
        interval = 0
    else:
        interval = Chord.interval(Chord.from_name(str(crd1)), Chord.from_name(str(crd2)))
    if not isinstance(crd1, Chord) and not isinstance(crd1, DbChord):
        crd1 = Chord.from_name(crd1)
    return "%d-%s" % (interval, chordmap[crd1.type])


class NgramTaggerModel(TaggerModel):
    MODEL_TYPE = 'ngram'
    # Set up possible options for training
    TRAINING_OPTIONS = [
        ModuleOption('n', filter=int, 
            help_text="Length of the n-grams which this model will use.",
            usage="n=N, where N is an integer. Defaults to bigrams", default=2),
        ModuleOption('backoff', filter=int, 
            help_text="Number of orders of backoff to use. This must be "\
                "less than n. E.g. if using a trigram model (n=3) you can "\
                "set backoff=2 to back off to bigrams and from bigrams "\
                "to unigrams. Set to 0 to use no backoff at all (default).",
            usage="backoff=X, where X is an integer < n", default=0),
        ModuleOption('cutoff', filter=int, 
            help_text="In estimating probabilities, treat any counts below "\
                "cutoff as zero",
            usage="cutoff=X, where X is an integer", default=0),
        ModuleOption('backoff_cutoff', filter=int, 
            help_text="Apply a different cutoff setting to the backoff model. "\
                "Default is to use the same as the main model",
            usage="backoff_cutoff=X, where X is an integer"),
        ModuleOption('estimator', filter=choose_from_dict(ESTIMATORS), 
            help_text="A way of constructing a probability model given "\
                "the set of counts from the data. Default is to use "\
                "laplace (add-one) smoothing.",
            usage="estimator=X, where X is one of: %s" % \
                ", ".join(ESTIMATORS.keys()), default=laplace_estimator),
        # Add the standard chord mapping option ("chord_mapping")
        get_chord_mapping_module_option(),
    ] + TaggerModel.TRAINING_OPTIONS
    
    def __init__(self, model_name, model=None, chordmap=None, *args, **kwargs):
        """
        An n-gram model to be used as a tagging model. Uses NLTK to 
        represent, train and evaluate the n-gram model.
        
        """
        super(NgramTaggerModel, self).__init__(model_name, *args, **kwargs)
        self.model = model
        
        self.chordmap = get_chord_mapping(chordmap)
        self.chordmap_name = chordmap
        
        if self.options['n'] <= self.options['backoff']:
            # This is not allowed
            # We can only back off n-1 orders for an n-gram model
            raise TaggingModelError, "tried to load an n-gram model with "\
                "more orders of backoff than are possible (backing off "\
                "%d orders on a %d-gram model)" % \
                    (self.options['backoff'], self.options['n'])
        
    def train(self, sequences, grammar=None, logger=None):
        from jazzparser.utils.nltk.ngram import PrecomputedNgramModel
        if grammar is None:
            from jazzparser.grammar import get_grammar
            # Load the default grammar
            grammar = get_grammar()
        
        N = self.options['n']
        backoff = self.options['backoff']
        chordmap = self.options['chord_mapping']
        self.chordmap = chordmap
        self.chordmap_name = chordmap.name
        
        # Get data in the form of lists of (observation,tag) pairs
        training_data = [[(observation_from_chord_pair(c1, c2, chordmap), c1cat) \
                                for ((c1,c2),c1cat) in zip(group_pairs(seq, none_final=True),seq.categories)]
                                    for seq in sequences]
        # Get all the possible pos tags from the grammar
        label_dom = grammar.pos_tags
        # Build the emission domain to include all the observations that 
        #  theoretically could occur, not just those that are seen - 
        #  we might not see all interval/chord type pairs in the data.
        chord_types = chordmap.values()
        emission_dom = sum([["%d-%s" % (interval,chord) for chord in chord_types] for interval in range(12)], [])
        
        # Ignore unlabelled data
        ignores = ['']
        
        if self.options['backoff_cutoff'] is None:
            backoff_kwargs = {}
        else:
            backoff_kwargs = {'cutoff' : self.options['backoff_cutoff']}
        
        # Precompute the transition matrix and store it along with the model
        self.model = PrecomputedNgramModel.train(
                            self.options['n'],
                            training_data,
                            label_dom,
                            emission_dom=emission_dom,
                            cutoff=self.options['cutoff'],
                            backoff_order=self.options['backoff'],
                            estimator=self.options['estimator'],
                            ignore_list=ignores,
                            backoff_kwargs=backoff_kwargs)
        
        # Add some model-specific info into the descriptive text
        #  so we know how it was trained
        est_name = get_estimator_name(self.options['estimator'])
        self.model_description = """\
Model order: %(order)d
Backoff orders: %(backoff)d
Probability estimator: %(est)s
Zero-count threshold: %(cutoff)d
Chord mapping: %(chordmap)s
Training sequences: %(seqs)d
Training samples: %(samples)d\
""" % \
            {
                'est' : est_name,
                'seqs' : len(training_data),
                'samples' : len(sum(training_data, [])),
                'order' : self.options['n'],
                'backoff' : self.options['backoff'],
                'cutoff' : self.options['cutoff'],
                'chordmap' : self.chordmap_name,
            }
        
    @staticmethod
    def _load_model(data):
        from jazzparser.utils.nltk.ngram import PrecomputedNgramModel
        
        model = PrecomputedNgramModel.from_picklable_dict(data['model'])
        name = data['name']
        chordmap = data.get("chordmap", None)
        return NgramTaggerModel(name, model=model, chordmap=chordmap)
    
    def _get_model_data(self):
        data = {
            'name' : self.model_name,
            'model' : self.model.to_picklable_dict(),
            'chordmap' : self.chordmap_name,
        }
        return data
        
    def generate_chord_sequence(self, length=20):
        """
        Just for a laugh, use the trained n-gram to generate a chord 
        sequence and output it in a playable form.
        Returns a tuple: (chords, tags)
        
        @todo: this isn't implemented yet for n-grams. It's not a 
        high priority, but would be fun.
        
        """
        # Easily done, because the NgramModel already implements it itself
        raise NotImplementedError, "not yet done generation for n-grams"
        # This is what the other tagger did:
        
        from jazzparser.utils.chords import int_to_chord_numeral
        # Use the model to generate randomly
        rand_seq = self.model.random_sample(random.Random(), length)
        pitch = 0
        chords = []
        prochords,tags = zip(*rand_seq)
        # Convert the generated observations into readable chords
        for chord in prochords:
            interval,__,ctype = chord.partition("-")
            chords.append("%s%s" % (int_to_chord_numeral(pitch),ctype))
            pitch = (pitch + int(interval)) % 12
        return (chords, tags)
        
    def forward_probabilities(self, sequence):
        """ Interface to the NgramModel's forward_probabilities """
        return self.model.forward_probabilities(sequence)
        
    def forward_backward_probabilities(self, sequence):
        return self.model.gamma_probabilities(sequence, dictionary=True)
        
    def viterbi_probabilities(self, sequence):
        return self.model.viterbi_selector_probabilities(sequence)
        
    def _get_tags(self):
        return self.model.label_dom
    tags = property(_get_tags)
    
    #### Readable output of the parameters ####
    def _get_readable_params(self):
        try:
            text = ""
            
            # Include the stored model description
            text += self.model_description
            
            text += "\nNum emissions: %d\n" % self.model.num_emissions
            text += "\nShowing only probs for non-zero counts. "\
                    "Others may have a non-zero prob by smoothing\n"
                
            text += "\nChord mapping: %s:\n" % self.chordmap.name
            for (crdin, crdout) in self.chordmap.items():
                text += "  %s -> %s\n" % (crdin, crdout)
            
            # Emission distribution
            text += "\nEmission dist:\n"
            for label in sorted(self.model.label_dom):
                text += "  %s:\n" % label
                probs = reversed(sorted(
                            [(self.model.emission_dist[label].prob(em),em) for \
                                em in self.model.emission_dist[label].samples()]))
                for (prob,em) in probs:
                    text += "    %s: %s\n" % (em, prob)
                    
            text += "\n\nTransition dist:\n"
            for history in sorted(self.model.label_dist.conditions()):
                text += "  %s\n" % str(history)
                dist = [(self.model.label_dist[history].prob(lab),lab) 
                            for lab in self.model.label_dist[history].samples()]
                for prob,label in reversed(sorted(dist)):
                    text += "    %s: %s\n" % (str(label), prob)
            
            return text
        except AttributeError, err:
            # Catch this, because otherwise it just looks like the attribute 
            #  (readable_parameters) doesn't exist (stupid Python behaviour)
            raise ValueError, "error generating model description "\
                            "(attribute error): %s" % err
    readable_parameters = property(_get_readable_params)
    

DECODERS = ['viterbi', 'forward-backward', 'forward']

class NgramTagger(ModelTagger):
    MODEL_CLASS = NgramTaggerModel
    TAGGER_OPTIONS = ModelTagger.TAGGER_OPTIONS + [
        ModuleOption('decode', filter=choose_from_list(DECODERS), 
            help_text="Decoding method for inference.",
            usage="decode=X, where X is one of %s" % \
                                ", ".join("'%s'" % d for d in DECODERS),
            default="forward-backward"),
    ]
    INPUT_TYPES = ['db', 'chords']
    
    def __init__(self, grammar, input, options={}, *args, **kwargs):
        """
        Tags using an ngram model backed by NLTK.
        
        """
        super(NgramTagger, self).__init__(grammar, input, options, *args, **kwargs)
        process_chord_input(self)
        
        #### Tag the input sequence ####
        self._tagged_data = []
        self._batch_ranges = []
        # Group the input into pairs to get observations
        inpairs = group_pairs(self.input, none_final=True)
        # Convert the pairs into observations
        observations = [observation_from_chord_pair(pair[0], pair[1], self.model.chordmap) for pair in inpairs]
        
        # Use the ngram model to get tag probabilities for each input by 
        # computing the forward probability matrix
        if self.options['decode'] == "viterbi":
            probabilities = self.model.viterbi_probabilities(observations)
        elif self.options['decode'] == "forward":
            probabilities = self.model.forward_probabilities(observations)
        else:
            probabilities = self.model.forward_backward_probabilities(observations)
            
        word_tag_probs = []
        
        for index,probs in enumerate(probabilities):
            features = {
                'duration' : self.durations[index],
                'time' : self.times[index],
            }
            word_signs = []
            # Now assign a probability to each tag, given the observation
            for tag in self.model.tags:
                # Read a full sign out of the grammar
                sign = self.grammar.get_sign_for_word_by_tag(self.input[index], tag, extra_features=features)
                if sign is not None:
                    # Read off the probability from the matrix
                    probability = probs[tag]
                    word_signs.append((sign, tag, probability))
            
            # Randomly sort the list first to make sure equal probabilities are randomly ordered
            word_signs = [(sign, tag, prob) for sign,tag,prob in word_signs]
            random.shuffle(word_signs)
            # Now sort by probability
            word_signs = list(reversed(sorted(word_signs, key=lambda x:x[2])))
            self._tagged_data.append(word_signs)
            
            # Store the list of probabilities for tags, which we'll use 
            #  after we've tagged every word to work out the sizes
            #  of the tag batches
            word_tag_probs.append([p for __,__,p in word_signs])
        
        if self.options['best']:
            # Only return one for each word
            self._batch_ranges = [[(0,1)] for i in range(len(self.input))]
        else:
            # Work out the number of tags to return in each batch
            batch_sizes = beamed_batch_sizes(word_tag_probs, self.batch_ratio)
            # So far, this has assigned a probability to every possible 
            #  tag. We don't want the tagger ever to return the least 
            #  probably batch of tags, unless it's the only one.
            #batch_sizes = [batches[:-1] if len(batches) > 1 else batches for batches in batch_sizes]
            # Transform these into a form that's easier to use for getting the signs
            self._batch_ranges = [[(sum(batches[:i]),sum(batches[:i+1])) for i in range(len(batches))] \
                                    for batches in batch_sizes]

    def get_signs(self, offset=0):
        all_signs = []
        for start_node in range(len(self.input)):
            # Get the indices of the signs to return in this offset batch
            ranges = self._batch_ranges[start_node]
            if offset >= len(ranges):
                # No more batches left for this word
                continue
            start,end = ranges[offset]
            signs = self._tagged_data[start_node][start:end]
            # Add each sign to the output list along with its node values
            for sign in signs:
                all_signs.append((start_node, start_node+1, sign))
        return all_signs
        
    def get_word(self, index):
        return self.input[index]
