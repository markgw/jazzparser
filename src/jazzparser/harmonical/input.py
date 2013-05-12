from __future__ import absolute_import
"""Harmonical input file processing.

Simple input reading to give tone specifications directly to the 
harmonical.

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

from jazzparser.utils.base import abstractmethod
from .tones import ToneMatrix, SineChordEvent, SineClusterEvent, ENVELOPES
from .midi import tonal_space_note_events
from .midi.chords import events_for_chord
from jazzparser.utils.tonalspace import tonal_space_et_pitch, tonal_space_pitch
from jazzparser.data import Fraction
from midi import write_midifile, EventStream, SetTempoEvent, \
                    ProgramChangeEvent, NoteOnEvent, NoteOffEvent

class HarmonicalInputFile(object):
    """
    Base class for input files to the harmonical.
    
    """
    @staticmethod
    def from_file(filename, formats=None):
        """
        Read in an input file. This method detects the type of input 
        and returns an instance of the appropriate subclass.
        
        @type formats: list of strings
        @param formats: list of formats to allow. By default, accepts any 
            format. If a list is given and the file's format isn't in it, 
            raises an error.
        
        """
        infile = open(filename, 'r')
        lines = infile.readlines()
        # Remove all comments from the lines
        lines = [line.partition("#")[0].strip() for line in lines]
        # Remove empty lines
        lines = [line for line in lines if len(line) > 0]
        # Make sure there's some content - a type line and at least one more
        if len(lines) < 2:
            raise HarmonicalInputFileReadError, "empty file"
        # Read any global directives and don't pass them through to the subclass
        dirlines = [line.lstrip("@") for line in lines if line.startswith("@")]
        directives = {}
        for dirline in dirlines:
            name,__,value = dirline.partition(":")
            value = value.strip()
            directives[name] = value
            
        # Check the @format directive is given
        if 'format' not in directives:
            raise HarmonicalInputFileReadError, "no format descriptor "\
                "found in the input file."
        format = directives.pop('format')
        # Make sure this is a format we know about
        if format not in INPUT_TYPES:
            raise HarmonicalInputFileReadError, "invalid harmonic "\
                "input format: '%s'. Should be one of: %s" % \
                (format, ", ".join(INPUT_TYPES.keys()))
        if formats is not None and format not in formats:
            raise HarmonicalInputFileReadError, "harmonical input format "\
                "%s not allowed here. You can only use %s" % (format, 
                    ", ".join(formats))
        
        lines = [line for line in lines if not line.startswith("@")]
        # First process the directives
        directives = INPUT_TYPES[format].process_global_directives(directives)
        # Use the subclass' loader to get an appropriate instance
        inst = INPUT_TYPES[format].from_data(lines, directives)
        return inst
            
    @staticmethod
    def process_global_directives(data):
        output = {}
        unused = data.keys()
        if "tempo" in data:
            output["tempo"] = int(data["tempo"])
            unused.remove("tempo")
        if len(unused) != 0:
            raise HarmonicalInputFileReadError, "unknown global " \
                "directive '%s'" % unused[0]
        return output
        
    @staticmethod
    @abstractmethod
    def from_data(data, global_directives):
        """
        Subclasses must provide this method to create an instance from 
        the lines of data read in from a file.
        Should take a second argument which will be a dictionary of 
        the global directive values.
        
        """
        pass
                
    @abstractmethod
    def render(self):
        """
        Subclasses must provide a way of building an audio signal.
        
        """
        pass
        
    @abstractmethod
    def render_midi(self):
        """
        Subclasses may provide a way of building a tuned midi file.
        
        @raise NotImplementedError: if this input format doesn't support 
            midi generation.
        
        """
        raise NotImplementedError, "input format does not support midi file "\
            "generation"
    

############ Utility functions for file reading ##########
def _get_duration(tokens):
    """Get a 'for' duration specification out of a line's tokens.
    Returns duration in quarter notes."""
    duration = 1
    if "for" in tokens:
        forpos = tokens.index("for")
        try:
            duration = float(Fraction(tokens.pop(forpos+1)))
        except:
            raise HarmonicalInputFileReadError, "'for' "\
                "must be followed by an integer number "\
                "of beats."
        tokens.pop(forpos)
    return duration
def _qn_to_seconds(duration):
    """
    Converts from quarter note duration to number of seconds.
    """
    return float(duration) * 60 / directives['tempo']

def _get_root(tokens):
    """Get a 'at' root specification out of a line's tokens."""
    if "at" in tokens:
        atpos = tokens.index("at")
        try:
            root = _read_coord(tokens.pop(atpos+1))
        except:
            raise HarmonicalInputFileReadError, "'at' "\
                "must be followed by an integer number "\
                "of beats."
        tokens.pop(atpos)
    else:
        root = (0,0,0)
    return root
    
