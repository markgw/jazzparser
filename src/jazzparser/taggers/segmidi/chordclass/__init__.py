from __future__ import absolute_import
"""First suggested segmidi tagger, based on chord classes.

This is the first model structure presented in my 2nd-year review. It is 
based on the Raphael & Stoddard model and conditions emission distributions 
on chord classes.

@deprecated: this tagger is deprecated. I started doing some experiments 
    with it, but never concluded them, so it's not useable.

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

from cStringIO import StringIO
from jazzparser.taggers.segmidi.base import SegmidiTagger
from jazzparser.taggers.segmidi.chordclass.hmm import ChordClassHmm
from jazzparser.taggers.segmidi.chordclass.train import ChordClassBaumWelchTrainer
from jazzparser.taggers.segmidi.chordclass.tagutils import prepare_categories
from jazzparser.taggers.segmidi.midi import midi_to_emission_stream
from jazzparser.taggers.models import TaggerModel
from jazzparser.data.input import detect_input_type, MidiTaggerTrainingBulkInput
from jazzparser.utils.options import ModuleOption, choose_from_list
from jazzparser.utils.strings import str_to_bool
from jazzparser.utils.chords import int_to_chord_numeral
from jazzparser.utils.midi import note_ons
from . import tools

def _filter_illegal_transition_string(val):
    # Interpret a specification of illegal transitions in string form
    transitions = []
    for trans_string in val.split(","):
        trans_string = trans_string.strip()
        # This should be of the form SCHEMA-SCHEMA
        if "-" not in trans_string:
            raise ValueError, "illegal transition specification must be of "\
                "the form SCHEMA-SCHEMA. Could not understand %s" % trans_string
        schema0,__,schema1 = trans_string.partition("-")
        # Allow multiple alternative schemata to be given at once
        schema0s = schema0.split("|")
        schema1s = schema1.split("|")
        for schema0 in schema0s:
            for schema1 in schema1s:
                transitions.append((schema0,schema1))
    return transitions

def _filter_fixed_root_transition_string(val):
    # Interpret a specification of fixed root transition in string form
    transitions = {}
    for trans_string in val.split(","):
        trans_string = trans_string.strip()
        # This should be of the form SCHEMA-SCHEMA-ROOT_INTERVAL
        if trans_string.count("-") != 2:
            raise ValueError, "fixed root transition string must be of "\
                "the form SCHEMA-SCHEMA-ROOT_INTERVAL. Could not understand "\
                "%s" % trans_string
        schema0,__,rest = trans_string.partition("-")
        schema1,__,root = rest.partition("-")
        root = int(root)
        if root < 0 or root > 11:
            raise ValueError, "root interval must be in the range [0,11], got "\
                "%d" % root
        # Allow multiple alternative schemata to be given at once
        schema0s = schema0.split("|")
        schema1s = schema1.split("|")
        for schema0 in schema0s:
            for schema1 in schema1s:
                transitions[(schema0,schema1)] = root
    return transitions


class ChordClassTaggerModel(TaggerModel):
    """
    Model class to go with L{ChordClassMidiTagger}. This is where the real 
    meat of the model is implemented.
    
    """
    MODEL_TYPE = 'chordclass'
    TRAINING_OPTIONS = TaggerModel.TRAINING_OPTIONS + [
        # Initialization options
        ModuleOption('ccprob', filter=float,
            help_text="Initialization of the emission distribution.",
            usage="ccprob=P, P is a probability. Prob P is distributed "\
                "over the pitch classes that are in the chord class.",
            required=True),
        ModuleOption('metric', filter=str_to_bool,
            help_text="Create the model with a metrical component, as in the "\
                "original Raphael & Stoddard model",
            usage="metric=True, or metric=False (default False)",
            default=False),
        ModuleOption('contprob', filter=(float, choose_from_list(["learn"])),
            help_text="Continuation probability for transition initialization: "\
                "probability of staying in the same state between emissions. "\
                "Use value 'learn' to learn the self-transition probabilities "\
                "from the durations in the transition training data",
            usage="contprob=P, P is a probability or 'learn'",
            default=0.3),
        ModuleOption('maxnotes', filter=int,
            help_text="Maximum number of notes that can be generated from a "\
                "a state. Limit is required to make the distribution finite.",
            usage="maxnotes=N, N is an integer",
            default=100),
        ModuleOption('illegal_transitions', filter=_filter_illegal_transition_string,
            help_text="List of grammatical schema transitions (pairs) that "\
                "will be forced to have a 0 probability. You may specify "\
                "groups of schemata, separating each with a |",
            usage="illegal_transitions=X0-Y0,X1-Y1,... where Xs and Ys and "\
                "schema tags",
            default=[]),
        ModuleOption('fixed_roots', filter=_filter_fixed_root_transition_string,
            help_text="List of schema transitions that may have only one "\
                "non-zero probability root interval. You may specify "\
                "groups of schemata, separating each with a |",
            usage="fixed_roots=X0-Y0-R0,X1-Y1-R1,... where Xs and Ys and "\
                "schema tags and Rs are integers in [0,11]",
            default={}),
    # Also include the options for the baum-welch training
    ] + ChordClassBaumWelchTrainer.OPTIONS
    
    def __init__(self, model_name, *args, **kwargs):
        self.hmm = kwargs.pop('model', None)
        super(ChordClassTaggerModel, self).__init__(model_name, *args, **kwargs)
        
    def train(self, inputs, grammar=None, logger=None):
        """
        @type inputs: L{jazzparser.data.input.MidiTaggerTrainingBulkInput} or 
            list of L{jazzparser.data.input.Input}s
        @param inputs: training MIDI data. Annotated chord sequences should 
            also be given (though this is optional) by loading a 
            bulk db input file in the MidiTaggerTrainingBulkInput.
        
        """
        if grammar is None:
            from jazzparser.grammar import get_grammar
            # Load the default grammar
            grammar = get_grammar()
            
        if len(inputs) == 0:
            # No data - nothing to do
            return
        
        # Check the type of one of the inputs - no guarantee they're all the 
        #  same, but there's something seriously weird going on if they're not
        input_type = detect_input_type(inputs[0], allowed=['segmidi'])
        # Get the chord training data too if it's been given
        if isinstance(inputs, MidiTaggerTrainingBulkInput) and \
                inputs.chords is not None:
            chord_inputs = inputs.chords
        else:
            chord_inputs = None
        
        # Initialize the emission distribution for chord classes
        self.hmm = ChordClassHmm.initialize_chord_classes(
                    self.options['ccprob'],
                    self.options['maxnotes'],
                    grammar,
                    metric=self.options['metric'],
                    illegal_transitions=self.options['illegal_transitions'],
                    fixed_root_transitions=self.options['fixed_roots'])
        
        if chord_inputs:
            # If chord training data was given, initially train transition 
            #  distribution from this
            self.hmm.add_history("Training initial transition distribution "\
                                    "from annotated chord data")
            self.hmm.train_transition_distribution(chord_inputs, grammar, \
                                        contprob=self.options['contprob'])
        else:
            # Otherwise it gets left as a uniform distribution
            self.hmm.add_history("No annotated chord training data given. "\
                    "Transition distribution initialized to uniform.")
        
        # Get a Baum-Welch trainer to do the EM retraining
        # Pull out the options to pass to the trainer
        bw_opt_names = [opt.name for opt in ChordClassBaumWelchTrainer.OPTIONS]
        bw_opts = dict([(name,val) for (name,val) in self.options.items() \
                        if name in bw_opt_names])
        retrainer = ChordClassBaumWelchTrainer(self.hmm, options=bw_opts)
        # Prepare a callback to save
        def _get_save_callback():
            def _save_callback():
                self.save()
            return _save_callback
        save_callback = _get_save_callback()
        # Do the Baum-Welch training
        retrainer.train(inputs, logger=logger, save_callback=save_callback)
        
        self.model_description = """\
