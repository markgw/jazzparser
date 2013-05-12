"""Tagger to combine a chord labeling model with a chord-input supertagger.

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

from jazzparser.taggers.tagger import Tagger
from jazzparser.taggers.ngram_multi.tagger import MultiChordNgramTagger
from jazzparser.taggers.fail.tagger import FailTagger
from jazzparser.misc.chordlabel.hmm import HPChordLabeler
from jazzparser.misc.chordlabel.midi import midi_to_emission_stream
from jazzparser.utils.options import ModuleOption, new_file_option
from jazzparser.data.db_mirrors import Chord
from jazzparser.data.input import DbInput, NullInput
from jazzparser.utils.strings import str_to_bool
from . import tools

class ChordLabelNgramTagger(Tagger):
    """
    Tagger that loads a chord labeling model to assign chord labels to MIDI 
    data, then hands over to a chord supertagger to process the output of 
    the labeler.
    
    """
    COMPATIBLE_FORMALISMS = ['music_halfspan']
    TAGGER_OPTIONS = MultiChordNgramTagger.TAGGER_OPTIONS + [
        ModuleOption('labeling_model', 
            help_text="Model name for chord labeler",
            usage="labeling_model=M, where M is a trained chord labeling model",
            required=True),
        ModuleOption('partition_labeler', filter=str_to_bool,
            help_text="By default, the chord labeling model is not loaded "\
                "with a partition number, even if the supertagging model is. "\
                "If this is True, the same partition number will be used for "\
                "the labeler's model as was given to the supertagger.",
            usage="partition_labeler=B, where B is True or False",
            default=False),
        ModuleOption('latticen', filter=int, 
            help_text="Number of chords per segment to get in the lattice",
            usage="latticen=N, where N is an integer",
            default=3),
        ModuleOption('lattice_beam', filter=float, 
            help_text="Beam ratio to apply to the chord lattice. Removes all "\
                "chord labels with probability < ratio * highest probability "\
                "in timestep. Default: 1e-5",
            usage="lattice_beam=F, where F is a float < 1.0 (e.g. 1e-6)",
            default=1e-5),
        ModuleOption('label_viterbi', filter=str_to_bool, 
            help_text="Use Viterbi decoding instead of forward-backward. "\
                "Only one chord will be returned for every timestep, no "\
                "matter what latticen is. Default: False",
            usage="viterbi=B, where B is True or False",
            default=False),
        ModuleOption('only_label', filter=str_to_bool, 
            help_text="Run the labeller, but stop before running the tagger. "\
                "(For testing only - this is not actually useful.)",
            usage="only_label=B, where B is True or False",
            default=False),
        ModuleOption('label_output', filter=new_file_option, 
            help_text="Append the chord labelling to a file. All chord labels "\
                "in the lattice are output, separated by spaces, with one "\
                "chord per line",
            usage="label_output=F, where F is a filename"),
    ]
    INPUT_TYPES = ['segmidi']
    name = "chordlabel"
    shell_tools = Tagger.shell_tools + [
        tools.ChordLabelTool(),
    ]
    LEXICAL_PROBABILITY = True

    def __init__(self, grammar, input, options={}, logger=None, *args, **kwargs):
        Tagger.__init__(self, grammar, input, options, logger=logger)
        # Make a copy of the options that we will pass through to the tagger
        options = self.options.copy()
        # Remove the options that the tagger doesn't need
        labeling_model_name = options.pop('labeling_model')
        latticen = options.pop('latticen')
        beam_ratio = options.pop('lattice_beam')
        viterbi = options.pop('label_viterbi')
        partition_labeler = options.pop('partition_labeler')
        label_output = options.pop('label_output')
        only_label = options.pop('only_label')
        
        # Partition the labeling model if requested and a partition number 
        #  was given for the supertagger
        if partition_labeler and 'partition' in self.options and \
                    self.options['partition'] is not None:
            labeling_model_name += "%d" % self.options['partition']
        
        self.logger.info("Labeling model: %s" % labeling_model_name)
        # First run the chord labeler on the MIDI input
        # Load a labeling model
        labeler = HPChordLabeler.load_model(labeling_model_name)
        self.labeler = labeler
        # Get chord labels from the model: get a lattice of possible chords
        lattice = labeler.label_lattice(input, options={
                                                'n' : latticen, 
                                                'nokey' : True,
                                                'viterbi' : viterbi },
                                            corpus=True)
        # Store the lattice for later reference
        self.lattice = lattice
        # Also store the labeler's emission matrix
        emissions = midi_to_emission_stream(input, remove_empty=False)[0]
        self.labeler_emission_matrix = labeler.get_small_emission_matrix(emissions)
        # Beam the lattice to get rid of very low probability labels
        lattice.apply_ratio_beam(ratio=beam_ratio)
        
        if label_output:
            # Output the labelling to a file
            with open(label_output, 'a') as outfile:
                for chord_tags in lattice:
                    print >>outfile, " ".join(str(crd) for (crd,prob) in chord_tags)
        
        if only_label:
            self.tagger = FailTagger(grammar, NullInput())
        else:
            self.tagger = MultiChordNgramTagger(grammar, lattice, options, 
                                                 logger=logger, *args, **kwargs)
            self._lex_prob_cache = [{} for i in range(self.input_length)]
    
    def get_signs(self, offset=0):
        return self.tagger.get_signs(offset=offset)
        
    def get_word(self, index):
        return self.input[index]
    
    def get_string_input(self):
        return [str(i) for i in range(self.input_length)]
        
    def lexical_probability(self, start_time, end_time, span_label):
        """
        Lexical probabilities for a probabilistic parser. This will only 
        get used if the parsing model can't compute a probability itself 
        (i.e. in the case of MIDI input).
        
        """
        # Take product of emission probabilities for time steps in this range
        prob = 1.0
        for time in range(start_time, end_time):
            prob *= self.single_step_lexical_probability(time, span_label)
        return prob
    
    def single_step_lexical_probability(self, time, span_label):
        if span_label not in self._lex_prob_cache[time]:
            # Compute the lexical probability for this single time step
            # Consider each of the chord labels in the lattice at this time
            chord_probs = []
            for (chord,prob) in self.lattice[time]:
                # Get the emission probabilities for this chord form the 
                #  chord labeling model
                chord_label = self.labeler.chord_types.index(chord.model_label)
                # All keys have the same em prob, so we don't worry about that
                chord_em_prob = self.labeler_emission_matrix[time, chord.root, chord_label]
                # Get the probability of generating this chord label from 
                #  the supertagger's distributions
                tagger_label = self.tagger.model.chordmap[chord.label]
                tagger_em_prob = self.tagger.model.model.emission_probability(
                                        (chord.root,tagger_label), span_label)
                # Multiply these probabilities to get the probability of the 
                #  chord label and emission given the tag
                chord_probs.append(chord_em_prob * tagger_em_prob)
            # Sum over the chords in the lattice to get the probabilitiy of 
            #  the emission given the tag
            self._lex_prob_cache[time][span_label] = sum(chord_probs, 0.0)
        return self._lex_prob_cache[time][span_label]
