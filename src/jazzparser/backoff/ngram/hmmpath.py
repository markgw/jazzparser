"""Ngram direct semantics models.

Here I use ngram models to assign a tonal-space semantics to an input 
sequence.
This is the model referred to as I{HmmPath} in papers and talks.

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

from StringIO import StringIO
from nltk.probability import ConditionalProbDist

from jazzparser.utils.nltk.ngram import NgramModel
from jazzparser.utils.nltk.probability import ESTIMATORS, laplace_estimator, \
                            get_estimator_name, CutoffConditionalFreqDist, \
                            logprob, sum_logs
from jazzparser.utils.base import group_pairs
from jazzparser.utils.options import ModuleOption, ModuleOptionError, \
                            choose_from_dict
from jazzparser.utils.tonalspace import coordinate_to_et_2d
from jazzparser.utils.loggers import create_dummy_logger

from ..base import ModelBackoffBuilder, BackoffModel, \
                merge_repeated_points
from jazzparser.grammar import get_grammar
from jazzparser.evaluation.parsing import parse_sequence_with_annotations
from jazzparser.parsers import ParseError
from jazzparser.taggers import process_chord_input
from jazzparser.taggers.chordmap import get_chord_mapping, \
                            get_chord_mapping_module_option
from jazzparser.taggers.ngram_multi.model import lattice_to_emissions

from jazzparser.data.input import DbBulkInput, AnnotatedDbBulkInput, \
                            ChordInput, WeightedChordLabelInput, DbInput
from jazzparser.data import Chord
from jazzparser.data.db_mirrors import Chord as DbChord

# We shouldn't really use this formalism-specific data structure here, 
#  but it includes the computation we need to do, so I'm being naughty
from jazzparser.formalisms.music_halfspan.semantics import EnharmonicCoordinate

def vector(p0, p1):
    """
    Vector from p0 to p1, where the ps are points represented as they are 
    internally in the model: (X,Y,x,y). (x,y) defines the point in the local 
    (enharmonic) space and is that closest to the previous point when 
    (X,Y) = (0,0). (X,Y) defines a shift of enharmonic space.
    
    """
    # We don't care about X0 and Y0
    X0,Y0,x0,y0 = p0
    X1,Y1,x1,y1 = p1
    # Get the basic vector, assuming (X1,Y1)=(0,0)
    nearest = EnharmonicCoordinate((x0,y0)).nearest((x1,y1))
    # Shift this according to X1 and Y1
    nearest.X += X1
    nearest.Y += Y1
    newx, newy = nearest.harmonic_coord
    return (newx-x0, newy-y0)

class HmmPathNgram(NgramModel):
    """
    An ngram model that takes multiple chords (weighted by probability) as 
    input to its decoding. It is trained on labeled data.
    
    This is similar to 
    L{jazzparser.taggers.ngram_multi.model.MultiChordNgramModel}, but the 
    states represent points on a TS path, rather than categories.
    
    """
    def __init__(self, order, point_transition_counts, fn_transition_counts, 
                    type_emission_counts, subst_emission_counts, 
                    estimator, backoff_model, chord_map, vector_dom, 
                    point_dom, history=""):
        self.order = order
        self.backoff_model = backoff_model
        
        chord_vocab = list(set(chord_map.keys()))
        self.chord_vocab = chord_vocab
        internal_chord_vocab = list(set(chord_map.values()))
        self.chord_map = chord_map
        self._estimator = estimator
        
        # Construct the domains by combining possible roots with 
        #  the other components of the labels
        self.vector_dom = vector_dom
        self.point_dom = point_dom
        self.label_dom = [(point,function) for point in point_dom \
                                            for function in ["T","D","S"] ]
        self.num_labels = len(self.label_dom)
        self.emission_dom = [(root,label) for root in range(12) \
                                        for label in internal_chord_vocab]
        self.num_emissions = len(self.emission_dom)
        
        # Keep hold of the freq dists
        self.point_transition_counts = point_transition_counts
        self.fn_transition_counts = fn_transition_counts
        self.type_emission_counts = type_emission_counts
        self.subst_emission_counts = subst_emission_counts
        # Make some prob dists
        self.point_transition_dist = ConditionalProbDist(
                        point_transition_counts, estimator, len(vector_dom))
        self.fn_transition_dist = ConditionalProbDist(
                        fn_transition_counts, estimator, 4) # Includes final state
        self.type_emission_dist = ConditionalProbDist(
                        type_emission_counts, estimator, len(internal_chord_vocab))
        self.subst_emission_dist = ConditionalProbDist(
                        subst_emission_counts, estimator, 12)
        
        # Store a string with information about training, etc
        self.history = history
        # Initialize the various caches
        # These will be filled as we access probabilities
        self.clear_cache()
    
    def add_history(self, string):
        """ Adds a line to the end of this model's history string. """
        self.history += "%s: %s\n" % (datetime.now().isoformat(' '), string)
    
    @staticmethod
    def train(data, estimator, grammar, cutoff=0, logger=None, 
                chord_map=None, order=2, backoff_orders=0, backoff_kwargs={}):
        """
        Initializes and trains an HMM in a supervised fashion using the given 
        training data. Training data should be chord sequence data (input 
        type C{bulk-db} or C{bulk-db-annotated}).
        
        """
        # Prepare a dummy logger if none was given
        if logger is None:
            logger = create_dummy_logger()
        logger.info(">>> Beginning training of ngram backoff model")
        
        training_data = []
        # Generate the gold standard data by parsing the annotations
        for dbinput in data:
            # Get a gold standard tonal space sequence
            try:
                parses = parse_sequence_with_annotations(dbinput, grammar, \
                                                        allow_subparses=False)
            except ParseError, err:
                # Just skip this sequence
                logger.error('Could not get a GS parse of %s: %s' % (dbinput,err))
                continue
            # There should only be one of these now
            parse = parses[0]
            if parse is None:
                logger.error('Could not get a GS parse of %s' % (dbinput))
                continue
            
            # Get the form of the analysis we need for the training
            if chord_map is None:
                chords = [(c.root, c.type) for c in dbinput.chords]
            else:
                chords = [(c.root, chord_map[c.type]) for c in dbinput.chords]
            
            points,times = zip(*grammar.formalism.semantics_to_coordinates(
                                                    parse.semantics))
            # Run through the sequence, transforming absolute points into 
            #  the condensed relative representation
            ec0 = EnharmonicCoordinate.from_harmonic_coord(points[0])
            # The first point is relative to the origin and always in the 
            #  (0,0) enharmonic space
            rel_points = [(0,0,ec0.x,ec0.y)]
            for point in points[1:]:
                ec1 = EnharmonicCoordinate.from_harmonic_coord(point)
                # Find the nearest enharmonic instance of this point to the last
                nearest = ec0.nearest((ec1.x, ec1.y))
                # Work out how much we have to shift this by to get the point
                dX = ec1.X - nearest.X
                dY = ec1.Y - nearest.Y
                rel_points.append((dX,dY,ec1.x,ec1.y))
                ec0 = ec1
            funs,times = zip(*grammar.formalism.semantics_to_functions(
                                                    parse.semantics))
            
            ### Synchronize the chords with the points and functions
            # We may need to repeat chords to match up with analysis 
            #  points that span multiple chords
            analysis = iter(zip(rel_points,funs,times))
            rel_point, fun, __ = analysis.next()
            next_rel_point,next_fun,next_anal_time = analysis.next()
            # Keep track of how much time has elapsed
            time = 0
            training_seq = []
            reached_end = False
            for crd_pair,chord in zip(chords, dbinput.chords):
                if time >= next_anal_time and not reached_end:
                    # Move on to the next analysis point
                    rel_point, fun = next_rel_point, next_fun
                    try:
                        next_rel_point,next_fun,next_anal_time = analysis.next()
                    except StopIteration:
                        # No more points: keep using the same to the end
                        reached_end = True
                training_seq.append((crd_pair, (rel_point,fun)))
                time += chord.duration
            training_data.append(training_seq)
        
        # Create some empty freq dists
        subst_emission_counts = CutoffConditionalFreqDist(cutoff=cutoff)
        type_emission_counts = CutoffConditionalFreqDist(cutoff=cutoff)
        point_transition_counts = CutoffConditionalFreqDist(cutoff=cutoff)
        fn_transition_counts = CutoffConditionalFreqDist(cutoff=cutoff)
        
        seen_vectors = []
        seen_points = set()
        seen_XY = set()
        
        # Count all the stats from the training data
        for seq in training_data:
            # Keep track of the necessary history context
            history = []
            for (chord, (point,fun)) in seq:
                ### Counts for the emission distribution
                chord_root,label = chord
                # Work out the chord substitution
                X,Y,x,y = point
                subst = (chord_root - coordinate_to_et_2d((x,y))) % 12
                # Increment the counts
                subst_emission_counts[fun].inc(subst)
                type_emission_counts[(subst,fun)].inc(label)
                
                seen_points.add(point)
                seen_XY.add((X,Y))
                
                if order > 1:
                    ### Counts for the transition distribution
                    # Update the history fifo
                    history = [(point,fun)] + history[:order-1]
                    if len(history) > 1:
                        points,functions = zip(*history)
                        #~ # Get the vectors between the points
                        #~ vectors = [vector(p0,p1) for (p1,p0) in \
                                        #~ group_pairs([p for p in points if p is not None])]
                        # The function is conditioned on all previous functions
                        fn_context = tuple(functions[1:])
                        fn_transition_counts[fn_context].inc(functions[0])
                        
                        #~ # The vector is conditioned on the function 
                        #~ #  and the pairs of vector and function preceding that
                        #~ point_context = tuple([functions[:2]] + 
                                              #~ list(zip(vectors[1:], functions[2:])))
                        # The vector is conditioned on the function
                        #~ point_transition_counts[point_context].inc(vectors[0])
                        vect = vector(points[1], points[0])
                        point_transition_counts[functions[0]].inc(vect)
                        
                        # Keep track of what vectors we've observed
                        #~ seen_vectors.append(vectors[0])
                        seen_vectors.append(vect)
                    else:
                        # For the first point, we only count the function prob
                        fn_transition_counts[tuple()].inc(fun)
            
            if order > 1:
                # Count the transition to the final state
                history = history[:order-1]
                points,functions = zip(*history)
                fn_context = tuple(functions)
                fn_transition_counts[fn_context].inc(None)
        
        # Labels are (X,Y,x,y). We want all the points seen in the data 
        #  and all (0,0,x,y)
        for X,Y in seen_XY:
            for x in range(4):
                for y in range(3):
                    seen_points.add((X,Y,x,y))
        point_dom = list(seen_points)
        
        if backoff_orders > 0:
            # Default to using the same params for the backoff model
            kwargs = {
                'cutoff' : cutoff,
                'chord_map' : chord_map, 
            }
            kwargs.update(backoff_kwargs)
            
            logger.info("Training backoff model")
            # Train a backoff model
            backoff = HmmPathNgram.train(data, estimator, grammar, logger=logger, 
                        order=order-1, backoff_orders=backoff_orders-1, 
                        backoff_kwargs=backoff_kwargs, **kwargs)
        else:
            backoff = None
        
        # Get a list of every vector in the training set
        vector_dom = list(set(seen_vectors))
        
        return HmmPathNgram(order, 
                            point_transition_counts, 
                            fn_transition_counts, 
                            type_emission_counts, 
                            subst_emission_counts, 
                            estimator, 
                            backoff, 
                            chord_map, 
                            vector_dom, 
                            point_dom)
    
    ################## Probabilities ###################
    def transition_log_probability(self, *states):
        states = [s if s is not None else (None,None) for s in states]
        
        if self.order == 1:
            # Transitions are all equiprobable
            return - logprob(len(self.label_dom))
        
        points,functions = zip(*states)
        
        if points[0] is None:
            # Just use the fun transition to get prob of final state
            fn_context = tuple(functions[:1])
            return self.fn_transition_dist[fn_context].logprob(None)
        
        if all(p is None for p in points[1:]) == 1:
            # Initial states: all points equiprobable
            # Only permit points in the (0,0) enharmonic space
            if points[0][0] != 0 or points[0][1] != 0:
                return float('-inf')
            # Get fn prob from initial dist
            return self.fn_transition_dist[tuple()].logprob(functions[0]) - logprob(12)
        
        # The function is conditioned on all previous functions
        fn_context = tuple(functions[1:])
        fn_prob = self.fn_transition_dist[fn_context].logprob(functions[0])
        
        vect = vector(points[1], points[0])
        # The vector is conditioned on the function 
        #  and the pairs of vector and function preceding that
        vector_prob = self.point_transition_dist[functions[0]].logprob(vect)
        
        # Multiply together the vector and function probs
        return vector_prob + fn_prob
        
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
        point,function = state
        chord_root,label = emission
        X,Y,x,y = point
        # Work out the chord substitution
        subst = (chord_root - coordinate_to_et_2d((x,y))) % 12
        
        # Generate the substitution given the chord function
        subst_prob = self.subst_emission_dist[function].logprob(subst)
        # Generate the label given the subst and chord function
        label_prob = self.type_emission_dist[(subst,function)].logprob(label)
        return subst_prob + label_prob
    
    ################## Storage ####################
    def to_picklable_dict(self):
        from jazzparser.utils.nltk.storage import object_to_dict
        
        if self.backoff_model is not None:
            backoff_model = self.backoff_model.to_picklable_dict()
        else:
            backoff_model = None
        
        return {
            'order' : self.order, 
            'point_transition_counts' : object_to_dict(self.point_transition_counts),
            'fn_transition_counts' : object_to_dict(self.fn_transition_counts),
            'type_emission_counts' : object_to_dict(self.type_emission_counts),
            'subst_emission_counts' : object_to_dict(self.subst_emission_counts),
            'estimator' : self._estimator,
            'backoff_model' : backoff_model,
            'chord_map' : self.chord_map.name,
            'vector_dom' : self.vector_dom, 
            'point_dom' : self.point_dom,
            'history' : self.history,
        }
        
    @classmethod
    def from_picklable_dict(cls, data):
        from jazzparser.utils.nltk.storage import dict_to_object
        
        if data['backoff_model'] is not None:
            backoff_model = cls.from_picklable_dict(data['backoff_model'])
        else:
            backoff_model = None
        
        return cls(data['order'],
                    dict_to_object(data['point_transition_counts']),
                    dict_to_object(data['fn_transition_counts']),
                    dict_to_object(data['type_emission_counts']),
                    dict_to_object(data['subst_emission_counts']),
                    data['estimator'],
                    backoff_model,
                    get_chord_mapping(data['chord_map']),
                    data['vector_dom'],
                    data['point_dom'],
                    history=data.get('history', ''))
    
    