def _read_coord(token):
    """Parse a 3D coordinate string."""
    if not token.startswith("(") or not token.endswith(")"):
        raise HarmonicalInputFileReadError, \
            "invalid coordinate: %s" % token
    parts = token[1:-1].split(",")
    if len(parts) != 3:
        raise HarmonicalInputFileReadError, \
            "coordinate must be 3D: %s" % token
    return int(parts[0]), int(parts[1]), int(parts[2])
    
def _get_pitch(point):
    """Get the pitch of a point in the space."""
    if state['equal_temperament']:
        return state['origin'] * tonal_space_et_pitch(point)
    else:
        return state['origin'] * tonal_space_pitch(point)
        
def _get_volume(tokens):
    """Reads a volume specifier."""
    if "vol" in tokens:
        atpos = tokens.index("vol")
        try:
            volume = int(tokens.pop(atpos+1))
        except ValueError:
            raise HarmonicalInputFileReadError, "'vol' "\
                "must be followed by an integer volume "\
                "between 0 and 100."
        if volume < 0 or volume > 100:
            raise HarmonicalInputFileReadError, "volume "\
                "value must be between 0 and 100, not %s" % volume
        tokens.pop(atpos)
        volume = float(volume)/100
    else:
        volume = 0.8
    return volume

###############################################


