"""Justly intoned chord sequence realization

Production of justly intoned chord sequences in the form of MIDI 
files with tuning instructions included.

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
from .. import CHORD_TYPES
from midi import write_midifile, EventStream, SetTempoEvent, \
                    ProgramChangeEvent, NoteOnEvent, NoteOffEvent
from . import tonal_space_note_events
from jazzparser.utils.base import group_pairs
from jazzparser.data import Fraction

class ChordSequenceRealizer(object):
    """
    A factory class to produce a MIDI file (represented using the midi 
    library package's C{EventStream})) from a sequence of tonal space 
    roots and chord types.
    
    The resulting MIDI file will be tuned so that the realization is 
    justly intoned.
    
    This provides an interface similar to 
    L{path_to_tones<jazzparser.harmonical.tones.path_to_tones>}, which 
    renders the path to raw wave data containing sine waves.
    
    """
    def __init__(self, path, chord_types=None, tempo=120, \
            root_octave=0, double_root=False, equal_temperament=False, \
            instrument=0, bass_root=None):
        """
            
        @type path: list of (3d-coordinate,length) tuples
        @param path: coordinates of the points in the sequence with their 
            associated lengths, given in beats (ints or 
            L{Fractions<jazzparser.data.Fraction>})
        @type tempo: int
        @param tempo: speed in beats per second (Maelzel's metronome)
        @type chord_types: list of (string,length) tuples
        @param chord_types: the type of chord to use for each tone, with 
            its associated length. See 
            L{..CHORD_TYPES<jazzparser.harmonical.CHORD_TYPES>} keys for possible values.
        @type equal_temperament: bool
        @param equal_temperament: render all the pitches as they would be 
            played in equal temperament.
        @type root_octave: int
        @param root_octave: octave to transpose the root to relative 
            to other notes. Default (0) has the other notes in the 
            octave above the root.
        @type double_root: bool
        @param double_root: if True, an extra tone will be added an 
            octave below the root
        @type instrument: int
        @param instrument: MIDI instrument to set at the beginning of 
            the file.
        @type bass_root: int
        @param bass_root: like double_root, adds an extra note an 
            octave below the root. In this case, adds it to a seperate 
            track, with the midi instrument number given. Set to None 
            not to add the note at all (default)
        
        """
        self.path = path
        
        if chord_types is None:
            # Default chord type is just a major chord
            self.chord_types = [('',length) for coord,length in path]
        else:
            # Check we've heard of all these chord types
            types = set([type for type,length in chord_types])
            for ctype in types:
                if ctype not in CHORD_TYPES:
                    raise ChordSequenceRealizationError, "don't know "\
                        "how to realize the chord type '%s'" % ctype
            self.chord_types = chord_types
            
        self.tempo = tempo
        self.root_octave = root_octave
        self.double_root = double_root
        self.equal_temperament = equal_temperament
        self.instrument = instrument
        self.bass_root = bass_root
        
    def render(self):
        """
        Creates MIDI data from the path and chord types.
        
        @rtype: midi.EventStream
        @return: an event stream containing all the midi events
        
        """
        mid = EventStream()
        mid.add_track()
        
        # Set the tempo at the beginning
        tempo = SetTempoEvent()
        tempo.tempo = self.tempo
        mid.add_event(tempo)
        
        # Set the instrument at the beginning
        instr = ProgramChangeEvent()
        instr.value = self.instrument
        mid.add_event(instr)
        
        beat_length = mid.resolution
        # Work out when each root change occurs
        time = Fraction(0)
        root_times = []
        for root,length in self.path:
            root_times.append((root,time))
            time += length
        def _root_at_time(time):
            current_root = root_times[0][0]
            for root,rtime in root_times[1:]:
                # Move through root until we get the first one that 
                #  occurs after the previous time
                if rtime > time:
                    return current_root
                current_root = root
            # If we're beyond the time of the last root, use that one
            return current_root
        
        # Add each chord
        time = Fraction(0)
        bass_events = []
        bass = self.bass_root is not None
        for chord_type,length in self.chord_types:
            tick_length = length * beat_length - 10
            tick_time = time * beat_length
            # Find out what root we're on at this time
            root = _root_at_time(time)
            # Add all the necessary events for this chord
            chord_events = events_for_chord(root, chord_type, int(tick_time), 
                                int(tick_length), 
                                equal_temperament=self.equal_temperament,
                                root_octave=self.root_octave, 
                                double_root=(self.double_root or bass))
            if bass:
                # Add the bass note to the bass track
                bass_events.extend([copy.copy(ev) for ev in chord_events[-1]])
            if bass and not self.double_root:
                # Remove the doubled root that we got for the bass line
                chord_events = sum(chord_events[:-1], [])
            # Add the main chord notes to the midi track
            for ev in chord_events:
                mid.add_event(ev)
            time += length
        
        if bass:
            bass_channel = 1
            # Add another track to the midi file for the bass notes
            mid.add_track()
            # Select a bass instrument - picked bass
            instr = ProgramChangeEvent()
            instr.value = 33
            instr.channel = bass_channel
            mid.add_event(instr)
            # Add all the bass notes
            for ev in bass_events:
                ev.channel = bass_channel
                mid.add_event(ev)
        return mid
        
    def write(self, outfile):
        """
        Renders MIDI data and writes it out the the given file.
        
        @type outfile: string or open file
        @param outfile: filename to write to or an open file(-like) object
        
        """
        mid = self.render()
        write_midifile(mid, outfile)

def events_for_chord(coord, chord_type, start, duration, origin_note=60, 
        equal_temperament=False, root_octave=0, double_root=False,
        velocity=100):
    """
    Builds a chord's midi events (note on and note off) from a root 
    coordinate and a chord type. Uses the chord definitions in 
    L{jazzparser.harmonical.CHORD_TYPES} to decide what notes to 
    play.
    
    The list is grouped into sublists, one for each note.
    For each note, three events are created: tuning, note on and note 
    off.
    
    @type root_octave: int
    @param root_octave: octave to transpose the root to relative 
        to other notes. Default (0) has the other notes in the 
        octave above the root.
    @type double_root: bool
    @param double_root: if True, an extra tone will be added an 
        octave below the root. This will be the last event in the list
    
    """
    notes = copy.copy(CHORD_TYPES[chord_type])
    if root_octave != 0 or double_root:
        # Do the special things with the root, if it's voiced
        root = None
        for (x,y,z) in notes:
            if x == y == 0:
                root = (x,y,z)
                break
        if root is not None:
            # Remove the root from the other notes
            notes.remove(root)
            # Add a root shifted to the requested octave
            notes.append((0,0,root[2]+root_octave))
            if double_root:
                # Double the root an octave below
                notes.append((0,0,root[2]+root_octave-1))
    notes = [(coord[0]+note[0], coord[1]+note[1], coord[2]+note[2]) for note in notes]
    
    events = []
    for note in notes:
        tuning,noteon,noteoff = tonal_space_note_events(note, start, duration, origin_note=origin_note, velocity=velocity)
        note_events = []
        # Skip the tuning if we're in ET
        if not equal_temperament:
            note_events.append(tuning)
        note_events.append(noteon)
        note_events.append(noteoff)
        events.append(note_events)
    return events
        
def render_path_to_file(filename, path, *args, **kwargs):
    """
    Convenience function that takes a path and set of timings and 
    uses the harmonical to render MIDI from it and writes it to a 
    file.
    
    Additional args/kwargs are passed to the L{ChordSequenceRealizer} 
    init.
    
    """
    realizer = ChordSequenceRealizer(path, *args, **kwargs)
    realizer.write(filename)

class ChordSequenceRealizationError(Exception):
    pass
