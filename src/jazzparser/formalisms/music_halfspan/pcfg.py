"""Special bindings to the music_halfspan formalism required by the PCFG parser.

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

import copy
from StringIO import StringIO
from nltk.probability import ConditionalProbDist

from jazzparser import settings
from jazzparser.data import Chord
from jazzparser.data.input import DbInput, ChordInput
from jazzparser.grammar import get_grammar
from jazzparser.data.input import DbInput
from jazzparser.parsers.pcfg.model import PcfgModel, ModelError, \
                            ModelTrainingError
from jazzparser.utils.nltk.probability import CutoffConditionalFreqDist, \
                            CutoffFreqDist, mle_estimator, ESTIMATORS, \
                            laplace_estimator, get_estimator_name, \
                            generate_from_prob_dist
from jazzparser.utils.nltk.storage import object_to_dict, dict_to_object
from jazzparser.utils.options import ModuleOption, choose_from_dict
from jazzparser.utils.strings import str_to_bool
from jazzparser.utils.loggers import create_dummy_logger
from jazzparser.taggers.chordmap import get_chord_mapping_module_option, \
                            get_chord_mapping
from jazzparser.taggers.pretagged import PretaggedTagger
from jazzparser.parsers.cky import DirectedCkyParser
from jazzparser.data.trees import build_tree_for_sequence, TreeBuildError
from jazzparser.formalisms.music_halfspan.syntax import syntax_from_string

class HalfspanPcfgModel(PcfgModel):
    """
    A simple implementation of the PcfgModel interface. The model just 
    uses counts to compute the probabilities, with only very simple 
    smoothing.
    
    By default, unary expansions are fobidden, since our grammar doesn't 
    use them. If you want to allow them, set C{unary_expansions=True}.
    
    """
    MODEL_TYPE = "halfspan"
    TRAINING_OPTIONS = PcfgModel.TRAINING_OPTIONS + [
        ModuleOption('cutoff', filter=int, 
            help_text="In estimating probabilities, treat any counts below "\
                "cutoff as zero",
            usage="cutoff=X, where X is an integer", 
            default=0),
        ModuleOption('cat_bins', filter=int, 
            help_text="Number of possible categories used in estimating "\
                "probabilities. When using smoothing, this will determine "\
                "mass reserved for unseen categories. Has no effect if using "\
                "mle. Overrides the value given in the grammar definition, "\
                "which will be used by default.",
            usage="cat_bins=X, where X is an integer", 
            default=None),
        ModuleOption('estimator', filter=choose_from_dict(ESTIMATORS), 
            help_text="A way of constructing a probability model given "\
                "the set of counts from the data. Default is to use "\
                "laplace (add-one) smoothing.",
            usage="estimator=X, where X is one of %s" % ", ".join(ESTIMATORS.keys()), 
            default=laplace_estimator),
        ModuleOption('lexical', filter=str_to_bool, 
            help_text="Whether the model generates actual lexical entries, "\
                "or just lexical categories. By default, models are lexical, "\
                "but when using a model in combination with a tagger, it's "\
                "sometimes desirable to let the PCCG model only the category "\
                "generation.",
            usage="lexical=B, where B is a boolean",
            default=True),
        # Add the standard chord mapping option ("chord_mapping")
        get_chord_mapping_module_option(),
    ]
    # Force non-lexical model for some input types
    LEX_INPUT_TYPES = [
        DbInput, ChordInput
    ]
    
    def __init__(self, name, cutoff=0, cat_bins=None, 
            estimator=laplace_estimator, lexical=True, chordmap=None, 
            parent_counts=None, expansion_type_counts=None, 
            head_expansion_counts=None, non_head_expansion_counts=None, 
            lexical_counts=None, **kwargs):
        if cat_bins is None:
            raise ValueError, "cat_bins must be specified"
        if chordmap is None:
            raise ValueError, "chordmap must be specified"
        
        self.cutoff = cutoff
        self.cat_bins = cat_bins
        self._estimator = estimator
        self.lexical = lexical
        self.chordmap = chordmap
        self.word_bins = 12*len(set(self.chordmap.values()))
        
        super(HalfspanPcfgModel, self).__init__(name, **kwargs)
        
        ## Prepare the distributions from the counts
        if parent_counts is None:
            parent_counts = CutoffFreqDist(cutoff)
        self._parent_counts = parent_counts
        self._parent_dist = estimator(parent_counts, cat_bins)
        if expansion_type_counts is None:
            expansion_type_counts = CutoffConditionalFreqDist(cutoff)
        self._expansion_type_counts = expansion_type_counts
        # 2 possible expansions: right and leaf
        # If it becomes possible to have more (e.g. unary), set this somehow
        self._expansion_type_dist = ConditionalProbDist(expansion_type_counts, 
                                                        estimator, 2)
        if head_expansion_counts is None:
            head_expansion_counts = CutoffConditionalFreqDist(cutoff)
        self._head_expansion_counts = head_expansion_counts
        self._head_expansion_dist = ConditionalProbDist(head_expansion_counts,
                                                    estimator, cat_bins)
        if non_head_expansion_counts is None:
            non_head_expansion_counts = CutoffConditionalFreqDist(cutoff)
        self._non_head_expansion_counts = non_head_expansion_counts
        self._non_head_expansion_dist = ConditionalProbDist(
                        non_head_expansion_counts, estimator, cat_bins)
        if lexical_counts is None:
            lexical_counts = CutoffConditionalFreqDist(cutoff)
        self._lexical_counts = lexical_counts
        self._lexical_dist = ConditionalProbDist(lexical_counts, 
                                    estimator, self.word_bins)
        
    def chord_observation(self, chord):
        """
        Returns the string observation counted for a given chord.
        Note that the chord should already have been made relative to its parent.
        
        """
        return "%s%s" % (chord.root_numeral, self.chordmap[chord.type])
        
    def _get_model_data(self):
        data = {
            'parents' : object_to_dict(self._parent_counts),
            'expansions' : object_to_dict(self._expansion_type_counts),
            'heads' : object_to_dict(self._head_expansion_counts),
            'non_heads' : object_to_dict(self._non_head_expansion_counts),
            'words' : object_to_dict(self._lexical_counts),
            'cutoff' : self.cutoff,
            'cat_bins' : self.cat_bins,
            'estimator': self._estimator,
            'grammar' : self.grammar,
            'lexical' : self.lexical,
            'chordmap' : self.chordmap.name,
        }
        return data
        
    @staticmethod
    def _load_model(name, data):
        obj = HalfspanPcfgModel(
                name = name,
                cutoff = data['cutoff'],
                cat_bins = data['cat_bins'],
                estimator = data['estimator'],
                lexical = data.get('lexical', True),
                chordmap = get_chord_mapping(data.get('chordmap', None)),
                parent_counts = dict_to_object(data['parents']),
                expansion_type_counts = dict_to_object(data['expansions']),
                head_expansion_counts = dict_to_object(data['heads']),
                non_head_expansion_counts = dict_to_object(data['non_heads']),
                lexical_counts = dict_to_object(data['words']),
                grammar = data['grammar'],
            )
        return obj
        
    def inside_probability(self, expansion, parent, left, right=None):
        """
        Probability of a (non-leaf) subtree, computed from the probability 
        of its expansions. This doesn't include the probabilities 
        of the subtrees of the daughters. To get the full inside probability, 
        multiply the returned value with the daughters' insider probabilities.
        
        """
        parent_rep = model_category_repr(parent.category)
        # Get the probability of the expansion type
        exp_prob = self._expansion_type_dist[parent_rep].prob(expansion)
        
        if expansion == 'leaf':
            # Get the probability of the word given parent
            # If the model doesn't generate words, this probability is 1
            if not self.lexical:
                word_prob = 1.0
            else:
                # In this case the word is given as the left branch
                word = left
                # Word should be a chord label: interpret it as such
                chord = Chord.from_name(word)
                chord_obs = self.chord_observation(
                                category_relative_chord(chord, 
                                                category=parent.category))
                word_prob = self._lexical_dist[parent_rep].prob(chord_obs)
            return exp_prob * word_prob
        else:
            # We currently only recognise one other case: right-head
            assert right is not None, "pcfg model only supports binary branches"
            head = right
            non_head = left
            # Get the probability of the head (right) daughter given the parent
            condition = (expansion, parent_rep)
            head_rep = model_category_repr(head.category, parent.category)
            head_prob = self._head_expansion_dist[condition].prob(head_rep)
            # Get the probability of the non-head daughter given the 
            #  parent and the head daughter
            condition = (head_rep, expansion, parent_rep)
            non_head_rep = model_category_repr(non_head.category, parent.category)
            non_head_prob = \
                self._non_head_expansion_dist[condition].prob(non_head_rep)
            return exp_prob * head_prob * non_head_prob
    
    def outside_probability(self, parent):
        """
        Outer probability of a subtree. This is approximated in these models 
        as the prior probability of the parent of the tree.
        
        Prior probability P(parent) is used to approximate the outside 
        probability.
        
        """
        cat = model_category_repr(parent.category)
        return self._parent_dist.prob(cat)
            
    def description(self):
        buff = StringIO()
        def _fdist_str(fd):
            return "FDist<%d>: %s" % (fd.N(), ", ".join("%s:%d" % pr for pr in fd.items()))
        def _cfd_str(cfd):
            fds = [(cond,cfd[cond]) for cond in cfd.conditions()]
            # Sort by N of each FD
            fds = reversed(sorted(fds, key=lambda (c,fd): fd.N()))
            return "\n".join("%s: %s" % (cond, _fdist_str(fd)) for (cond,fd) in fds)
        
        print >>buff, "Parent distribution:"
        print >>buff, _fdist_str(self._parent_counts)
        print >>buff
        print >>buff, "Expansion type distribution:"
        print >>buff, _cfd_str(self._expansion_type_counts)
        print >>buff
        print >>buff, "Head expansion distribution:"
        print >>buff, _cfd_str(self._head_expansion_counts)
        print >>buff
        print >>buff, "Non-head expansion distribution:"
        print >>buff, _cfd_str(self._non_head_expansion_counts)
        print >>buff
        print >>buff, "Lexical expansion distribution:"
        print >>buff, _cfd_str(self._lexical_counts)
        print >>buff
        print >>buff, "Possible words: %d" % self.word_bins
        print >>buff, "Possible categories: %d" % self.cat_bins
        print >>buff
        print >>buff, "Estimator: %s" % get_estimator_name(self._estimator)
        print >>buff, "Frequency cutoff: %d" % self.cutoff
        return buff.getvalue()
    
    @staticmethod
    def train(name, training_data, options, grammar=None, logger=None):
        if grammar is None:
            grammar = get_grammar()
        if logger is None:
            logger = create_dummy_logger()
        
        # If cat_bins wasn't given, read it from the grammar
        if options["cat_bins"]:
            cat_bins = options["cat_bins"]
        elif grammar.max_categories:
            cat_bins = grammar.max_categories
        else:
            # Nothing given in the grammar either: error
            raise ValueError, "no value was given for cat_bins and the "\
                "grammar doesn't supply one"
        
        # Create a new model with empty distributions
        model = HalfspanPcfgModel(
                    name,
                    cutoff = options['cutoff'], 
                    cat_bins = cat_bins, 
                    estimator = options['estimator'], 
                    lexical = options['lexical'], 
                    chordmap = options['chord_mapping'],
                    grammar = grammar)
        
        # Add counts to this model for each sequence
        for sequence in training_data:
            try:
                model._sequence_train(sequence)
            except ModelTrainingError, err:
                logger.warn("Error training on %s: %s" % (sequence.string_name, 
                                                          err))
        
        return model
        
    def _sequence_train(self, sequence):
        """
        Adds counts to the model for a single chord sequence.
        
        """
        # Prepare the input and annotations
        input = DbInput.from_sequence(sequence)
        categories = [chord.category for chord in sequence.iterator()]
        str_inputs = input.inputs
        # Build the implicit normal-form tree from the annotations
        try:
            tree = build_tree_for_sequence(sequence)
        except TreeBuildError, err:
            raise ModelTrainingError, "could not build a tree for '%s': %s" % \
                (sequence.string_name, err)
        
        def _add_counts(trace):
            """ Add counts to the model from a derivation trace """
            parent = trace.result
            # Add a count for the parent category
            parent_rep = model_category_repr(parent.category)
            self._parent_counts.inc(parent_rep)
            
            if len(trace.rules) == 0:
                # Leaf node - lexical generation
                # Count this parent expanding as a leaf
                self._expansion_type_counts[parent_rep].inc('leaf')
                # Interpret the word as a chord
                chord = Chord.from_name(trace.word)
                chord = category_relative_chord(chord, parent.category)
                observation = self.chord_observation(chord)
                # Count this parent producing this word
                # The chord root is now relative to the base pitch of the category
                self._lexical_counts[parent_rep].inc(observation)
            else:
                # Internal node - rule application
                # There should only be one rule application, but just in case...
                for rule,args in trace.rules:
                    if rule.arity == 1:
                        # Unary rule
                        raise ModelTrainingError, "we don't currently support "\
                            "unary rule application, but one was found in "\
                            "the training data"
                    if rule.arity == 2:
                        # Binary rule
                        # Assume all heads come from the right
                        expansion = 'right'
                        self._expansion_type_counts[parent_rep].inc(expansion)
                        # Count this parent expanding to the head daughter
                        head_rep = model_category_repr(args[1].result.category, 
                                                            parent.category)
                        self._head_expansion_counts[
                                        (expansion,parent_rep)].inc(head_rep)
                        # Count this parent with this head expansion expanding
                        #  to the non-head daughter
                        non_head_rep = model_category_repr(
                                        args[0].result.category, parent.category)
                        self._non_head_expansion_counts[
                                    (head_rep,expansion,parent_rep)
                                                        ].inc(non_head_rep)
                    # Recurse to count derivations from the daughters
                    for arg in args:
                        _add_counts(arg)
        
        # The root of this structure is an extra node to contain all separate 
        #  trees. If there's more than one tree, it represents partial parses
        end = 0
        successes = 0
        num_trees = 0
        for sub_tree in tree.children:
            # Use each partial tree to get counts
            length = sub_tree.span_length
            start = end
            end += length
            
            # If this is just a leaf, ignore it - it came from an unlabelled chord
            if not hasattr(sub_tree, 'chord'):
                num_trees += 1
                # Prepare the tagger for this part of the sequence
                # Get a sign for each annotated chord
                tags = []
                for word,tag in zip(str_inputs[start:end],categories[start:end]):
                    if tag == "":
                        word_signs = []
                    elif tag not in self.grammar.families:
                        raise ModelTrainingError, "could not get a sign from "\
                            "the grammar for tag '%s' (chord '%s')" % \
                            (tag, word)
                    else:
                        # Get all signs that correspond to this tag from the grammar
                        word_signs = self.grammar.get_signs_for_word(word, tags=[tag])
                    tags.append(word_signs)
                
                tagger = PretaggedTagger(self.grammar, input.slice(start,end), tags=tags)
                # Use the directed parser to parse according to this tree
                parser = DirectedCkyParser(self.grammar, tagger, derivation_tree=sub_tree)
                try:
                    parser.parse(derivations=True)
                except DirectedParseError, err:
                    # Parse failed, so we can't train on this sequence
                    logger.error("Parsing using the derivation tree failed: "\
                        "%s" % err)
                    continue
                
                # We should now have a complete parse available
                parses = parser.chart.parses
                if len(parses) > 1:
                    raise ModelTrainingError, "the annotated tree gave multiple "\
                        "parse results: %s" % ", ".join(["%s" % p for p in parses])
                parse = parses[0]
                # Hooray! We have a parse!
                # Now use the derivation trace to add counts to the model
                # Store the counts in the model recursively
                _add_counts(parse.derivation_trace)
                successes += 1
    
    def generate(self, logger=None, max_depth=None):
        """
        Generate a chord sequence from the model.
        
        """
        if logger is None:
            logger = create_dummy_logger()
        
        def _generate(parent, depth=0, pitch=0):
            # Transform the parent category so it's relative to itself
            # All generated categories will be relative to this, 
            #  so we need to make the parent self-relative at the 
            #  start of each recursion
            parent_rep = model_category_repr(parent)
            parent_pitch = (pitch + base_pitch(parent)) % 12
            logger.debug("%sGenerating from parent: %s" % (" "*depth,parent_rep))
            
            if max_depth is not None and depth >= max_depth and \
                        len(self._lexical_dist[parent_rep].samples()) != 0:
                # Don't go any deeper than this if we can stop here
                # Only possible if the parent has generated a leaf before
                exp = 'leaf'
                logger.debug("%sForcing leaf" % (" "*depth))
            else:
                # Otherwise freely generate an expansion type
                exp = generate_from_prob_dist(self._expansion_type_dist[parent_rep])
                logger.debug("%sExpansion: %s" % (" "*depth, exp))
                exp_parent = (exp,parent_rep)
            
            if exp == 'leaf':
                # Generate a leaf node (word)
                word = generate_from_prob_dist(self._lexical_dist[parent_rep])
                logger.debug("%sWord: %s, pitch: %d" % (" "*depth, word, parent_pitch))
                chord = Chord.from_name(word)
                chord.root = (chord.root + parent_pitch) % 12
                return [chord]
            else:
                # First generate a head node
                head = generate_from_prob_dist(self._head_expansion_dist[exp_parent])
                logger.debug("%sHead: %s" % (" "*depth, head))
                # Continue to expand this recursively to a word sequence
                head_generated = _generate(head, depth=depth+1, \
                                                            pitch=parent_pitch)
                
                head_exp_parent = (head,exp,parent_rep)
                # Now generate a non-head node
                non_head = generate_from_prob_dist(
                            self._non_head_expansion_dist[head_exp_parent])
                logger.debug("%sNon-head: %s" % (" "*depth, non_head))
                # Continue to expand this too
                non_head_generated = _generate(non_head, depth=depth+1, \
                                                            pitch=parent_pitch)
                
                return non_head_generated + head_generated
    
        # Choose a start node
        # Build a I^T-I^T as the root
        root = syntax_from_string("I^T-I^T")
        logger.debug("Root: %s" % root)
        return _generate(root)


def model_category_repr(category, base_category=None):
    """
    Given a syntactic category, generates a representation that will 
    be used by the model. The result should be a string and must 
    uniquely identify all of the features of the category that the 
    model should distinguish.
    
    If base_category is given, it may be used as a base to compare the 
    category to. In this case, observations of generated categories 
    always take their parent as a base category and syntactic pitches 
    are all relative to it.
    
    If base_category is not given, the category itself will be 
    considered the base category.
    
    """
    from .syntax import make_absolute_category_from_relative
    
    category = category.copy()
    if base_category is None:
        base_category = category
    # Get a root from the base category
    root = base_pitch(base_category)
    if root is None:
        # No root pitch found in the base category
        # Just make the category itself relative to its own root
        root = base_pitch(category)
        # If root is still None, it doesn't matter - there are no roots to adjust
    
    if root is not None:
        # The function used below adds a cat's root to the base:
        #  we want to subtract - i.e. make a relative category from 
        #  an absolute
        root_pitch = (12 - root) % 12
        # Make the category's roots all relative to this base root
        make_absolute_category_from_relative(category, root_pitch)
    
    return category

def base_pitch(cat):
    """
    Arbitrarily picks a root out of the category, so that we can take 
    the rest of the category and other categories relative to this 
    consistently picked root.
    
    """
    from .syntax import AtomicCategory, ComplexCategory
    if isinstance(cat, AtomicCategory):
        # Use the start part of the category as the root
        return cat.from_half.root
    elif isinstance(cat, ComplexCategory):
        # Get a root from the left side of the slash
        return cat.result.root
    else:
        raise TypeError, "category given to base_pitch was neither "\
            "complex nor atomic. Type was %s" % (type(cat).__name__)

def category_relative_chord(chord, category=None):
    """
    Returns a version of the Chord object that's relative to the base 
    pitch of the category. If no category is given, the chord returned 
    will be rooted at I (i.e. relative to itself).
    
    """
    if category is not None:
        base = base_pitch(category)
        if base is None:
            base = chord.root
    else:
        base = chord.root
    chord_rel = copy.deepcopy(chord)
    chord_rel.root -= base
    return chord_rel