class ChordInputFile(HarmonicalInputFile):
    """
    Type of harmonical input file that simply specifies a list of 
    chords, with durations, defined by a list of tonal space points.
    
    For documentation of the file syntax, see 
    U{http://jazzparser.granroth-wilding.co.uk/HarmonicalChordInput}.
    
    """
    def __init__(self, tone_matrix, midi_file=None):
        self.__tone_matrix = tone_matrix
        self.__midi_file = midi_file
        
    def render(self):
        # This is built when the file's read, so just return it now
        matrix = self.__tone_matrix
        # Now render the matrix to audio
        return matrix.render()
        
    def render_midi(self):
        # Midi file is actually generated during parsing, so we just return it
        return self.__midi_file
        
    @staticmethod
    def from_data(data, directives):
        # Build the tone matrix straight up
        state = {
            'equal_temperament' : False,
            'double_root' : False,
            'envelope' : None,
            'origin' : 440,
            'time' : 0.0,
        }
        tone_matrix = ToneMatrix()
        
        #### Prepare a midi stream
        mid = EventStream()
        mid.add_track()
        # Add a tempo event
        tempo = SetTempoEvent()
        tempo.tempo = directives['tempo']
        tempo.tick = 0
        mid.add_event(tempo)
        
        # Each line represents a single chord or some kind of directive
        for line in data:
            first_word = line.split()[0].lower()
            if "=" in line:
                # This is an assignment
                key, __, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Check it's valid
                if key == "equal_temperament":
                    if value not in ['off','on']:
                        raise HarmonicalInputFileReadError, \
                            "equal_temperament must be 'off' or 'on', "\
                            "not '%s'" % value
                    value = (value == 'on')
                elif key == "origin":
                    try:
                        value = int(value)
                    except ValueError:
                        # Try interpreting as a coordinate
                        try:
                            coord = _read_coord(value)
                        except HarmonicalInputFileReadError:
                            raise HarmonicalInputFileReadError, "origin "\
                                "value must be an integer or a coordinate."
                        value = _get_pitch(coord)
                elif key == "double_root":
                    if value not in ['off','on']:
                        raise HarmonicalInputFileReadError, \
                            "double_root must be 'off' or 'on', "\
                            "not '%s'" % value
                    value = (value == 'on')
                elif key == "envelope":
                    if value not in ENVELOPES:
                        raise HarmonicalInputFileReadError, "unknown "\
                            "envelope '%s'. Must be one of: %s" % \
                            (value, ", ".join(ENVELOPES.keys()))
                    value = ENVELOPES[value]()
                elif key == "program":
                    # Midi program change
                    try:
                        value = int(value)
                        if value > 127 or value < 0:
                            raise ValueError
                    except ValueError:
                        raise HarmonicalInputFileReadError, "invalid program "\
                            "change: %s. Should be an integer 0-127" % value
                    pchange = ProgramChangeEvent()
                    pchange.value = value
                    pchange.tick = int(state['time'] * mid.resolution)
                    mid.add_event(pchange)
                else:
                    raise HarmonicalInputFileReadError, "invalid "\
                        "assignment key: '%s'" % key
                # Make this assignment when we get to it in the score
                state[key] = value
            elif first_word == "rest":
                tokens = line.split()
                duration = _get_duration(tokens)
                
                # Just move the time counter on without doing anything
                state['time'] += duration
            elif first_word == "chord":
                tokens = line.lstrip("chord").split()
                duration = _get_duration(tokens)
                root = _get_root(tokens)
                volume = _get_volume(tokens)
                sec_duration = _qn_to_seconds(duration)
                
                # Must be just a chord type left
                if len(tokens) > 1:
                    raise HarmonicalInputFileReadError, "chord must "\
                        "include just a chord type"
                if len(tokens) == 0:
                    ctype = ''
                else:
                    ctype = tokens[0]
                
                # Add the chord to the tone matrix
                tone_matrix.add_tone(
                        _qn_to_seconds(state['time']), 
                        SineChordEvent(
                            _get_pitch(root), 
                            ctype,
                            duration=sec_duration, 
                            amplitude=volume,
                            equal_temperament=state['equal_temperament'],
                            double_root=state['double_root'],
                            envelope=state['envelope']
                        )
                    )
                    
                # Add the same chord to the midi file
                tick_time = int(mid.resolution * state['time'])
                tick_duration = int(duration * mid.resolution)
                # TODO: currently this will always treat C as the origin 
                #  even if you change it with directives
                events = events_for_chord(root, 
                                          ctype,
                                          tick_time,
                                          tick_duration, 
                                          velocity = int(volume*127),
                                          equal_temperament=state['equal_temperament'],
                                          double_root=state['double_root'])
                for ev in events:
                    mid.add_event(ev)
                
                # Move the timer on ready for the next chord
                state['time'] += duration
            elif first_word in ["tones", "t"]:
                # Must be a chord made up of coordinates
                tokens = line.lstrip("tones").split()
                duration = _get_duration(tokens)
                root = _get_root(tokens)
                volume = _get_volume(tokens)
                sec_duration = _qn_to_seconds(duration)
                    
                # The rest should be the list of coordinates
                coordinates = [_read_coord(token) for token in tokens]
                
                # Add the chord to the tone matrix
                tone_matrix.add_tone(
                        _qn_to_seconds(state['time']), 
                        SineClusterEvent(
                            _get_pitch(root), 
                            coordinates,
                            duration=sec_duration, 
                            amplitude=volume,
                            equal_temperament=state['equal_temperament'],
                            double_root=state['double_root'],
                            envelope=state['envelope']
                        )
                    )
                    
                
                # Add the same chord to the midi file
                tick_time = int(mid.resolution * state['time'])
                tick_duration = int(duration * mid.resolution)
                for note in coordinates:
                    # TODO: currently this will always treat C as the origin 
                    #  even if you change it with directives
                    events = tonal_space_note_events(note, 
                                                     tick_time,
                                                     tick_duration, 
                                                     velocity = int(volume*127))
                    if state['equal_temperament']:
                        # Omit tuning event (the first one)
                        events = events[1:]
                    for ev in events:
                        mid.add_event(ev)
                
                # Move the timer on ready for the next chord
                state['time'] += duration
            else:
                raise HarmonicalInputFileReadError, "could not make sense "\
                    "of the line: %s" % line
        return ChordInputFile(tone_matrix, midi_file=mid)


class ChordDictionaryFile(HarmonicalInputFile):
    """
    Rather like the ChordInputFile format, but specifies a list of chords 
    with names. This is used by the interactive tonal space to specify 
    chord clusters.
    
    For documentation of the file syntax, see 
    U{http://jazzparser.granroth-wilding.co.uk/HarmonicalChordVocab}.
    
    """
    def __init__(self, chord_dict, names=None):
        self.chords = chord_dict
        if names is None:
            self.chord_names = chord_dict.keys()
        else:
            self.chord_names = names
        
    @staticmethod
    def from_data(data, directives):
        chords = {}
        names = []
        
        # Each line represents a single chord type (TS cluster), or some 
        #  kind of directive
        for line in data:
            if ":" in line:
                # Definition of a chord type
                name, __, value = line.partition(":")
                name = name.strip()
                tokens = value.strip().split()
                notes = [_read_coord(tok) for tok in tokens]
                chords[name] = notes
                names.append(name)
            else:
                raise HarmonicalInputFileReadError, "could not make sense "\
                    "of the line: %s" % line
        return ChordDictionaryFile(chords, names)

INPUT_TYPES = {
    'chord' : ChordInputFile,
    'chord-vocab' : ChordDictionaryFile,
}

class HarmonicalInputFileReadError(Exception):
    pass
