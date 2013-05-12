from __future__ import absolute_import
"""Midi input handling for Raphsto models

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

import os.path, csv
from midi import EventStream, NoteOnEvent, read_midifile, NoteOffEvent, \
                    ProgramChangeEvent, LyricsEvent
from . import constants

class MidiHandler(object):
    """
    Class to encapsulate all the midi processing needed for getting 
    input to a Raphsto model. Read in midi files using the L{midi} 
    library and load an L{midi.EventStream}. Then use this class to 
    get whatever form of data out of it you need for your input.
    
    """
    def __init__(self, stream, time_unit=4, remove_drums=False, \
                    tick_offset=0):
        """
        @type stream: L{midi.EventStream}
        @param stream: the midi data to get input from
        @type time_unit: int or float
        @param time_unit: number of beats to take as the basic unit 
            of time for observations
        
        """
        self.stream = stream
        self.time_unit = time_unit
        self.filtered_stream = list(sorted(self.stream.trackpool))
        if remove_drums:
            self.filtered_stream = [ev for ev in self.filtered_stream if ev.channel != 9]
        if tick_offset != 0:
            self.filtered_stream = [ev for ev in self.filtered_stream if ev.tick >= tick_offset]
        self.tick_offset = tick_offset
        
    def get_emission_stream(self):
        """
        Get a list of emissions from the midi stream's note on events.
        
        Returns a 2-tuple of the list of emissions and their 
        corresponding start times in midi ticks.
        
        """
        note_ons = [ev for ev in self.filtered_stream if isinstance(ev, NoteOnEvent)]
        tick_unit = int(self.stream.resolution*self.time_unit)
        # Divide up the note-ons into chucks of this size
        chunks = []
        current_chunk = []
        for ev in note_ons:
            while ev.tick-self.tick_offset >= (len(chunks)+1)*tick_unit:
                chunks.append(current_chunk)
                current_chunk = []
            bar_start = len(chunks)*tick_unit + self.tick_offset
            if ev.tick == bar_start:
                rhythm = 0
            elif ev.tick == bar_start + (tick_unit/2):
                rhythm = 1
            elif ev.tick == bar_start + (tick_unit/4) or \
                    ev.tick == bar_start + (tick_unit*3/4):
                rhythm = 2
            else:
                rhythm = 3
            pc = ev.pitch % 12
            current_chunk.append((pc, rhythm))
        # Get the last chunk
        chunks.append(current_chunk)
        
        # Get rid of duplicate values in the chunks (octaves)
        chunks = [list(set(c)) for c in chunks]
        
        start_times = [i*tick_unit for i in range(len(chunks))]
        stream = zip(*( (em,time) for (em,time) in zip(chunks,start_times) if len(em) > 0 ))
        return stream
    
    def get_slices(self):
        """
        Get a list of L{midi.slice.EventStreamSlice}s corresponding to the 
        chunks that this midi stream will be divided into.
        This includes all midi events, not just note-ons.
        
        """
        from midi.slice import EventStreamSlice
        
        tick_unit = int(self.stream.resolution*self.time_unit)
        if len(self.stream.trackpool) == 0:
            end_time = 0
        else:
            end_time = max(self.stream.trackpool).tick
        
        slices = [EventStreamSlice(self.stream, 
                                   chunk_start,
                                   chunk_start+tick_unit-1)
                    for chunk_start in range(self.tick_offset, end_time, tick_unit)]
        return slices

class InputSourceFile(object):
    """
    File reader to get midi input files listed in a single file format.
    The format is CSV, each row containing a midi filename (relative 
    to the source file's location) and the parameters to use to process 
    the midi data as input:
    
    C{filename,time_unit,tick_offset,remove_drums}
    
    See L{MidiHandler} for the meaning of these parameters.
    
    Once the file's loaded, the (parsed) files and parameters are 
    available in the list obj.inputs. You can also get directly at 
    a list of L{MidiHandler}s using L{get_handlers}.
    
    """
    def __init__(self, filename):
        """
        @type filename: str
        @param filename: filename of the file to read from
        
        """
        infile = open(filename, 'r')
        reader = csv.reader(infile)
        self.data = list(reader)
        infile.close()
        
        self.base_path = os.path.abspath(os.path.dirname(filename))
        
        # Read the file's data and process it
        self.inputs = []
        for row in self.data:
            # Optional col 4 allows us to ignore rows for training while 
            #  keeping their parameters in the file
            if len(row) > 4:
                ignore = bool(row[4])
            else:
                ignore = False
            
            if not ignore:
                filename = row[0]
                # Read in the midi file
                midi = os.path.join(self.base_path, filename)
                
                # Prepare the parameters
                if row[1]:
                    time_unit = int(row[1])
                else:
                    time_unit = 4
                
                if row[2]:
                    tick_offset = int(row[2])
                else:
                    tick_offset = 0
                
                remove_drums = bool(row[3])
                
                self.inputs.append((midi, time_unit, tick_offset, remove_drums))
        
    def get_handlers(self):
        """
        Generator to get L{MidiHandler}s, one for each line of the 
        input file.
        
        """
        for line in self.inputs:
            yield MidiHandler(read_midifile(line[0]), time_unit=line[1], 
                            tick_offset=line[2], remove_drums=line[3])

class ChordSequenceRealizer(object):
    """
    Factory to take the output from the labeller and realize the chord sequence 
    as a midi file.
    
    Very basic - not going to sound great, but it's easier than playing it 
    myself.
    
    """
    def __init__(self, labels, resolution=120, chord_length=2, times=None, \
                    text_events=False, state_formatter=None):
        """
        @type labels: list of tuples
        @param labels: state label tuples output by the model
        @type resolution: int
        @param resolution: midi resolution to give the result (midi ticks per beat)
        @type chord_length: int
        @param chord_length: length of each chord as a number of beats
        @type times: list of ints
        @param times: optional onset time for each chord in midi ticks.
            If not given, it will be calculated by giving chord_length to 
            every chord
        @type text_events: bool
        @param text_events: include chord labels in the midi as text events
        @type state_formatter: 1-arg function
        @param state_formatter: function to take a state label and produce 
            the text label that will go in the midi data. Optional: 
            by default, will use L{jazzparser.misc.raphsto.format_state_as_chord}.
        
        """
        self.labels = labels
        self.resolution = resolution
        self.chord_length = chord_length
        self.times = times
        self.text_events = text_events
        
        from jazzparser.misc.raphsto import format_state_as_raphsto
        if state_formatter is None:
            self.formatter = format_state_as_raphsto
        else:
            self.formatter = state_formatter
        
    def generate(self, overlay=None, offset=0):
        """
        Generates a midi stream.
        
        """
        octaves = 1
        
        if overlay is not None:
            stream = overlay
            # Use organ sound
            instrument = 23
            # Find the last channel used in the file we're overlaying
            channel = max(ev.channel for ev in stream.trackpool) + 1
            volume = 30
        else:
            stream = EventStream()
            stream.resolution = self.resolution
            # Just use piano
            instrument = 0
            channel = 0
            volume = 127
        stream.add_track()
        pc = ProgramChangeEvent()
        pc.value = instrument
        pc.tick = 0
        pc.channel = channel
        stream.add_event(pc)
        # Length of each chord in midi ticks
        chord_length = int(self.resolution * self.chord_length)
        
        if self.times is None:
            times = [i*chord_length + offset for i in range(len(self.labels))]
        else:
            times = [t+offset for t in self.times]
        
        formatter = getattr(self, 'formatter')
        
        pending_note_offs = []
        for (tonic,mode,chord),time in zip(self.labels, times):
            scale_chord_root = constants.CHORD_NOTES[mode][chord][0]
            chord_root = (tonic+scale_chord_root) % 12
            triad_type = constants.SCALE_TRIADS[mode][chord]
            # Work out the notes for this chord
            triad_notes = [(chord_root + note) % (octaves*12) + 72 for note in constants.TRIAD_NOTES[triad_type]]
            # Add the root in the octave two below
            triad_notes.append(chord_root + 48)
            
            # Add note offs for notes already on
            for noff in pending_note_offs:
                noff.tick = time-1
                stream.add_event(noff)
            pending_note_offs = []
            
            if self.text_events:
                # Add a text event to represent the chord label
                tevent = LyricsEvent()
                label = formatter((tonic,mode,chord))
                tevent.data = "%s\n" % label
                tevent.tick = time
                stream.add_event(tevent)
            
            # Add a note-on and off event for each note
            for note in triad_notes:
                non = NoteOnEvent()
                non.tick = time
                non.pitch = note
                non.channel = channel
                non.velocity = volume
                stream.add_event(non)
                
                # Hold the note until the next chord is played
                noff = NoteOffEvent()
                noff.pitch = note
                noff.channel = channel
                noff.velocity = volume
                pending_note_offs.append(noff)
        
        # Add the last remaining note offs
        for noff in pending_note_offs:
            noff.tick = time+chord_length
            stream.add_event(noff)
        return stream
