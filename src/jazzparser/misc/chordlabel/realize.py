from __future__ import absolute_import
"""Chord sequence realizer for the output of a chord labeler.

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

from midi import EventStream, NoteOnEvent, read_midifile, NoteOffEvent, \
                    ProgramChangeEvent, LyricsEvent

class ChordSequenceRealizer(object):
    """
    Factory to take the output from the labeler and realize the chord sequence 
    as a midi file.
    
    Very basic - not going to sound great, but it's easier than playing it 
    myself.
    
    """
    def __init__(self, labels, chord_vocab, resolution=120, chord_length=2, \
                    text_events=False):
        """
        @type labels: list of L{jazzparser.misc.chordlabel.data.ChordLabel}s
        @param labels: chord labels output by the model
        @type chord_vocab: dict
        @param chord_vocab: mapping from the chord labels that may appear in 
            C{labels} to the notes of the chord
        @type resolution: int
        @param resolution: midi resolution to give the result (midi ticks per beat)
        @type chord_length: int
        @param chord_length: length of each chord as a number of beats
        @type text_events: bool
        @param text_events: include chord labels in the midi as text events
        
        """
        self.labels = labels
        self.chord_vocab = chord_vocab
        self.resolution = resolution
        self.chord_length = chord_length
        self.text_events = text_events
        
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
            volume = 50
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
        
        times = [i*chord_length + offset for i in range(len(self.labels))]
        
        pending_note_offs = []
        for label,time in zip(self.labels, times):
            chord_root = label.root
            # Work out the notes for this chord
            triad_notes = [(chord_root + note) % (octaves*12) + 72 for \
                                        note in self.chord_vocab[label.label]]
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

