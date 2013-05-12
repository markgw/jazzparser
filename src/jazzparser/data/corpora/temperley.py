"""Corpus file handling for David Temperley's corpora.

David Temperley has various corpora that he has used in his books:
 - The Cognition of Basic Musical Structures (2001)
 - Music and Probability (2007)

He evaluates his own techniques and others' on this data, so it is 
an important comparison for me. It's also an important source of 
annotated data, aside for my own small corpus.

This module provides utilities for reading in the corpus files and 
representing the data internally.

The data formats are described in Temperley's documentation for the 
programs that make up Melisma.

@note: This implementation is not intended to be complete. It may not handle 
all types of input that Temperley describes. I'm just implementing 
things as I need them.

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

import os
from jazzparser.data.corpora import get_corpus_file

_EVENTS = {}

class Event(object):
    """
    Superclass of all events that occur in the data.
    
    """
    EVENT_NAME = None
    """The identifier that begins the line of an input file for this event."""
    
    @staticmethod
    def from_line(line):
        """
        Creates an instance of the appropriate event type given a line 
        of an input file.
        
        All subclasses should define a C{from_line} that creates an 
        instance of them given the list of string arguments from a line 
        of an input file.
        
        """
        name = line.split()[0]
        # Consult the registry for an event for this name
        if name not in _EVENTS:
            raise InputError, "unknown event type %s" % name
        return _EVENTS[name].from_line(line.split()[1:])
        
    def to_line(self):
        """
        Generates a string representation suitable for writing out to 
        a line of a file.
        
        """
        raise NotImplementedError, "%s does not implement to_line()" % type(self).__name__
    
    def __str__(self):
        return "<%s>" % self.to_line()
    
    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            event_name = dict['EVENT_NAME']
            if event_name is None:
                if name != "Event":
                    raise AttributeError, "event class %s does not define "\
                        "an event name (%s.EVENT_NAME)" % \
                        (name,name)
            else:
                if event_name in _EVENTS:
                    raise AttributeError, "multiply defined event name: %s" \
                        % event_name
                _EVENTS[event_name] = cls
            
    def _get_sort_key(self):
        return 0
        
    def __cmp__(self, other):
        if hasattr(other, "_get_sort_key"):
            return cmp(self._get_sort_key(), other._get_sort_key())
        else:
            return cmp(super(Event,self),other)

class TPCNoteEvent(Event):
    """
    Tonal pitch-class note, found in TPC files and chord files.
    A tonal pitch-class is a note as notated - i.e. it distinguishes 
    all differently named notes. They are represented as a position on 
    the line of fifths:
    
    ...-2 -1  0  1  2  3  4  5  6  7  8  9 10 11 12 ...
    ... Ab Eb Bb F  C  G  D  A  E  B  F# C# G# D# A#...
    
    They are also redundantly represented as a midi note value.
    
    """
    EVENT_NAME = "TPCNote"
    
    def __init__(self, start, end, note, pitch_class):
        self.start = start
        self.end = end
        self.note = note
        self.pitch_class = pitch_class
        
    @staticmethod
    def from_line(line):
        debug_line = "  ".join(line)
        if len(line) != 4:
            raise InputError, "TPCNote event needs 4 arguments. %d "\
                "found: %s" % (len(line), debug_line)
        return TPCNoteEvent(int(line[0]), int(line[1]), int(line[2]), int(line[3]))
        
    def to_line(self):
        return "%s   %d  %d  %d  %d" % (self.EVENT_NAME, self.start, 
            self.end, self.note, self.pitch_class)
        
    def _get_sort_key(self):
        return self.start

class BeatEvent(Event):
    """
    A beat identifier, giving a time of occurrence and a beat level.
    
    """
    EVENT_NAME = "Beat"
    
    def __init__(self, time, level):
        self.time = time
        self.level = level
        
    @staticmethod
    def from_line(line):
        debug_line = "  ".join(line)
        if len(line) != 2:
            raise InputError, "Beat event needs 2 arguments. %d "\
                "found: %s" % (len(line), debug_line)
        return BeatEvent(int(line[0]), int(line[1]))
        
    def to_line(self):
        return "%s   %d  %d" % (self.EVENT_NAME, self.time, 
            self.level)
        
    def _get_sort_key(self):
        return self.time

class ChordEvent(Event):
    """
    A chord, identified just by its start time, end time and root. The 
    root is a position on the line of fifths.
    
    @see: L{TPCNoteEvent}
    
    """
    EVENT_NAME = "Chord"
    
    def __init__(self, start, end, root):
        self.start = start
        self.end = end
        self.root = root
        
    @staticmethod
    def from_line(line):
        debug_line = "  ".join(line)
        if len(line) != 3:
            raise InputError, "Chord event needs 3 arguments. %d "\
                "found: %s" % (len(line), debug_line)
        return ChordEvent(int(line[0]), int(line[1]), int(line[2]))
    
    def to_line(self):
        return "%s   %d  %d  %d" % (self.EVENT_NAME, self.start, 
            self.end, self.root)
        
    def _get_sort_key(self):
        return self.start
        
class DataSequence(object):
    """
    Data structure to store a list of events read in from a corpus 
    file.
    
    """
    def __init__(self):
        self._events = []
        self._event_types = {}
        self._ordered_types = []
    
    def add_event(self, event):
        self._events.append(event)
        self._event_types.setdefault(event.EVENT_NAME, []).append(event)
        # Keep a list of the event types in the order they appeared in the input
        if event.EVENT_NAME not in self._ordered_types:
            self._ordered_types.append(event.EVENT_NAME)
        
    def __get_events(self):
        return list(sorted(self._events))
    events = property(__get_events)
    
    def get_events_by_type(self, type):
        """
        Returns a list of all events of a specific type.
        
        """
        if type in self._event_types:
            return list(sorted(self._event_types[type]))
        else:
            return []
            
    def get_grouped_events(self):
        """
        Returns a list of all events, grouped by their event type, 
        with the event types in the order they were found in the input.
        
        This should provide a form suitable for outputing to the lines 
        of a file (using C{to_line()} on each event). Alternatively, 
        just use C{to_lines()}.
        
        """
        return sum([self.get_events_by_type(typ) for typ in self._ordered_types], [])
        
    def to_lines(self):
        """
        Returns a list of lines suitable for outputing to a file.
        
        """
        return [ev.to_line() for ev in self.get_grouped_events()]
    
    @staticmethod
    def from_file(infile):
        """
        Creates a new DataSequence to represent the data in a file. 
        
        @type infile: str or open file object
        @param infile: filename or file object. Filename may be the 
            path to the file or the path within the corpus.
            
        """
        if type(infile) == str:
            if not os.path.exists(infile):
                # Try getting it from the corpus instead
                infile = get_corpus_file('kp', infile)
            infile = open(infile, 'r')
        
        lines = infile.readlines()
        dseq = DataSequence()
        for line in lines:
            dseq.add_event(Event.from_line(line))
        return dseq
    
    def __str__(self):
        evs = self.events
        if len(evs) > 10:
            evs = evs[:9] + ["...", evs[-1]]
        return "<Temperley: %s>" % ", ".join([str(ev) for ev in evs])
        
    def __iter__(self):
        return iter(self.events)
    
    def to_midi(self):
        """
        Constructs a L{MIDI EventStream<midi.EventStream>} from the 
        data in this stream.
        This can then be output to a file to be played.
        
        Note that TPCNotes will be output as normal MIDI notes. We 
        can't do anything of the clever tuning stuff that we can do 
        with tonal space coordinates, since we'd need to do a further 
        step of analysis to work out the fully specified TS point from 
        the pitch class.
        
        """
        tempo = 120
        
        from midi import EventStream, NoteOffEvent, NoteOnEvent, SetTempoEvent
        mid = EventStream()
        mid.add_track()
        # Set the tempo first at the beginning
        temp = SetTempoEvent()
        temp.tempo = tempo
        temp.tick = 0
        mid.add_event(temp)
        # Work out how many ticks there are in a millisecond
        ticks_per_ms = float(mid.resolution) * tempo / 60000
        # Create midi events for every event in our stream
        for ev in self.events:
            if isinstance(ev, TPCNoteEvent):
                # Create note-on and note-off events
                note = ev.note
                
                noteon = NoteOnEvent()
                noteon.pitch = note
                noteon.tick = int(ev.start * ticks_per_ms)
                noteon.velocity = 100
                mid.add_event(noteon)
                
                noteoff = NoteOffEvent()
                noteoff.pitch = note
                noteoff.tick = int(ev.end * ticks_per_ms)
                noteoff.velocity = 100
                mid.add_event(noteoff)
            elif isinstance(ev, (ChordEvent,BeatEvent)):
                # These events don't affect the midi data
                continue
            else:
                raise TypeError, "event type %s not recognised by "\
                    "MIDI converter." % type(ev).__name__
        return mid

read_file = DataSequence.from_file

class InputError(Exception):
    pass

