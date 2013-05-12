from __future__ import absolute_import
"""Wrappers for different types of input data.

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

import sys
from jazzparser.data import Fraction, Chord
from jazzparser.utils.options import ModuleOption
from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.utils.strings import str_to_bool, make_unique
from . import tools

class InputReader(object):
    """
    Superclass for all sorts of input. Specifically, this is the superclass 
    of L{Input} and L{BulkInput}. You should subclass these if creating a new 
    input type.
    
    This just provides the maintenance stuff common to L{Input} and 
    L{BulkInput}.
    
    """
    FILE_INPUT_OPTIONS = []
    SHELL_TOOLS = [ tools.InputTool() ]
    
    @classmethod
    def process_option_dict(cls, optdict):
        return ModuleOption.process_option_dict(optdict, cls.FILE_INPUT_OPTIONS)
    
    @staticmethod
    def from_file(filename, options={}):
        raise NotImplementedError, "called from_file() on abstract base class"

class Input(InputReader):
    """
    Superclass for different types of input wrapper.
    
    All of these methods should be overridden by subclasses.
    
    """
    def __init__(self, name=None):
        self.name = name
    
    def __str__(self):
        if self.name is not None:
            return "<input '%s'>" % self.name
        else:
            return "<input data>"
            
    def _get_string_name(self):
        if self.name is None:
            return "Unnamed sequence"
        else:
            return self.name
    string_name = property(_get_string_name)
    
    def __len__(self):
        raise NotImplementedError, "%s defines no len(). All input types "\
            "should." % type(self).__name__
    
    def __getitem__(self, item):
        raise NotImplementedError, "%s does not support indexing. All input "\
            "types should" % type(self).__name__
    
    def slice(self, start=None, end=None):
        """
        Subclasses should provide a way of slicing (taking a subsequence of)
        the input that returns an input of the original type.
        """
        raise NotImplementedError, "%s does not support slicing. All input "\
            "types should" % type(self).__name__
    
    def get_gold_analysis(self):
        """
        If the input includes a gold-standard analysis, this should return it.
        Otherwise, it will return None.
        
        """
        return

class NullInput(Input):
    """
    Input that's not an input. Used internally by the fail tagger and for 
    testing purposes.
    
    """
    def __str__(self):
        return "<null input>"
        
    def __len__(self):
        return 0
    
    def __getitem__(self, item):
        raise IndexError, "null input has no contents"
    
    def slice(self, start=None, end=None):
        return NullInput()

class DbInput(Input):
    """
    Wrapper for input from the database, rather than the command line.
    No point in reducing db input to a string, then reinterpreting it.
    
    If only one of C{times} and C{durations} is given, the other will 
    be computed from it. Computing C{times} from durations involves 
    assuming that the first chord occurs at time 0. Computing 
    C{durations} from C{times} involves assuming that the last chord 
    has a length of 1.
    
    At least one of C{times} and C{durations} must be given.
    
    We also store the id of the chord sequence that this came from (C{id}) and 
    the sequence representation itself (C{sequence}). This may be C{None} in 
    some cases.
    
    Confusingly (for historical reasons!), C{inputs} contains string chord 
    labels. C{chords} contains the db_mirrors representation of the chords.
    
    """
    FILE_INPUT_OPTIONS = [
        ModuleOption('index', filter=int, 
                     help_text="read the sequence with index (not id) X",
                     usage="index=X, where X is an int",
                     required=True),
    ]
    
    def __init__(self, inputs, durations=None, times=None, id=None, \
                    chords=None, sequence=None, *args, **kwargs):
        super(DbInput, self).__init__(*args, **kwargs)
        
        self.inputs = inputs
        self.durations = durations
        self.times = times
        self.id = id
        self.chords = chords
        self.sequence = sequence
        
        if durations is None and times is None:
            raise ValueError, "cannot create a DbInput with neither "\
                "times nor durations given"
        elif times is None:
            self.times = [sum(durations[:i]) for i in range(len(durations))]
        elif durations is None:
            from jazzparser.utils.base import group_pairs
            self.durations = [time1-time0 for (time1,time0) in group_pairs(times)] + [Fraction(1)]
    
    def get_gold_analysis(self):
        """
        Parses the annotations, if present, to get a gold analysis. Unlike 
        L{AnnotatedDbInput}, this input type cannot be assumed to have 
        annotations. It will therefore not raise an error if annotations 
        are missing or incomplete, but just return None.
        
        """
        from jazzparser.evaluation.parsing import parse_sequence_with_annotations
        from jazzparser.grammar import get_grammar
        from jazzparser.parsers import ParseError
        
        try:
            parses = parse_sequence_with_annotations(
                            self, get_grammar(), allow_subparses=False)
        except ParseError:
            return None
        else:
            return parses[0].semantics
    
    @staticmethod
    def from_sequence(seq):
        """
        Creates a DbInput from a database representation of a sequence.
        
        """
        chords = list(seq)
        inputs = [str(chord) for chord in chords]
        durations = [chord.duration for chord in seq]
        return DbInput(inputs, durations=durations, name=seq.string_name, \
                        id=seq.id, chords=chords, sequence=seq)
        
    def __str__(self):
        return " ".join(["%s" % i for i in self.inputs])
    
    def __len__(self):
        return len(self.inputs)
        
    def __getitem__(self, item):
        return self.inputs[item]
        
    def slice(self, start=None, end=None):
        if self.chords:
            chords = self.chords[start:end]
        else:
            chords = None
        return DbInput(self.inputs[start:end],
                       self.durations[start:end],
                       self.times[start:end],
                       id=self.id,
                       name=self.name,
                       chords=chords,
                       sequence=self.sequence)
        
    @staticmethod
    def from_file(filename, options={}):
        # Load up a sequence index file according to the filename
        seqs = SequenceIndex.from_file(filename)
        # Get a sequence by index from the file
        seq = seqs.sequence_by_index(options['index'])
        if seq is None:
            raise InputReadError("%d is not a valid sequence index in %s" % \
                (options['index'], filename))
        # Get the data from the sequence
        return DbInput.from_sequence(seq)
    
class WeightedChordLabelInput(Input):
    """
    Input wrapper for a lattice of chord labels, including a set of chord 
    labels for each timestep, each with a probability. The labels themselves 
    are similar to the chord in a L{DbInput} and are represented using 
    L{jazzparser.misc.chordlabel.data.ChordLabel}s.
    
    The lattice should be a list of timesteps. Each timestep should be a 
    list of (label,prob) tuples, where label is a C{ChordLabel} and prob is 
    a probability.
    
    """
    FILE_INPUT_OPTIONS = []
    
    def __init__(self, lattice, *args, **kwargs):
        super(WeightedChordLabelInput, self).__init__(*args, **kwargs)
        # Make sure the lattice entries are sorted
        self.lattice = [ \
            list(reversed(sorted(timestep, key=lambda x:x[1]))) for timestep in lattice]
        
    def __str__(self):
        return "<Lattice:%s\n>" % "".join(["\n  %d: %s" % (t, \
            ", ".join(["%s (%.2e)" % (label,prob) for (label,prob) in timestep])) \
                    for t,timestep in enumerate(self.lattice)])
    
    def __repr__(self):
        return "<Lattice (%d)>" % len(self)
    
    def __len__(self):
        return len(self.lattice)
        
    def __getitem__(self, item):
        return self.lattice[item]
        
    def slice(self, start=None, end=None):
        return WeightedChordLabelInput(self.lattice[start:end])
    
    def apply_ratio_beam(self, ratio=1e-4):
        """
        Applies a beam to remove all values from the lattice whose probability 
        is less than the given ratio of the highest probability for that 
        timestep.
        
        @type ratio: float
        @param ratio: the max ratio of a probability to the highest 
            probability in the timestep
        
        """
        for timestep in self:
            min_prob = timestep[0][1] * ratio
            # Check if any values have a prob small enough to remove
            to_remove = [i for i,val in enumerate(timestep) if val[1] < min_prob]
            # Get rid of all of these values
            for removed,index in enumerate(to_remove):
                timestep.pop(index-removed)
        
    @staticmethod
    def from_file(filename, options={}):
        # Load a lattice from a file by unpickling it
        import cPickle as pickle
        f = open(filename, 'r')
        lattice = pickle.load(f)
        return WeightedChordLabelInput(lattice)

class ChordInput(Input):
    """
    Input wrapper for textual chord input.
    
    This is the simplest type of input, usually taken from the command line.
    
    You must provide a list of chord symbols and either a list of durations 
    or a list of times when constructing this. To process pure text (which 
    includes computing durations/times and splitting up chords), use 
    L{ChordInput.from_string}.
    
    """
    FILE_INPUT_OPTIONS = [
        ModuleOption('roman', filter=str_to_bool, 
                     help_text="read chord symbols as roman numberals. "\
                        "Default is to assume note names",
                     usage="roman=B, where B is a boolean",
                     default=False),
    ]
    
    def __init__(self, inputs, durations=None, times=None, roman=False, 
                    *args, **kwargs):
        super(ChordInput, self).__init__(*args, **kwargs)
        
        self.inputs = inputs
        self.durations = durations
        self.times = times
        self.roman = roman
        
        # Compute the durations from times or vice versa
        if durations is None and times is None:
            raise ValueError, "cannot create a ChordInput with neither "\
                "times nor durations given"
        elif times is None:
            self.times = [sum(durations[:i], Fraction(0)) for i in range(len(durations))]
        elif durations is None:
            from jazzparser.utils.base import group_pairs
            self.durations = [time1-time0 for (time1,time0) in group_pairs(times)] + [Fraction(1)]
        
        # Convert all strings to internal chord representation
        # Done now so we check the chords can all be understood before doing 
        #  anything else
        self.chords = [
            Chord.from_name(name, roman=roman).to_db_mirror() for name in inputs
        ]
        for chord,dur in zip(self.chords, self.durations):
            chord.duration = dur
    
    @staticmethod
    def from_string(input, name="<string input>", roman=False):
        """
        Produce a wrapped-up version of the input directly from an input string, 
        which may come, for example, from the command line.
        
        """
        from jazzparser.utils.input import assign_durations, strip_input
        # Get durations from the original string before doing anything else
        durations = assign_durations(input)
        # Remove unwanted characters from the string
        input = strip_input(input)
        # Tokenise the string
        chords = input.split()
        return ChordInput(chords, durations=durations, name=name, roman=roman)
        
    def __str__(self):
        return " ".join(["%s" % i for i in self.inputs])
    
    def __len__(self):
        return len(self.inputs)
    
    def __getitem__(self, item):
        return self.inputs[item]
        
    def slice(self, start=None, end=None):
        return ChordInput(self.inputs[start:end],
                          self.durations[start:end],
                          self.times[start:end],
                          name=self.name)
        
    @staticmethod
    def from_file(filename, options={}):
        # Read the whole contents of the file
        f = open(filename, 'r')
        try:
            data = f.read()
        finally:
            f.close()
        # Just treat the whole file as one sequence
        return ChordInput.from_string(data, name="File: %s" % filename, 
                                        roman=options['roman'])
    
    def to_db_input(self):
        """
        This data type is useful for reading textual input. For internal 
        processing, however, it can be converted to a L{DbInput}, which 
        is generally more convenient to handle.
        
        """
        return DbInput(self.inputs, durations=self.durations, chords=self.chords)

class SegmentedMidiInput(Input):
    """
    Input wrapper for MIDI files with extra information about segmentation, 
    in the form it's needed for the Raphael and Stoddard model and midi 
    supertagging models: that is, offset (start of first bar) and bar length.
    
    Each segment is a midi L{midi.EventStream}. It also has the additional 
    attribute C{segment_start}, giving the tick time at which the segment 
    begins in the original midi stream.
    
    Optionally also stores a gold standard analysis in the form of a 
    db annotated chord sequence: see L{AnnotatedDbInput}.
    
    """
    FILE_INPUT_OPTIONS = [
        ModuleOption('time_unit', filter=float, 
                     help_text="number of beats (by the MIDI file resolution) "\
                        "to take to be one time unit",
                     usage="time_unit=X, where X is an int or float",
                     required=False,
                     default=4),
        ModuleOption('tick_offset', filter=int, 
                     help_text="time in MIDI ticks at which the first time "\
                        "unit begins",
                     usage="tick_offset=X, where X is an int",
                     required=False,
                     default=0),
        ModuleOption('truncate', filter=int, 
                     help_text="truncate the input to this length.",
                     usage="truncate=L, where L is an integer"),
    ]
    SHELL_TOOLS = Input.SHELL_TOOLS + [ 
        tools.PlayMidiChunksTool(),
        tools.PrintMidiChunksTool()
    ]
    
    def __init__(self, inputs, time_unit=4, tick_offset=0, stream=None, 
            gold=None, sequence_index=None, *args, **kwargs):
        """
        
        @type inputs: list of L{midi.EventStream}s
        @param stream: the midi data segments
        @type time_unit: int or float
        @param time_unit: number of beats to take as the basic unit 
            of time for observations
        @type tick_offset: int
        @param tick_offset: number of ticks after which the first bar begins
        
        """
        super(SegmentedMidiInput, self).__init__(*args, **kwargs)
        
        self.stream = stream
        self.time_unit = time_unit
        self.tick_offset = tick_offset
        self.inputs = inputs
        self.gold = gold
        self.sequence_index = sequence_index
        
        self.tick_unit = int(stream.resolution*time_unit)
        
    def __len__(self):
        return len(self.inputs)
        
    def __getitem__(self, item):
        return self.inputs[item]
        
    def __str__(self):
        if self.name is not None:
            return "<MIDI: %s (%d)>" % (self.name, len(self))
        else:
            return "<MIDI: %d chunks>" % len(self)
        
    def slice(self, start=None, end=None):
        return SegmentedMidiInput(self.inputs[start:end],
                                  durations=self.durations[start:end],
                                  times=self.times[start:end],
                                  name=self.name,
                                  stream=self.stream,
                                  sequence_index=self.sequence_index)
    
    def get_gold_analysis(self):
        # This may be None if no analysis was in the input
        return self.gold
    
    @staticmethod
    def from_file(filename, options={}, gold=None, sequence_index=None):
        from midi import read_midifile
        from os.path import basename
        # Read are parse the midi file
        stream = read_midifile(filename)
        # Get the required segmentation parameters from the options
        time_unit = options['time_unit']
        tick_offset = options['tick_offset']
        # Use the filename as an identifier
        name = basename(filename)
        
        return SegmentedMidiInput.from_stream(stream, 
                                              time_unit=time_unit, 
                                              tick_offset=tick_offset,
                                              name=name,
                                              truncate=options['truncate'],
                                              gold=gold, 
                                              only_notes=True,
                                              sequence_index=sequence_index)
    
    @staticmethod
    def from_stream(stream, time_unit=4, tick_offset=0, name=None, 
                            only_notes=True, truncate=None, gold=None,
                            sequence_index=None):
        """
        Creates a L{SegmentedMidiInput} from a midi event stream.
        
        @type only_notes: bool
        @param only_notes: if True, only includes note-on/note-off events in 
            the segments. If False, the stream will be sliced so that each 
            segment repeats things like program change events at the beginning.
            Including only notes, however, makes the preprocessing very much 
            faster
        
        """
        # Divide the stream up into slices of the right size
        # Number of ticks in each slice
        tick_unit = int(stream.resolution*time_unit)
        if len(stream.trackpool) == 0:
            end_time = 0
        else:
            end_time = max(stream.trackpool).tick
        
        if only_notes:
            from midi import EventStream, NoteOnEvent, NoteOffEvent, EndOfTrackEvent
            # Only include notes in the stream
            # This is much simpler and faster than the alternative
            events = [ev for ev in list(sorted(stream.trackpool)) if \
                        type(ev) in [NoteOnEvent, NoteOffEvent]]
            events = iter(events)
            try:
                current_event = events.next()
                # Get up to the start point in the stream
                while current_event.tick < tick_offset:
                    current_event = events.next()
            except StopIteration:
                # Got to the end of the stream before we even started
                inputs = []
            else:
                inputs = []
                for chunk_start in range(tick_offset, end_time, tick_unit):
                    chunk_end = chunk_start+tick_unit
                    slc = EventStream()
                    slc.add_track()
                    slc.format = stream.format
                    slc.resolution = stream.resolution
                    slc.segment_start = chunk_start
                    
                    # Add all the note events in this time period
                    try:
                        while current_event.tick < chunk_end:
                            slc.add_event(current_event)
                            current_event = events.next()
                        # Add the end of track event
                        eot = EndOfTrackEvent()
                        eot.tick = chunk_end
                        slc.add_event(eot)
                    except StopIteration:
                        # Reached the end of the stream
                        inputs.append(slc)
                        break
                    
                    inputs.append(slc)
        else:
            # Use slices to do all the necessary repetition of ongoing events
            from midi.slice import EventStreamSlice
            start_times = range(tick_offset, end_time, tick_unit)
            # First slice starts at the offset value
            slices = [EventStreamSlice(stream, 
                                       chunk_start,
                                       chunk_start+tick_unit)
                        for chunk_start in start_times]
            inputs = [slc.to_event_stream(repeat_playing=False, cancel_playing=False) \
                                for slc in slices]
            # Associate the start time with each segment
            for slc,start_time in zip(inputs, start_times):
                slc.segment_start = start_time
        
        # Remove empty segments from the start and end
        current = 0
        # There's always one event - the end of track
        while len(inputs[current].trackpool) < 2:
            current += 1
        inputs = inputs[current:]
        # And the end
        current = len(inputs) - 1
        while len(inputs[current].trackpool) < 2:
            current -= 1
        inputs = inputs[:current+1]
        
        if truncate is not None:
            inputs = inputs[:truncate]
        
        return SegmentedMidiInput(inputs,
                                  time_unit=time_unit,
                                  tick_offset=tick_offset,
                                  name=name,
                                  stream=stream,
                                  gold=gold,
                                  sequence_index=sequence_index)

class AnnotatedDbInput(DbInput):
    """
    Like DbInput, but stores category annotations along with the chords.
    
    """
    FILE_INPUT_OPTIONS = DbInput.FILE_INPUT_OPTIONS
    
    def __init__(self, *args, **kwargs):
        self.categories = kwargs.pop('categories', [])
        super(AnnotatedDbInput, self).__init__(*args, **kwargs)
        
        if len(self.categories) != len(self):
            raise InputTypeError, "there must be the same number of category "\
                "annotations as chords"
    
    def get_gold_analysis(self):
        """
        Parses the annotations to get a gold analysis.
        
        """
        from jazzparser.evaluation.parsing import parse_sequence_with_annotations
        from jazzparser.grammar import get_grammar
        parses = parse_sequence_with_annotations(
                        self, get_grammar(), allow_subparses=False)
        return parses[0].semantics
    
    @staticmethod
    def from_sequence(seq):
        """
        Creates a DbInput from a database representation of a sequence.
        
        """
        inputs = [str(chord) for chord in seq]
        chords = list(seq.iterator())
        durations = [chord.duration for chord in seq]
        categories = [c.category for c in seq]
        return AnnotatedDbInput(inputs, durations=durations, 
                    name=seq.string_name, id=seq.id, categories=categories,
                    sequence=seq, chords=chords)
        
    @staticmethod
    def from_file(filename, options={}):
        # Load up a sequence index file according to the filename
        seqs = SequenceIndex.from_file(filename)
        # Get a sequence by index from the file
        seq = seqs.sequence_by_index(options['index'])
        if seq is None:
            raise InputReadError("%d is not a valid sequence index in %s" % \
                (options['index'], filename))
        return AnnotatedDbInput.from_sequence(seq)

INPUT_TYPES = [
    ('db', DbInput),
    ('db-annotated', AnnotatedDbInput),
    ('chords', ChordInput),
    ('segmidi', SegmentedMidiInput),
    ('labels', WeightedChordLabelInput),
    ('null', NullInput),
]

class BulkInput(InputReader):
    """
    Ways of accepting multiple inputs at once. These types can be used by the 
    parser script, whch will iterate over the component inputs.
    
    The classes should be iterable and iterate over the inputs.
    
    """
    INPUT_TYPE = None
    
    def __iter__(self):
        return iter(self.inputs)
    
    def __len__(self):
        return len(self.inputs)
        
    def __getitem__(self, i):
        return self.inputs[i]
        
    def subset(self, *ranges):
        """
        Returns an object of the same type containing the data points in the 
        given ranges, given as [start,end) pairs. Give multiple ranges as 
        successive arguments.
        
        A default implementation is provided, but subclasses may want to 
        provide their own if this is not appropriate.
        
        """
        return type(self)(\
            sum([self.inputs[start:end] for (start,end) in ranges], []))
    
    def get_partitions(self, num_partitions):
        """
        Generate an n-way partition and the corresponding heldout sets for 
        the data set. The objects returned are of the same bulk input 
        type.
        
        @return: ([part0, part1, ...], [rest0, rest1, ...])
        
        """
        partition_size = len(self) / num_partitions
        partitions = []
        heldout_sets = []
        
        # Get each equally-sized partition (all but the last)
        for parti in range(num_partitions-1):
            partitions.append(self.subset((partition_size*parti, partition_size*(parti+1))))
            # Get the set of inputs not in partition parti
            heldout_sets.append(self.subset(
                                    (0, partition_size*parti), 
                                    (partition_size*(parti+1), None)
                                ))
        
        # Last partition: throw in everything that's left
        partitions.append(self.subset((partition_size*(num_partitions-1), None)))
        heldout_sets.append(self.subset((0, partition_size*(num_partitions-1))))
        return (partitions, heldout_sets)
        
    def get_identifiers(self):
        """
        Returns a list containing a string identifier for each input. What 
        this is depends on the input type. At its simplest it may be just an 
        integer. In cases where something more informative is available (e.g. 
        a filename), this will be returned instead.
        
        Whatever happens, each input will have a unique identifier. This is 
        useful, for example, for creating an output file for each input.
        
        """
        # Try getting a name for each
        ids = [inp.name for inp in self]
        # Replace any None or blank names with an id
        ids = [name or str(i) for i,name in enumerate(ids)]
        # Check that the names are all unique and append ints if not
        return make_unique(ids)

class DbBulkInput(BulkInput):
    """
    A file containing a list of chord sequences. Can be read in from a 
    sequence index file.
    
    """
    INPUT_TYPE = DbInput
    
    def __init__(self, inputs):
        self.inputs = inputs
    
    @staticmethod
    def from_file(filename, options={}):
        # Read in the sequence index file
        f = SequenceIndex.from_file(filename)
        inputs = [DbInput.from_sequence(s) for s in f]
        return DbBulkInput(inputs)
    
    @property
    def sequences(self):
        return [inp.sequence for inp in self.inputs]

class ChordBulkInput(BulkInput):
    """
    A file containing a list of textual chord sequences. This used to be 
    provided fully in the top-level parser script as input processing.
    
    """
    INPUT_TYPE = ChordInput
    FILE_INPUT_OPTIONS = [
        ModuleOption('start', filter=int, 
                     help_text="line number to start reading from",
                     usage="start=X, where X is an int"),
        ModuleOption('end', filter=int, 
                     help_text="line number at which to stop reading",
                     usage="end=X, where X is an int"),
        ModuleOption('roman', filter=str_to_bool, 
                     help_text="read chord symbols as roman numberals. "\
                        "Default is to assume note names",
                     usage="roman=B, where B is a boolean",
                     default=False),
    ]
    
    def __init__(self, inputs, output_lines=None):
        self.inputs = inputs
        self.output_lines = output_lines
        
    @staticmethod
    def from_file(filename, options={}):
        f = open(filename, 'r')
        try:
            lines = f.readlines()
        finally:
            f.close()
        lines = [l.rstrip("\n") for l in lines]
        
        # Use the start and end line numbers if they were given
        if 'start' in options:
            lines = lines[options['start']:]
        if 'end' in options:
            lines = lines[:options['end']]
        
        # Do all the preprocessing
        output_lines = {}
        inputs = []
        sequence_name = None
        for line in lines:
            # If this is an output comment, output it and move to the next item
            if line.startswith(">>"):
                # If this is also a name definition, use it for the next sequence
                if line[2:].startswith("="):
                    sequence_name = line[3:-1]
                    output_lines[len(inputs)] = line[3:]
                else:
                    output_lines[len(inputs)] = line[2:]
                continue
            elif line.startswith("//"):
                # Non-printing comment
                # This could also be a name definition
                if line[2:].startswith("="):
                    output_lines[len(inputs)] = line[3:-1]
                continue
            elif len(line.strip()) == 0:
                # Ignore blank lines
                continue
            else:
                # Otherwise it's an actual chord sequence
                inputs.append(ChordInput.from_string(line, 
                                                     name=sequence_name,
                                                     roman=options['roman']))
                # Reset the sequence name
                sequence_name = None
        return ChordBulkInput(inputs, output_lines=output_lines)
    
    def to_db_inputs(self):
        """
        @see: L{ChordInput.to_db_input}
        """
        return DbBulkInput([chords.to_db_input() for chords in self.inputs])

class SegmentedMidiBulkInput(BulkInput):
    """
    A CSV file containing midi file paths and the parameters for segmenting 
    each one.
    
    May store an index of a gold analysis with each input. This should appear 
    in column 4. If these are given, the first line of the file should specify 
    the path to the sequence input file as follows::
    
      GOLD: <relative path>
    
    Columns: filename, time unit, tick offset, ignore (bool, optional), gold id (int, optional)
    
    """
    INPUT_TYPE = SegmentedMidiInput
    FILE_INPUT_OPTIONS = [
            ModuleOption('truncate', filter=int, 
                         help_text="truncate each input to this length.",
                         usage="truncate=L, where L is an integer")]
    SHELL_TOOLS = BulkInput.SHELL_TOOLS + [ tools.PlayBulkMidiChunksTool() ]
    
    def __init__(self, inputs):
        self.inputs = inputs
    
    def __str__(self):
        return "<bulk midi: %s>" % (" ".join([str(mid) for mid in self.inputs]))
    
    @staticmethod
    def writeln(csv, filename, time_unit=None, tick_offset=0, ignore=False, 
                    seq_index=None):
        """
        Writes a line to a segmidi bulk input file, opened as a CSV writer.
        
        """
        row = [
            "%s" % filename,
            "%f" % time_unit if time_unit else "2",
            "%d" % tick_offset,
            "TRUE" if ignore else "",
            "%d" % seq_index if seq_index is not None else ""
        ]
        csv.writerow(row)
        
    @staticmethod
    def from_file(filename, options={}):
        import csv, os
        # Read in the CSV file
        infile = open(filename, 'r')
        try:
            reader = csv.reader(infile)
            data = list(reader)
        finally:
            infile.close()
            
        base_path = os.path.abspath(os.path.dirname(filename))
        
        # Check the first line of the file for GOLD input
        if data[0][0].startswith("GOLD:"):
            gold_path = data[0][0].lstrip("GOLD:").strip()
            gold_path = os.path.join(base_path, gold_path)
            # Load the annotated data
            gold_data = AnnotatedDbBulkInput.from_file(gold_path)
            # Ignore this first line now
            data = data[1:]
        else:
            gold_data = None
        
        # Read the file's data and process it
        inputs = []
        for row in data:
            # Optional col 4 allows us to ignore rows for training while 
            #  keeping their parameters in the file
            if len(row) > 3:
                ignore = str_to_bool(row[3])
            else:
                ignore = False
            
            if not ignore:
                filename = row[0]
                # Read in the midi file
                midi = os.path.join(base_path, filename)
                
                # Prepare the parameters
                if row[1]:
                    time_unit = float(row[1])
                else:
                    time_unit = 2.0
                
                if row[2]:
                    tick_offset = int(row[2])
                else:
                    tick_offset = 0
                    
                if len(row) > 4 and gold_data is not None and row[4].strip():
                    # A gold sequence analysis was given: load it up
                    seq_index = int(row[4])
                    gold = gold_data[seq_index].get_gold_analysis()
                else:
                    seq_index = None
                    gold = None
                
                options = SegmentedMidiInput.process_option_dict({
                    'time_unit' : time_unit,
                    'tick_offset' : tick_offset,
                    'truncate' : options['truncate'],
                })
                inputs.append(
                    SegmentedMidiInput.from_file(midi, options=options, 
                                            gold=gold, sequence_index=seq_index))
        return SegmentedMidiBulkInput(inputs)

class AnnotatedDbBulkInput(DbBulkInput):
    """
    Like DbBulkInput, but for AnnotatedDbInput.
    
    """
    INPUT_TYPE = AnnotatedDbInput
    
    @staticmethod
    def from_file(filename, options={}):
        # Read in the sequence index file
        f = SequenceIndex.from_file(filename)
        inputs = [AnnotatedDbInput.from_sequence(s) for s in f]
        return AnnotatedDbBulkInput(inputs)

class MidiTaggerTrainingBulkInput(SegmentedMidiBulkInput):
    """
    Subclass of L{SegmentedMidiBulkInput} for taking training input for midi 
    supertaggers. This is identical to L{SegmentedMidiBulkInput}, but has an 
    additional option C{chords} to specify a path from which to read a 
    L{AnnotatedDbBulkInput}. This may be used by the training procedure to initialize 
    or train parameters, in addition to the main midi training input.
    
    Accepts additionally all options accepted by L{AnnotatedDbBulkInput}. These will 
    be passed on to L{DbBulkInput} when it's read in.
    
    """
    FILE_INPUT_OPTIONS = \
            SegmentedMidiBulkInput.FILE_INPUT_OPTIONS + \
            [ModuleOption('chords', 
                     help_text="path from which to read a bulk-db input, "\
                        "which may be used in addition to the midi training "\
                        "data by the training procedure",
                     usage="chords=F, where F is an filename")] + \
            AnnotatedDbBulkInput.FILE_INPUT_OPTIONS
    
    def __init__(self, inputs, chords=None):
        self.inputs = inputs
        self.chords = chords
    
    @staticmethod
    def from_file(filename, options={}):
        if 'chords' in options and options['chords'] is not None:
            # Read in the AnnotatedDbBulkInput from this file
            # Take AnnotatedDbBulkInput's options out of the option dict
            dboptions = {}
            for dbopt in AnnotatedDbBulkInput.FILE_INPUT_OPTIONS:
                if dbopt.name in options:
                    dboptions[dbopt.name] = options.pop(dbopt.name)
            chords = AnnotatedDbBulkInput.from_file(options['chords'], options=dboptions)
        else:
            chords = None
        # Read the main midi data just as SegmentedMidiBulkInput does
        main_data = SegmentedMidiBulkInput.from_file(filename, options)
        return MidiTaggerTrainingBulkInput(main_data.inputs, chords=chords)
    
    def subset(self, *ranges):
        # Custom implementation so subsets get the chord input
        return MidiTaggerTrainingBulkInput(\
            sum([self.inputs[start:end] for (start,end) in ranges], []), 
            chords=self.chords)
    

BULK_INPUT_TYPES = [
    ('bulk-db', DbBulkInput),
    ('bulk-db-annotated', AnnotatedDbBulkInput),
    ('bulk-chords', ChordBulkInput),
    ('bulk-segmidi', SegmentedMidiBulkInput),
    ('bulk-midi-train', MidiTaggerTrainingBulkInput),
]


class InputTypeError(Exception):
    pass
    
class InputReadError(Exception):
    pass

def input_type_name(cls):
    for datatype,clsmatch in INPUT_TYPES+BULK_INPUT_TYPES:
        if clsmatch == cls:
            return datatype
    return None
    
def get_input_type(name):
    for datatype,cls in INPUT_TYPES+BULK_INPUT_TYPES:
        if datatype == name:
            return cls
    return None

def get_input_type_names(single=True, bulk=True):
    types = [] + (INPUT_TYPES if single else []) + (BULK_INPUT_TYPES if bulk else [])
    return zip(*types)[0]

def is_bulk_type(cls):
    return issubclass(cls, BulkInput)

def detect_input_type(data, allowed=None, allow_bulk=False, errmess=""):
    """
    Preprocesses input.
    
    The input may be already wrapped using one of the wrappers in this 
    module, or it may be a string. In this case it will be wrapped using 
    ChordInput and the result will be returned.
    
    @type allowed: list of input type names
    @param allowed: (optional) list of data types that are allowed. If the 
        data is in a recognised format, but not one of these, an error will 
        be raised
    @type allow_bulk: bool
    @param allow_bulk: if True, accepts bulk input types. If C{allowed} is also 
        given, will check that the bulk input supplies an allowed type of 
        individual inputs
    @type errmess: str
    @param errmess: additional error message to include in the output when 
        a disallowed type is encountered. The message reads something like 
        "input of type <type> is not allowed<errmess>..."
    @rtype: (type name, input) pair
    @return: the identified input type and the wrapped-up input, ready to be 
        used by a tagger
    
    """
    if type(data) == str:
        # Handle strings by wrapping them up in a ChordInput
        datatype = 'chords'
        data = ChordInput.from_string(data)
    else:
        # Other types should already be wrapped
        for typename,cls in INPUT_TYPES:
            if type(data) == cls:
                datatype = typename
                break
        else:
            if allow_bulk:
                # Check the bulk input types
                for typename,cls in BULK_INPUT_TYPES:
                    if type(data) == cls:
                        datatype = typename
                        break
                else:
                    # No valid wrapped type was found
                    raise InputTypeError, "invalid input type: %s%s" % \
                            (type(data).__name__, errmess)
            else:
                # No valid wrapped type was found
                raise InputTypeError, "invalid input type: %s%s" % \
                        (type(data).__name__, errmess)
    if allowed is not None and datatype not in allowed:
        raise InputTypeError, "input of type '%s' is not allowed%s. Allowed "\
            "types are: %s" % (datatype, errmess, ", ".join(allowed))
    return (datatype,data)

def command_line_input(filename=None, filetype=None, options="", \
        allowed_types=None, default_type=None):
    """
    Utility function for processing file input options from the command line.
    Pass in as args the values straight from the command line options to 
    select a filename, filetype and list of options.
    
    Typical command-line options for this purpose (for an optparse option parser C{op})::
     op.add_option("--file", "-f", dest="file", action="store", help="use a file to get input from")
     op.add_option("--filetype", "--ft", dest="filetype", action="store", help="select the file type for the input file. Use '--filetype help' for a list of available types")
     op.add_option("--file-options", "--fopt", dest="file_options", action="store", help="options for the input file. Use '--fopt help', with '--ft <type>', for a list of available options")
    Then you can call this function as::
     command_line_input(filename=options.file, filetype=options.filetype, options=options.file_options)
    
    @type allowed_types: list of strs
    @param allowed_types: types of input you want the user to be able to give.
        If not given, all types are allowed
    @type default_type: str
    @param default_type: filetype to assume if no other filetype is given
    @rtype: L{InputReader} subclass
    @return: the input wrapper of appropriate type, or None if no input file 
        was given
    
    """
    if allowed_types is None:
        allowed_types = get_input_type_names()
    
    if filetype is None and default_type is not None:
        filetype = default_type
    
    # Catch a request for filetype help
    if filetype is not None and filetype.lower() == "help":
        # Output possible file types
        print "Allowed input types: %s" % ", ".join(allowed_types)
        sys.exit(0)
    
    # Check that the filetype is valid and get the input type class if it is
    input_type = get_input_type(filetype)
    type_name = input_type_name(input_type)
    if input_type is None:
        raise InputTypeError, "Unknown filetype '%s'. Allowed types are: %s" % \
            (filetype, ", ".join(allowed_types))
    if type_name not in allowed_types:
        raise InputTypeError, "Cannot accept input of type '%s'. Allowed "\
            "types are: %s" % (filetype, ", ".join(allowed_types))

    if options is not None and options.lower() == "help":
        # Output help text
        from jazzparser.utils.options import options_help_text
        print options_help_text(input_type.FILE_INPUT_OPTIONS, intro="Available options for input type %s" % type_name)
        sys.exit(0)
    
    if filename is None:
        return None
    
    # First get a dict of the options
    file_options = ModuleOption.process_option_string(options)
    # Process the options as appropriate for this type
    file_options = input_type.process_option_dict(file_options)
    
    # Instantiate the input from the file as appropriate for the input type
    input_data = input_type.from_file(filename, file_options)
    return input_data