class HmmPathModel(BackoffModel):
    """
    Model type that uses an ngram model to assign a tonal space
    path to a sequence. This class provides the interface to the model 
    training and decoding. The details are all implemented in the 
    model class above.
    
    """
    MODEL_TYPE = "ngram"
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
        ModuleOption('estimator', filter=choose_from_dict(ESTIMATORS), 
            help_text="A way of constructing a probability model given "\
                "the set of counts from the data. Default is to use "\
                "laplace (add-one) smoothing.",
            usage="estimator=X, where X is one of: %s" % ", ".join(ESTIMATORS.keys()), 
            default=laplace_estimator),
        get_chord_mapping_module_option(),
    ] + BackoffModel.TRAINING_OPTIONS
    
    def __init__(self, model_name, model=None, grammar=None, *args, **kwargs):
        super(HmmPathModel, self).__init__(model_name, *args, **kwargs)
        self.model = model
        self.grammar = grammar
        
        if self.options['n'] <= self.options['backoff']:
            # This is not allowed
            # We can only back off n-1 orders for an n-gram model
            raise TaggingModelError, "tried to load an n-gram model with "\
                "more orders of backoff than are possible (backing off "\
                "%d orders on a %d-gram model)" % \
                    (self.options['backoff'], self.options['n'])
                    
    def train(self, data, grammar=None, logger=None):
        if grammar is None:
            from jazzparser.grammar import get_grammar
            # Load the default grammar
            grammar = get_grammar()
        
        model = HmmPathNgram.train(data, self.options['estimator'], grammar, 
                                   cutoff=self.options['cutoff'], 
                                   chord_map=self.options['chord_mapping'],
                                   order=self.options['n'],
                                   backoff_orders=self.options['backoff'])
        self.model = model
        
        # Add some model-specific info into the descriptive text
        #  so we know how it was trained
        est_name = get_estimator_name(self.options['estimator'])
        self.model_description = """\
Model order: %(order)d
Backoff orders: %(backoff)d
Probability estimator: %(est)s
Zero-count threshold: %(cutoff)d
Training sequences: %(seqs)d
Training samples: %(samples)d\
""" % \
            {
                'est' : est_name,
                'seqs' : len(data),
                'samples' : sum([len(s) for s in data], 0),
                'order' : self.options['n'],
                'backoff' : self.options['backoff'],
                'cutoff' : self.options['cutoff'],
            }
        
    @staticmethod
    def _load_model(data):
        model = HmmPathNgram.from_picklable_dict(data['model'])
        name = data['name']
        return HmmPathModel(name, model=model)
    
    def _get_model_data(self):
        data = {
            'name' : self.model_name,
            'model' : self.model.to_picklable_dict()
        }
        return data
        
    def forward_probabilities(self, sequence):
        """ Interface to the NgramModel's forward_probabilities """
        return self.model.forward_probabilities(sequence)
        
    def forward_backward_probabilities(self, sequence):
        return self.model.normal_forward_backward_probabilities(sequence)
        
    def viterbi_probabilities(self, sequence):
        return self.model.viterbi_selector_probabilities(sequence)
        
    def viterbi_paths(self, sequence, paths=None):
        return self.model.generalized_viterbi(sequence, N=paths)
        
    def _get_labels(self):
        return self.model.label_dom
    labels = property(_get_labels)
    
    ############ Parameter output ###########
    def _get_readable_parameters(self):
        """ Produce a human-readable repr of the params of the model """
        buff = StringIO()
        model = self.model
        
        try:
            # Include the stored model description
            print >>buff, self.model_description
            print >>buff, "\nNum emissions: %d" % model.num_emissions
                
            print >>buff, "\nChord mapping: %s:" % model.chord_map.name
            for (crdin, crdout) in model.chord_map.items():
                print >>buff, "  %s -> %s" % (crdin, crdout)
            
            print >>buff, "\nPoint transition dist"
            for cond in sorted(model.point_transition_dist.conditions()):
                print >>buff, "  %s" % str(cond)
                for prob,samp in reversed(sorted(\
                        (model.point_transition_dist[cond].prob(interval),
                         interval) for \
                        interval in model.point_transition_dist[cond].samples())):
                    print >>buff, "    %s: %s " % (samp, prob)
            print >>buff
            
            print >>buff, "Function transition dist"
            for context in sorted(model.fn_transition_dist.conditions()):
                print >>buff, "  %s" % ",".join([str(s) for s in context])
                for prob,samp in reversed(sorted(\
                        (model.fn_transition_dist[context].prob(samp),
                         samp) for \
                        samp in model.fn_transition_dist[context].samples())):
                    print >>buff, "    %s: %s " % (samp, prob)
            print >>buff
            
            print >>buff, "Substition emission dist"
            for state in sorted(model.subst_emission_dist.conditions()):
                print >>buff, "  %s" % state
                for prob,subst in reversed(sorted(\
                        (model.subst_emission_dist[state].prob(subst),
                         subst) for \
                        subst in model.subst_emission_dist[state].samples())):
                    print >>buff, "    %s: %s " % (subst, prob)
            
            print >>buff, "Chord type emission dist"
            for state in sorted(model.type_emission_dist.conditions()):
                print >>buff, "  %s" % str(state)
                for prob,chord in reversed(sorted(\
                        (model.type_emission_dist[state].prob(chord),
                         chord) for \
                        chord in self.model.type_emission_dist[state].samples())):
                    print >>buff, "    %s: %s " % (chord, prob)
        except AttributeError, err:
            # Catch this, because otherwise it just looks like the attribute 
            #  (readable_parameters) doesn't exist (stupid Python behaviour)
            raise ValueError, "error generating model description "\
                            "(attribute error): %s" % err
        
        return buff.getvalue()
    readable_parameters = property(_get_readable_parameters)

