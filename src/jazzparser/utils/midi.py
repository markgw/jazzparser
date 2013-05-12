from __future__ import absolute_import
"""Midi processing utilities

Utilities for processing MIDI data.

Note that most MIDI processing is not provided here. Anything that's 
sufficiently generic is in the C{midi} library (which I've been 
developing myself, so can easily add to). Things relating to retuning 
and generation are in the L{<jazzparser.harmonical>harmonical module}.

@see: L{midi}
@see: L{jazzparser.harmonical}

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

from midi import NoteOnEvent, NoteOffEvent

def note_on_similarity(midi0, midi1):
    """
    Given two L{EventStreams<midi.EventStream>}, returns the similarity,
    between 0 and 1, of the note on events.
    
    This is useful for detecting duplicate MIDI files. Exact mirrors 
    of files can easily be found by checking for equality of the raw 
    MIDI data, but often files are redistributed with different 
    instruments, or simply different meta data.
    
    Note that the absolute time of two MIDI events must be equal for 
    them to match, so an offset version of the same file will not 
    match.
    
    This measure is not symmetric. C{midi0} is compared to C{midi1} 
    and vice versa and both results are returned. If you want a 
    symmetric measure, average the two.
    
    @rtype: (float,float) pair
    @return: a pair of similarities, the first from testing for how 
        much of C{midi0} is found in C{midi1} and the second from the 
        opposite.
    
    """
    from copy import copy
    
    note_ons0 = [ev for ev in midi0.trackpool if isinstance(ev, NoteOnEvent)]
    note_ons1 = [ev for ev in midi1.trackpool if isinstance(ev, NoteOnEvent)]
    note_ons0.sort()
    note_ons1.sort()
    
    def _matches(base, comp):
        base = copy(base)
        comp = copy(comp)
        matches = 0
        # Go through each note-on in the first file and look for a matching 
        #  one in the second
        for note_on in base:
            # Try to find a note-on with the same note at the same time
            while len(comp) and comp[0].tick < note_on.tick:
                comp.pop(0)
            if len(comp) == 0:
                # No more matches to find
                break
            i = 0
            while len(comp) > i and comp[i].tick == note_on.tick:
                if comp[i].pitch == note_on.pitch:
                    matches += 1
                    break
                i += 1
        return matches
    
    # Work out the similarity both ways so the measure is symetric
    matches0 = _matches(note_ons0, note_ons1)
    matches1 = _matches(note_ons1, note_ons0)
    
    return float(matches0)/len(note_ons0), float(matches1)/len(note_ons1)

def trim_intro(mid):
    """
    Many MIDI files begin with a count-in on a drum. Some might even 
    begin with some silence.
    
    Given a L{midi.EventStream}, returns a version with any drum intro 
    or silence trimmed from the beginning, so that the first thing 
    heard is a non-drum note.
    
    It is assumed that this is General MIDI data, so channel 10 is 
    necessarily a drum channel.
    
    """
    from midi import EndOfTrackEvent
    import copy
    
    mid = copy.deepcopy(mid)
    first_note = None
    events = iter(sorted(mid.trackpool))
    # Find the time of the first played note that's not a drum note
    while first_note is None:
        ev = events.next()
        if isinstance(ev, NoteOnEvent) and ev.channel != 9:
            first_note = ev.tick
    
    # Shift everything backwards
    to_remove = []
    intro_events = []
    intro_length = 0
    for track in mid.tracklist.values():
        # Keep all the events in the right order, but remove as much 
        #  empty time as possible
        for ev in track:
            intro_times = {}
            if ev.tick < first_note:
                # Remove all note-ons and -offs
                if isinstance(ev, (NoteOnEvent,NoteOffEvent)):
                    to_remove.append(ev)
                else:
                    # Put the rest as close to the beginning as possible
                    intro_times.setdefault(ev.tick, []).append(ev)
                    intro_events.append(id(ev))
        # Give each distinct time only a single midi tick
        for tick,(old_tick, pre_events) in enumerate(intro_times.items()):
            for ev in pre_events:
                ev.tick = tick
        intro_length = max(intro_length, len(intro_times))
    
    # Now get rid of the pre-start notes
    for ev in to_remove:
        mid.remove_event_instance(ev)
        
    # Shift everything back as for as we can
    shift = first_note - intro_length
    for ev in mid.trackpool:
        if id(ev) not in intro_events:
            old_time = ev.tick
            ev.tick -= shift
    return mid

def play_stream(stream, block=False):
    """
    Plays an event stream.
    
    Various methods for playing midi data are provided in the L{midi}
    library. At the time of writing, the only one that works is Timidity 
    via SDL via PyGame and this is what this function uses.
    
    Whatever happens with the midi library, this function should 
    continue to provide some convenient way to play a L{midi.EventStream}.
    
    If a keyboard interrupt is received, the playing will stop. The interrupt 
    will still be raised.
    
    @rtype: L{midi.sequencer_pygame.Sequencer}
    @return: the sequencer that's been instantiated to do the playing.
    
    """
    from midi.sequencer_pygame import Sequencer
    seq = Sequencer(stream)
    try:
        seq.play(block=block)
    except KeyboardInterrupt:
        seq.stop()
        raise
    return seq

def get_midi_text(stream):
    """
    Extracts descriptive text from a L{midi.EventStream}. This is often 
    stored in the form of copyright notices, text events, track names, 
    etc. This tries to pull out everything it can and return it all in 
    a multiline string.
    
    Midi data can use non-ASCII characters. We assume the latin1 
    encoding is intended for these. This certainly covers the most 
    common case: the copyright symbol.
    
    Returns a unicode string.
    
    """
    from midi import CopyrightEvent, TextEvent, TrackNameEvent
    lines = []
    
    for ev in sorted(stream.trackpool):
        if isinstance(ev, (CopyrightEvent, TextEvent)):
            lines.append(unicode(ev.data, 'latin1'))
        elif isinstance(ev, NoteOnEvent):
            # Stop looking for text once the notes start
            #  (this prevents us getting lyrics)
            break
    
    # Get track name events in order of tracks
    for track in stream:
        for ev in sorted(track):
            if isinstance(ev, TrackNameEvent):
                lines.append(u"Track: %s" % unicode(ev.data, 'latin1'))
                # There should only be one of these
                break
    return u"\n".join(lines)

def first_note_tick(stream):
    """
    Returns the tick time of the first note-on event in an EventStream.
    
    """
    for ev in sorted(stream.trackpool):
        if type(ev) == NoteOnEvent:
            return ev.tick

def simplify(stream, remove_drums=False, remove_pc=False, 
        remove_all_text=False, one_track=False, remove_tempo=False,
        remove_control=False, one_channel=False, 
        remove_misc_control=False, real_note_offs=False, remove_duplicates=False):
    """
    Filters a midi L{midi.EventStream} to simplify it. This is useful 
    as a preprocessing step before taking midi input to an algorithm, 
    for example, to make it clearer what the algorithm is using.
    
    Use kwargs to determine what filters will be applied. Without any 
    kwargs, the stream will just be left as it was.
    
    Returns a filtered copy of the stream.
    
    @type remove_drums: bool
    @param remove_drums: filter out all channel 10 events
    @type remove_pc: bool
    @param remove_pc: filter out all program change events
    @type remove_all_text: bool
    @param remove_all_text: filter out any text events. This includes 
        copyright, text, track name, lyrics.
    @type one_track: bool
    @param one_track: reduce everything to just one track
    @type remove_tempo: bool
    @param remove_tempo: filter out all tempo events
    @type remove_control: bool
    @param remove_control: filter out all control change events
    @type one_channel: bool
    @param one_channel: use only one channel: set the channel of 
        every event to 0
    @type remove_misc_control: bool
    @param remove_misc_control: filters a miscellany of device 
        control events: aftertouch, channel aftertouch, pitch wheel, 
        sysex, port
    @type real_note_offs: bool
    @param real_note_offs: replace 0-velocity note-ons with actual 
        note-offs. Some midi files use one, some the other
    
    """
    from midi import EventStream, TextEvent, ProgramChangeEvent, \
        CopyrightEvent, TrackNameEvent, \
        SetTempoEvent, ControlChangeEvent, AfterTouchEvent, \
        ChannelAfterTouchEvent, PitchWheelEvent, SysExEvent, \
        LyricsEvent, PortEvent, CuePointEvent, MarkerEvent, EndOfTrackEvent
    import copy
    
    # Empty stream to which we'll add the events we don't filter
    new_stream = EventStream()
    new_stream.resolution = stream.resolution
    new_stream.format = stream.format
    
    # Work out when the first note starts in the input stream
    input_start = first_note_tick(stream)
    
    # Filter track by track
    for track in stream:
        track_events = []
        for ev in sorted(track):
            # Don't add EOTs - they get added automatically
            if type(ev) == EndOfTrackEvent:
                continue
            ev = copy.deepcopy(ev)
            # Each filter may modify the event or continue to filter it altogether
            
            if remove_drums:
                # Filter out any channel 10 events, which is typically 
                #  reserved for drums
                if ev.channel == 9 and \
                        type(ev) in (NoteOnEvent, NoteOffEvent):
                    continue
            if remove_pc:
                # Filter out any program change events
                if type(ev) == ProgramChangeEvent:
                    continue
            if remove_all_text:
                # Filter out any types of text event
                if type(ev) in (TextEvent, CopyrightEvent, TrackNameEvent,
                        LyricsEvent, CuePointEvent, MarkerEvent):
                    continue
            if remove_tempo:
                # Filter out any tempo events
                if type(ev) == SetTempoEvent:
                    continue
            if remove_control:
                # Filter out any control change events
                if type(ev) == ControlChangeEvent:
                    continue
            if remove_misc_control:
                # Filter out various types of control events
                if type(ev) in (AfterTouchEvent, ChannelAfterTouchEvent, 
                        ChannelAfterTouchEvent, PitchWheelEvent, 
                        SysExEvent, PortEvent):
                    continue
            if real_note_offs:
                # Replace 0-velocity note-ons with note-offs
                if type(ev) == NoteOnEvent and ev.velocity == 0:
                    new_ev = NoteOffEvent()
                    new_ev.pitch = ev.pitch
                    new_ev.channel = ev.channel
                    new_ev.tick = ev.tick
                    ev = new_ev
            if one_channel:
                ev.channel = 0
            
            track_events.append(ev)
        
        # If there are events left in the track, add them all as a new track
        if len(track_events) > 1:
            if not one_track or len(new_stream.tracklist) == 0:
                new_stream.add_track()
            for ev in track_events:
                new_stream.add_event(ev)
            track_events = []
    
    for track in stream:
        track.sort()
    
    # Work out when the first note happens now
    result_start = first_note_tick(new_stream)
    # Move all events after and including this sooner so the music 
    #  starts at the same point it did before
    shift = result_start - input_start
    before_start = max(input_start-1, 0)
    if shift > 0:
        for ev in new_stream.trackpool:
            if ev.tick >= result_start:
                ev.tick -= shift
            elif ev.tick < result_start and ev.tick >= input_start:
                # This event happened in a region that no longer contains notes
                # Move it back to before what's now the first note
                ev.tick = before_start
    
    new_stream.trackpool.sort()
    
    if remove_duplicates:
        # Get rid of now duplicate events
        remove_duplicate_notes(new_stream, replay=True)
    
    return new_stream

def remove_duplicate_notes(stream, replay=False):
    """
    Some processing operations, like L{simplify}, can leave a midi file with 
    the same note being played twice at the same time.
    
    To avoid the confusion this leads to, it's best to remove these. This 
    function will remove multiple instances of the same note being played 
    simultaneously (in the same track and channel) and insert note-off events 
    before a note is replayed that's already being played.
    
    This can lead to some strange effects if multiple instruments have been 
    reduced to one, as in the case of L{simplify}. You may wish to keep 
    seperate instruments on separate channels to avoid this.
    
    @type replay: bool
    @param replay: if True, notes that are played while they're already sounding 
        while be replayed - taken off and put back on. Otherwise, such notes 
        will be ignored.
    
    """
    to_remove = []
    to_add = {}
    
    for i,track in stream.tracklist.items():
        notes_on = {}
        last_instance = {}
        
        for ev in sorted(track):
            if type(ev) == NoteOnEvent and ev.velocity > 0:
                # Note on
                if ev.channel in notes_on and \
                        ev.pitch in notes_on[ev.channel]:
                    # Note is already being played
                    previous = last_instance[ev.channel][ev.pitch]
                    if not replay or previous.tick == ev.tick:
                        # Simultaneous duplicate, or we don't want to replay 
                        #  resounded notes
                        # Remove this one
                        to_remove.append(ev)
                    else:
                        # Replay: insert a note-off
                        note_off = NoteOffEvent()
                        note_off.pitch = ev.pitch
                        note_off.channel = ev.channel
                        note_off.velocity = 127
                        note_off.tick = ev.tick-1
                        to_add.setdefault(i, []).append(note_off)
                # Increase the count of instances of this note being played
                notes_on.setdefault(ev.channel, {}).setdefault(ev.pitch, 0)
                notes_on[ev.channel][ev.pitch] += 1
                last_instance.setdefault(ev.channel, {})[ev.pitch] = ev
            elif type(ev) == NoteOffEvent or \
                    (type(ev) == NoteOnEvent and ev.velocity == 0):
                # Note off
                if ev.channel not in notes_on or \
                        ev.pitch not in notes_on[ev.channel]:
                    # Note is not currently being played
                    # Remove this note off
                    to_remove.append(ev)
                else:
                    # Decrease the count of instances of this note being played
                    notes_on[ev.channel][ev.pitch] -= 1
                    if notes_on[ev.channel][ev.pitch] == 0:
                        # Note was only being played once
                        # Leave the note off in there
                        del notes_on[ev.channel][ev.pitch]
                    else:
                        # Note was being played multiple times
                        # Decrease the count, but don't include this note off
                        to_remove.append(ev)
    
    # Remove all events scheduled for removal
    stream.remove_event_instances(to_remove)
    # Add all events scheduled to addition
    for trk,evs in to_add.items():
        stream.curtrack = trk
        for ev in evs:
            stream.add_event(ev)

def remove_channels(stream, channels=[]):
    """
    Modifies a stream in place to remove all events played on certain channels.
    
    """
    to_remove = []
    for ev in stream.trackpool:
        if ev.channel in channels:
            to_remove.append(ev)
    stream.remove_event_instances(to_remove)

def note_ons(stream):
    """
    Filters the events in an event stream to return only note-on events with a 
    non-zero velocity.
    
    """
    return [ev for ev in stream.trackpool if isinstance(ev, NoteOnEvent) \
                                    and ev.velocity > 0]
