"""Combination of HmmPath with chord recognizer

Simple extension of baseline to MIDI input by getting a lattice from an 
HP chord labeler and decoding the baseline on the resulting lattice.

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

from jazzparser.utils.options import ModuleOption, ModuleOptionError
from jazzparser.grammar import get_grammar
from jazzparser.utils.strings import str_to_bool
from jazzparser.misc.chordlabel.hmm import HPChordLabeler

from .hmmpath import HmmPathBuilder
from ..base import BackoffBuilder

class MidiHmmPathBuilder(BackoffBuilder):
    """
    Use an HP chord labeler to get a chord lattice and HmmPath on the lattice.
    """
    MODEL_CLASS = None
    BUILDER_OPTIONS = HmmPathBuilder.BUILDER_OPTIONS + [
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
    ]
    INPUT_TYPES = ['segmidi']

    def __init__(self, input, options={}, grammar=None, *args, **kwargs):
        super(MidiHmmPathBuilder, self).__init__(input, options, *args, **kwargs)
        if grammar is None:
            self.grammar = get_grammar()
        else:
            self.grammar = grammar
        
        # Make a copy of the options that we will pass through to HmmPath
        options = self.options.copy()
        # Remove the options that the tagger doesn't need
        labeling_model_name = options.pop('labeling_model')
        latticen = options.pop('latticen')
        beam_ratio = options.pop('lattice_beam')
        viterbi = options.pop('label_viterbi')
        partition_labeler = options.pop('partition_labeler')
        
        # Use an HP chord labeler to label the MIDI data
        # Partition the labeling model if requested and a partition number 
        #  was given for the supertagger
        if partition_labeler and 'partition' in self.options and \
                    self.options['partition'] is not None:
            labeling_model_name += "%d" % self.options['partition']
        
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
        # Beam the lattice to get rid of very low probability labels
        lattice.apply_ratio_beam(ratio=beam_ratio)
        
        # Tag the lattice
        self.hmmpath = HmmPathBuilder(lattice, options, grammar, *args, **kwargs)
            
    @property
    def num_paths(self):
        return len(self.hmmpath._paths)
            
    def get_tonal_space_path(self, rank=0):
        if rank >= len(self.hmmpath._paths):
            return None
        else:
            return self.hmmpath._paths[rank]