class HmmPathBuilder(ModelBackoffBuilder):
    """
    Builds a semantics using an ngram model. Can take input from chord 
    sequences or a weighted lattice of chords.
    
    """
    MODEL_CLASS = HmmPathModel
    BUILDER_OPTIONS = ModelBackoffBuilder.BUILDER_OPTIONS + [
        ModuleOption('paths', filter=int, 
            help_text="Number of paths to suggest.",
            usage="paths=X, where X is an integer",
            default=10),
    ]
    INPUT_TYPES = ['db', 'chords', 'labels']

    def __init__(self, input, options={}, grammar=None, *args, **kwargs):
        super(HmmPathBuilder, self).__init__(input, options, *args, **kwargs)
        process_chord_input(self)
        
        if grammar is None:
            self.grammar = get_grammar()
        else:
            self.grammar = grammar
        
        #### Tag the input sequence ####
        self._tagged_data = []
        
        chord_map = self.model.model.chord_map
        if isinstance(self.wrapped_input, ChordInput):
            chords = self.wrapped_input.to_db_input().chords
            observations = [(chord.root, chord_map[chord.type]) for chord in 
                                chords]
            self.input = chords
        elif isinstance(self.wrapped_input, DbInput):
            observations = [(chord.root, chord_map[chord.type]) for chord in 
                                self.wrapped_input.chords]
        elif isinstance(self.wrapped_input, WeightedChordLabelInput):
            observations = lattice_to_emissions(input, chord_map=chord_map)
            
        # Use the ngram model to get tag probabilities for each input by 
        # computing the state occupation probability matrix
        path_probs = self.model.viterbi_paths(observations, self.options['paths'])
        
        self._paths = [
            self.grammar.formalism.backoff_states_to_lf(zip(states,self.times))
                    for states,prob in path_probs]
        # Set the probability on each result
        for path,(states,prob) in zip(self._paths,path_probs):
            path.probability = prob
            
    @property
    def num_paths(self):
        return len(self._paths)
            
    def get_tonal_space_path(self, rank=0):
        if rank >= len(self._paths):
            return None
        else:
            return self._paths[rank]
