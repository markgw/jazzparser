"""N-gram tagger that operates on chord inputs or chord lattices.

This differs from the "ngram" tagger in that it can accept lattice input. 
The model is also very slightly different: it's almost equivalent, but 
makes a slightly different independence assumption. In general, you're 
probably better off using this version.

I'm using this version for all the experiments in the thesis, so that 
I can use the same supertagger for the supertagging experiments, parsing 
experiments and MIDI parsing experiments.

Note that this used to be called C{bigram-multi}, before I generalized it 
to n-grams and renamed it C{ngram-multi}. There may yet be bugs that arise 
as a result of this renaming, or old config files, etc, that haven't been
updated. The tagger and model classes have been correspondingly renamed.

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

import cPickle as pickle
from cStringIO import StringIO
from operator import mul

from jazzparser.taggers.models import ModelTagger, ModelLoadError, \
                            TaggerModel, TaggingModelError, ModelSaveError
from jazzparser.taggers import process_chord_input
from jazzparser.parsers.base.utils import SpanCombiner
from jazzparser.data.input import DbBulkInput, AnnotatedDbBulkInput, \
                            ChordInput, WeightedChordLabelInput, DbInput

from jazzparser.utils.options import ModuleOption, choose_from_list, \
                            choose_from_dict
from jazzparser.utils.probabilities import batch_sizes, beamed_batch_sizes
from jazzparser.utils.nltk.probability import ESTIMATORS, laplace_estimator, \
                                                            get_estimator_name
from jazzparser.taggers.chordmap import get_chord_mapping, \
                            get_chord_mapping_module_option

from .model import MultiChordNgramModel, lattice_to_emissions
from .. import TaggerTrainingError

class MultiChordNgramTaggerModel(TaggerModel):
    MODEL_TYPE = 'ngram-multi'
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
            usage="estimator=X, where X is one of: %s" \
                % ", ".join(ESTIMATORS.keys()), 
            default=laplace_estimator),
        # Standard chord mapping option
        get_chord_mapping_module_option(),
    ] + TaggerModel.TRAINING_OPTIONS
    
    def __init__(self, model_name, model=None, chordmap=None, *args, **kwargs):
        """
        An n-gram model to be used as a tagging model. Uses NLTK to 
        represent, train and evaluate the n-gram model.
        
        """
        super(MultiChordNgramTaggerModel, self).__init__(model_name, *args, **kwargs)
        self.model = model
        if chordmap is None:
            chordmap = get_chord_mapping()
        self.chordmap = chordmap
        
    def train(self, sequences, grammar=None, logger=None):
        if grammar is None:
            from jazzparser.grammar import get_grammar
            # Load the default grammar
            grammar = get_grammar()
        
        # We can only train on annotated chord sequence input
        if not isinstance(sequences, (DbBulkInput, AnnotatedDbBulkInput)):
            raise TaggerTrainingError, "can only train ngram-multi model "\
                "on bulk db chord input (bulk-db or bulk-db-annotated). Got "\
                "input of type '%s'" % type(sequences).__name__
        
        if self.options['backoff_cutoff'] is None:
            backoff_kwargs = {}
        else:
            backoff_kwargs = {'cutoff' : self.options['backoff_cutoff']}
        
        # Get all the possible pos tags from the grammar
        schemata = grammar.pos_tags
        # Build the emission domain to include all the observations that 
        #  theoretically could occur, not just those that are seen - 
        #  we might not see all interval/chord type pairs in the data.
        chord_types = list(set(self.options['chord_mapping'].values()))
        
        self.model = MultiChordNgramModel.train(
                                    sequences,
                                    schemata,
                                    chord_types,
                                    self.options['estimator'], 
                                    cutoff=self.options['cutoff'],
                                    chord_map=self.options['chord_mapping'],
                                    order=self.options['n'],
                                    backoff_orders=self.options['backoff'],
                                    backoff_kwargs=backoff_kwargs)
        
        # Add some model-specific info into the descriptive text
        #  so we know how it was trained
        est_name = get_estimator_name(self.options['estimator'])
        self.model_description = """\
