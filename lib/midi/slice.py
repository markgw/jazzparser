"""Slice midi streams up.

Utilities for handling portions of a midi stream in various ways.

"""
"""
    Copyright 2011 Giles Hall, Mark Granroth-Wilding
    
    This file is part of Pymidi2.

    Pymidi2 is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Pymidi2 is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Pymidi2.  If not, see <http://www.gnu.org/licenses/>.

"""

from midi import *
from copy import deepcopy

class EventStreamSlice(object):
    """
    Represents a portion of a midi stream (an L{EventStream}).
    
    The slice is not actually performed (events cut out of the stream) 
    until needed, e.g. when creating a new event stream from the 
    slice.
    
    When the slice is performed, events are copied from the original 
    stream into a whole new stream. The original stream is left intact 
    and the events of the new stream are new events.
    
    """
    def __init__(self, stream, start, end=None):
        """
        @type stream: L{EventStream}
        @param stream: the midi stream to take a slice of
        @type start: int
        @param start: the start time in midi ticks
        @type end: int or None
        @param end: the end time in midi ticks, or None to go to the end
        
        """
        self.stream = stream
        self.start = start
        self.end = end
        
    def to_event_stream(self, repeat_playing=True, cancel_playing=False, all_off=False):
        """
        Performs the actual slice operation, producing a new event 
        stream for just the portion of the midi stream covered by the 
        slice.
        
        @type repeat_playing: bool
        @param repeat_playing: if True all notes currently being played 
            at the start point will be replayed at the beginning of the 
            result. Default: True
        @type cancel_playing: bool
        @param cancel_playing: if True, all notes being played at the end point 
            will be cancelled (by an appropriate note-off) and the end of 
            the result. Default: False
        @type all_off: bool
        @param all_off: if True, adds an All Notes Off event to the end of the 
            stream.
        
        """
        # Collect up events from prior to the start that we should 
        #  repeat at the start of the new stream
        repeat_events = {}
        last_repeat_event_time = 0
        replay_notes = {}
        cancel_notes = {}
        for track_num,track in enumerate(self.stream):
            track_repeat_events = {}
            track_replay_notes = {}
            track_cancel_notes = {}
            
            ev_iter = iter(sorted(track))
            try:
                ev = ev_iter.next()
                # Stop once we've reached the start point
                while ev.tick >= self.start:
                    event_type = type(ev)
                    # Only repeat events of certain types
                    if event_type in SLICE_REPEAT_EVENTS:
                        override_check = SLICE_REPEAT_EVENTS[event_type]
                        # Check whether this overrides earlier events
                        if event_type in track_repeat_events:
                            earlier = track_repeat_events[event_type]
                            # Only look at events on the same channel
                            earlier = [e for e in earlier if e.channel == ev.channel]
                            # If this overrides any of the earlier events,
                            #  remove them
                            remove_events = []
                            for prior in earlier:
                                if override_check(ev, prior):
                                    remove_events.append(id(prior))
                            track_repeat_events[event_type] = \
                                [e for e in track_repeat_events[event_type] \
                                    if id(e) not in remove_events]
                        # Add this event
                        track_repeat_events.setdefault(event_type, []).append(ev)
                    elif repeat_playing or cancel_playing:
                        if isinstance(ev, NoteOnEvent) and ev.velocity > 0:
                            # Note sounded before the start: replay it unless 
                            #  it's subsequently taken off before the start
                            track_replay_notes[ev.pitch] = ev
                        elif (isinstance(ev, NoteOffEvent) or \
                                (isinstance(ev, NoteOnEvent) and ev.velocity == 0) \
                             ) and ev.pitch in track_replay_notes:
                            # Note's been played previously, but is taken off, 
                            #  so don't replay it
                            del track_replay_notes[ev.pitch]
                    ev = ev_iter.next()
                
                # Continue to work out what notes are playing at the end if we need to
                if cancel_playing:
                    # Start with the notes we know are playing at the beginning
                    track_cancel_notes = track_replay_notes.copy()
                    while ev.tick < self.end:
                        if isinstance(ev, NoteOnEvent) and ev.velocity > 0:
                            # New note starts
                            track_cancel_notes[ev.pitch] = ev
                        elif (isinstance(ev, NoteOffEvent) or \
                                (isinstance(ev, NoteOnEvent) and ev.velocity == 0) \
                             ) and ev.pitch in track_cancel_notes:
                            # Note ends naturally
                            del track_cancel_notes[ev.pitch]
                        ev = ev_iter.next()
            except StopIteration:
                pass
            
            # Make each set of events at a distinct time take only one tick
            events_to_repeat = sum(track_repeat_events.values(), [])
            if len(events_to_repeat):
                #  Prepare the copy we'll use in the new version
                events_to_repeat = [deepcopy(e) for e in events_to_repeat]
                event_time_groups = {}
                for ev in events_to_repeat:
                    event_time_groups.setdefault(ev.tick, []).append(ev)
                repeat_events[track_num] = []
                for new_time,time in enumerate(sorted(event_time_groups.keys())):
                    # Give all simultaneous events the same time
                    for e in event_time_groups[time]:
                        e.tick = new_time
                    repeat_events[track_num].extend(sum(event_time_groups.values(),[]))
                # Keep track of the latest of these repeated events
                last_repeat_event_time = max(last_repeat_event_time, new_time)
            
            if repeat_playing:
                # Prepare the notes we need to replay at the begining
                replay_notes[track_num] = [deepcopy(ev) for ev in track_replay_notes.values()]
                
            if cancel_playing:
                # Prepare the notes we need to stop at the end
                cancel_notes[track_num] = [deepcopy(ev) for ev in track_cancel_notes.values()]
        
        # Work out the tempo at the start of the slice
        start_tempo = deepcopy(self.stream.get_tempo(self.start))
        start_tempo.tick = last_repeat_event_time
        
        # Now for the actual stream copying
        new_str = EventStream()
        # Copy the parameters from the old event stream
        new_str.format = self.stream.format
        new_str.resolution = self.stream.resolution
        
        # Add the events from the old stream that are within the slice
        for i,track in enumerate(self.stream):
            new_str.add_track()
            
            # Add in the events we need to repeat at the beginning
            if i in repeat_events:
                for ev in repeat_events[i]:
                    # We've already set the tick of these
                    new_str.add_event(ev)
            
            # If this is the first track, add the start tempo
            if i == 0:
                new_str.add_event(start_tempo)
            
            if repeat_playing:
                # Add any notes that were played before the start and 
                #  haven't been taken off yet
                for ev in replay_notes[i]:
                    ev.tick = last_repeat_event_time + 1
                    new_str.add_event(ev)
                
            # Add each event in the track
            for ev in sorted(track):
                # Only look at events in the range of the slice
                if ev.tick < self.start:
                    continue
                if self.end is not None and ev.tick >= self.end:
                    break
                # Take a copy of the event from the source stream
                ev = deepcopy(ev)
                # Shift the event back
                ev.tick -= (self.start - last_repeat_event_time - 1)
                new_str.add_event(ev)
            
            if cancel_playing:
                # Add note-offs for any notes still playing at the end
                for ev in cancel_notes[i]:
                    noteoff = NoteOffEvent()
                    noteoff.tick = (self.end - self.start)
                    noteoff.pitch = ev.pitch
                    noteoff.channel = ev.channel
                    new_str.add_event(noteoff)
        
            if all_off:
                # Find all channels that have been used
                channels = list(set(ev.channel for ev in new_str.track))
                for ch in channels:
                    # Add an All Notes Off event for each channel
                    all_off_ev = all_notes_off_event(ch)
                    all_off.tick = self.end - self.start + 1
                    new_str.add_event(all_off)
            
            # If we have no end time, the EOT can just be set by the last event
            if self.end is not None:
                # Add an end-of-track event at the time the slice is supposed to stop
                eot = EndOfTrackEvent()
                eot.tick = self.end
                new_str.add_event(eot)
        
        return new_str


__repeat_all = lambda x,y: False
__only_latest = lambda x,y: True

SLICE_REPEAT_EVENTS = {
    AfterTouchEvent : lambda x,y: x.pitch == y.pitch,
    ControlChangeEvent : lambda x,y: x.control == y.control,
    ProgramChangeEvent : __only_latest,
    ChannelAfterTouchEvent : __only_latest,
    PitchWheelEvent : __only_latest,
    # Repeat all SysExes to be on the safe side - we don't know what they do
    SysExEvent : __repeat_all,
    # Always repeat these things, since they don't supercede earlier ones
    CopyrightEvent : __repeat_all,
    TrackNameEvent : __repeat_all,
    InstrumentNameEvent : __only_latest,
    PortEvent : __only_latest,
    TimeSignatureEvent : __only_latest,
    KeySignatureEvent : __only_latest,
}
"""
The event types that should be repeated at the beginning of a slice if 
they occurred prior to the start of the slice in the event stream.

The repeat key function will be consulted to decide whether a later 
event overrides an earlier one of the same type on the same channel. 
The later event will be considered to have overridden the earlier if it 
returns True.

ChannelPrefixEvent has a special behaviour and doesn't fit into this 
framework.

"""