Initial chord class emission prob: %(ccprob)f
Initial self-transition prob: %(contprob)s
Metrical model: %(metric)s
""" % \
            {
                'ccprob' : self.options['ccprob'],
                'metric' : self.options['metric'],
                'contprob' : self.options['contprob'],
            }
        
    @staticmethod
    def _load_model(data):
        model = ChordClassHmm.from_picklable_dict(data['model'])
        name = data['name']
        return ChordClassTaggerModel(name, model=model)
    
    def _get_model_data(self):
        data = {
            'name' : self.model_name,
            'model' : self.hmm.to_picklable_dict()
        }
        return data
        
    def _get_readable_parameters(self):
        """ Produce a human-readable repr of the params of the model """
        buff = StringIO()
        
        print >>buff, "\nChord classes:\n%s" % ", ".join(\
                            [str(cc) for cc in self.hmm.chord_classes])
        print >>buff, "\nSchemata:\n%s" % ", ".join(sorted(self.hmm.schemata))
        print >>buff, "\nIllegal transitions (probabilities below will be "\
            "redistributed):\n%s" % ", ".join(["%s-%s" % labels for labels in \
            self.hmm.illegal_transitions])
        print >>buff, "\nFixed-root transitions:\n%s" % \
            "\n".join(["%s -> %s, %d" % (label0, label1, root) for \
                ((label0,label1), root) in sorted(self.hmm.fixed_root_transitions.items())])
        
        print >>buff, "\n*** Emission distributions ***"
        def _fmt_cond(cond):
            if self.hmm.metric:
                return "%s, %s, %s" % (cond[0], cond[1])
            else:
                # Don't bother showing the 2nd element: it's always 0
                return "%s" % (cond[0])
        # Output emission parameters
        em_dist = self.hmm.emission_dist
        for cond in sorted(em_dist.conditions()):
            print >>buff, "%s:" % _fmt_cond(cond)
            for (prob,samp) in reversed(sorted(\
                        [(em_dist[cond].prob(samp),samp) for \
                            samp in em_dist[cond].samples()])):
                print >>buff, "  %s: %s" % (samp, prob)
        
        print >>buff, "\n*** Transition distributions ***"
        print >>buff, "Schema transitions"
        # Output transition parameters
        schema_trans_dist = self.hmm.schema_transition_dist
        for label0 in sorted(schema_trans_dist.conditions()):
            print >>buff, "%s ->" % label0
            for (prob,samp) in reversed(sorted(\
                        [(schema_trans_dist[label0].prob(samp),samp) \
                            for samp in schema_trans_dist[label0].samples()])):
                print >>buff, "  %s: %s" % (samp, prob)
        
        print >>buff, "\nRoot transitions"
        root_trans_dist = self.hmm.root_transition_dist
        for label0,label1 in sorted(root_trans_dist.conditions()):
            # Don't show the distribution for transitions where the schema 
            #  transition is forced to have 0 probability
            if (label0,label1) in self.hmm.illegal_transitions:
                print >>buff, "%s -> %s illegal" % (label0, label1)
            elif (label0,label1) in self.hmm.fixed_root_transitions:
                # Show a special case for the constrained transitions
                print >>buff, "%s -> %s, only %d" % (label0,label1,\
                        self.hmm.fixed_root_transitions[(label0,label1)])
            else:
                print >>buff, "%s -> %s," % (label0, label1)
                for (prob,samp) in reversed(sorted(\
                            [(root_trans_dist[(label0,label1)].prob(samp),samp) \
                                for samp in root_trans_dist[(label0,label1)].samples()])):
                    print >>buff, "  %s: %s" % (samp, prob)
        
        print >>buff, "\n*** Initial state distribution ***"
        init_dist = self.hmm.initial_state_dist
        for (prob,label) in reversed(sorted(\
                            [(init_dist.prob(label),label) for \
                                label in init_dist.samples()])):
            print >>buff, "%s: %s" % (label, prob)
        
        return buff.getvalue()
    readable_parameters = property(_get_readable_parameters)
    
    def __get_description(self):
        """ Overridden to add history onto description. """
        if self.model_description is not None:
            model_desc = "\n\n%s" % self.model_description
        else:
            model_desc = ""
        return "%s%s\nModel history:\n%s" % \
                (self._description,model_desc,self.hmm.history)
    description = property(__get_description)

class ChordClassMidiTagger(SegmidiTagger):
    MODEL_CLASS = ChordClassTaggerModel
    TAGGER_OPTIONS = SegmidiTagger.TAGGER_OPTIONS + [
        ModuleOption('decoden', filter=int, 
            help_text="Number of best categories to consider for each timestep",
            usage="decoden=N, where N is an integer",
            default=5),
    ]
    shell_tools = SegmidiTagger.shell_tools + [
        tools.StateGridTool()
    ]
    
    def __init__(self, *args, **kwargs):
        SegmidiTagger.__init__(self, *args, **kwargs)
        grammar = self.grammar
        
        # Prepare the input data to get the observations in the required form
        emissions = midi_to_emission_stream(self.input, 
                                            metric=self.model.hmm.metric,
                                            remove_empty=False)
        
        # Use the hmm model to get tag probabilities for each input by 
        # computing n-best viterbi
        N = self.options['decoden']
        # Get the N-best tags for each timestep
        gamma = self.model.hmm.compute_gamma(emissions[0])
        # Match up the elements in the array with their labels
        T = gamma.shape[0]
        probabilities = []
        for t in range(T):
            timeprobs = {}
            for i,label in enumerate(self.model.hmm.label_dom):
                timeprobs[label] = gamma[t,i]
            probabilities.append(timeprobs)
        
        top_tags = []
        for time,probs in enumerate(probabilities):
            ranked = list(reversed(sorted(\
                    [(prob,(schema,root)) for ((schema,root,chord_class),prob) in probs.items()])))
            top_tags.append(ranked[:N])
        self.top_tags = top_tags
        
        # Process the tags to add spans for repeated tags
        spans = prepare_categories(top_tags)
        # Each spanset is a priority group of spans
        category_sets = []
        added_spans = []
        for spanset in spans:
            categories = []
            # Get a category for each span by its tag
            for start,end,(log_prob,(schema,root)) in spanset:
                # For now just use the start cell as the time value
                # TODO: maybe use the midi tick time??
                new_cats = [
                    (start,
                     end,
                     (category,schema,2**log_prob)) \
                        for category in \
                            grammar.get_signs_for_tag(schema, 
                                    {'root' : root, 'time' : start })]
                # Don't add the same category twice to the same span
                # This can happen because some (schema,root) pairs map to the 
                #  same category
                for new_cat in new_cats:
                    if (start,end,new_cat[2][0]) not in added_spans:
                        categories.append(new_cat)
                        added_spans.append((start,end,new_cat[2][0]))
            category_sets.append(categories)
        self.category_sets = category_sets
    
    def get_signs(self, offset=0):
        if offset >= len(self.category_sets):
            return []
        else:
            return self.category_sets[offset]