Order: %(order)d
Backoff orders: %(backoff)d
Probability estimator: %(est)s
Zero-count threshold: %(cutoff)d
Chord mapping: %(chordmap)s
Training sequences: %(seqs)d\
""" % \
            {
                'est' : est_name,
                'seqs' : len(sequences),
                'cutoff' : self.options['cutoff'],
                'chordmap' : self.options['chord_mapping'].name,
                'order' : self.options['n'],
                'backoff' : self.options['backoff'],
            }
        
    @staticmethod
    def _load_model(data):
        from .model import MultiChordNgramModel
        
        model = MultiChordNgramModel.from_picklable_dict(data['model'])
        name = data['name']
        chordmap = get_chord_mapping(data.get('chordmap', None))
        return MultiChordNgramTaggerModel(name, model=model, chordmap=chordmap)
    
    def _get_model_data(self):
        data = {
            'name' : self.model_name,
            'model' : self.model.to_picklable_dict(),
            'chordmap' : self.chordmap.name,
        }
        return data
        
    #################### Decoding ######################
    # Decoding is mostly done by the superclass: we just provide some 
    #  handy interfaces here
    def forward_backward_probabilities(self, observations):
        """
        Returns a list of timesteps, each consisting of a dictionary mapping 
        states to their occupation probability in that timestep.
        
        """
        matrix = []
        # Get the state occupation probabilities
        gamma = self.model.compute_gamma(observations)
        
        T,N = gamma.shape
        # Make these into a matrix indexed by the state labels
        for t in range(T):
            state_probs = {}
            for s,state in enumerate(self.model.label_dom):
                state_probs[state] = gamma[t, s]
            matrix.append(state_probs)
        return matrix
        
    def forward_probabilities(self, observations):
        """
        Like L{forward_backward_probabilities}, but only uses forward algorithm.
        
        """
        # This is easy, since the hmm already provides the right form of matrix
        return self.model.normal_forward_probabilities(observations)
    
    ############ Parameter output ###########
    def _get_readable_parameters(self):
        """ Produce a human-readable repr of the params of the model """
        buff = StringIO()
        
        try:
            
            # Include the stored model description
            print >>buff, self.model_description
            
            print >>buff, "\nNum emissions: %d" % self.model.num_emissions
            print >>buff, "\nShowing only probs for non-zero counts. "\
                    "Others may have a non-zero prob by smoothing"
                
            print >>buff, "\nChord mapping: %s:" % self.chordmap.name
            for (crdin, crdout) in self.chordmap.items():
                print >>buff, "  %s -> %s" % (crdin, crdout)
            
            print >>buff, "\nRoot transition dist"
            for schema in sorted(self.model.root_transition_dist.conditions()):
                print >>buff, "  %s" % schema
                for prob,interval in reversed(sorted(\
                        (self.model.root_transition_dist[schema].prob(interval),
                         interval) for \
                        interval in self.model.root_transition_dist[schema].samples())):
                    print >>buff, "    %s: %s " % (interval, prob)
            print >>buff
            
            print >>buff, "Schema transition dist"
            for context in sorted(self.model.schema_transition_dist.conditions()):
                print >>buff, "  %s" % ",".join([str(s) for s in context])
                for prob,schema in reversed(sorted(\
                        (self.model.schema_transition_dist[context].prob(schema),
                         schema) for \
                        schema in self.model.schema_transition_dist[context].samples())):
                    print >>buff, "    %s: %s " % (schema, prob)
            print >>buff
            
            print >>buff, "Emission dist"
            for schema in sorted(self.model.emission_dist.conditions()):
                print >>buff, "  %s" % schema
                for prob,chord in reversed(sorted(\
                        (self.model.emission_dist[schema].prob(chord),
                         chord) for \
                        chord in self.model.emission_dist[schema].samples())):
                    print >>buff, "    %s: %s " % (chord, prob)
        except AttributeError, err:
            # Catch this, because otherwise it just looks like the attribute 
            #  (readable_parameters) doesn't exist (stupid Python behaviour)
            raise ValueError, "error generating model description "\
                            "(attribute error): %s" % err
        
        return buff.getvalue()
    readable_parameters = property(_get_readable_parameters)
    

class MultiChordNgramTagger(ModelTagger):
    MODEL_CLASS = MultiChordNgramTaggerModel
    TAGGER_OPTIONS = ModelTagger.TAGGER_OPTIONS + [
        ModuleOption('decode', filter=choose_from_list([ \
                                        'forward-backward', 'forward']), 
            help_text="Decoding method for inference.",
            usage="decode=X, where X is one of 'viterbi', 'forward-backward' "\
                "or 'forward'",
            default="forward-backward"),
    ]
    INPUT_TYPES = ['db', 'chords', 'labels']
    
    def __init__(self, grammar, input, options={}, *args, **kwargs):
        super(MultiChordNgramTagger, self).__init__(grammar, input, options, *args, **kwargs)
        process_chord_input(self)
        
        #### Tag the input sequence ####
        self._tagged_times = []
        self._tagged_spans = []
        self._batch_ranges = []
        word_tag_probs = []
        
        # Map the chord types as the model requires
        chord_map = self.model.chordmap
        
        if isinstance(self.wrapped_input, ChordInput):
            chords = self.wrapped_input.to_db_input().chords
            observations = [(chord.root, chord_map[chord.type]) for chord in chords]
            self.input = chords
        elif isinstance(self.wrapped_input, DbInput):
            observations = [(chord.root, chord_map[chord.type]) for chord in self.wrapped_input.chords]
        elif isinstance(self.wrapped_input, WeightedChordLabelInput):
            observations = lattice_to_emissions(input, chord_map=chord_map)
            
        # Use the ngram model to get tag probabilities for each input by 
        # computing the forward probability matrix
        if self.options['decode'] == "forward":
            probabilities = self.model.forward_probabilities(observations)
        else:
            probabilities = self.model.forward_backward_probabilities(observations)
        
        # Filter out zero probability states and order by desc prob
        probabilities = [
            reversed(sorted(\
                [(state,prob) for (state,prob) in timestep.items() if prob > 0.0], \
                    key=lambda x:x[1])) \
                for timestep in probabilities]
        
        for index,probs in enumerate(probabilities):
            features = {
                'duration' : self.durations[index],
                'time' : self.times[index],
            }
            
            word_signs = []
            for (state,prob) in probs:
                root,schema = state
                # Instantiate a sign for this state
                features['root'] = root
                signs = self.grammar.get_signs_for_tag(schema, features)
                # There should only be one of these
                if not signs:
                    continue
                else:
                    sign = signs[0]
                word_signs.append((sign, (root, schema), prob))
            
            self._tagged_times.append(word_signs)
            
            # Store the list of probabilities for tags, which we'll use 
            #  after we've tagged every word to work out the sizes
            #  of the tag batches
            word_tag_probs.append([p for __,__,p in word_signs])
        
        if self.options['best']:
            # Only return one for each word
            batch_ranges = [[(0,1)] for i in range(len(self.input))]
        else:
            # Work out the number of tags to return in each batch
            batch_sizes = beamed_batch_sizes(word_tag_probs, self.batch_ratio, max_batch=self.options['max_batch'])
            # Transform these into a form that's easier to use for getting the signs
            batch_ranges = [[(sum(batches[:i]),sum(batches[:i+1])) for i in range(len(batches))] \
                                    for batches in batch_sizes]
        
        # Step through adding each to see which we should also add to combine 
        #  repetitions of identical schema,root pairs
        def prob_combiner(probs):
            return sum(probs, 0.0) / float(len(probs))
        combiner = SpanCombiner()
        added = True
        offset = 0
        while added:
            added = False
            batch_spans = []
            for time in range(len(batch_ranges)):
                if offset < len(batch_ranges[time]):
                    start, end = batch_ranges[time][offset]
                    for sign_offset in range(start, end):
                        sign, (root,schema), prob = self._tagged_times[time][sign_offset]
                        added = True
                        # Add the length 1 span
                        batch_spans.append((time, time+1, (sign,(root,schema),prob)))
                        # Add this to the combiner to see if it combines 
                        #  with anything we've previously added
                        combined = combiner.combine_edge(
                                            (time, time+1, (root,schema)),
                                            properties=prob,
                                            prop_combiner=prob_combiner)
                        # Add each additional span with the same sign
                        for (span_start, span_end) in combined:
                            # Set the probability of the combined categories
                            new_prob = combiner.edge_properties[
                                        (span_start, span_end, (root,schema))]
                            # Set timing properties of this spanning category
                            features = {
                                'duration' : sum(
                                        self.durations[span_start:span_end]),
                                'time' : self.times[span_start],
                                'root' : root,
                            }
                            # Technically there could be multiple of these, 
                            #  though in fact there never are
                            new_signs = \
                                self.grammar.get_signs_for_tag(schema, features)
                            for new_sign in new_signs:
                                batch_spans.append(
                                    (span_start, span_end, 
                                        (new_sign, (root,schema), new_prob)))
            self._tagged_spans.append(batch_spans)
            offset += 1

    def get_signs(self, offset=0):
        if offset < len(self._tagged_spans):
            return self._tagged_spans[offset]
        else:
            return []
        
    def get_word(self, index):
        return self.input[index]
