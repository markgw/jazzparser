"""Midi file I/O and manipulation library.

Python MIDI

 - Original author: Giles Hall
 - Modified by Mark Granroth-Wilding, 2010-11

This package contains data structures and utilities for reading, 
manipulating and writing MIDI data.

"""
import copy
from cStringIO import StringIO
from struct import unpack, pack
from math import log

from .constants import NOTE_VALUE_MAP_SHARP, BEATVALUES, \
                        DEFAULT_MIDI_HEADER_SIZE
from .encoding import read_varlen, write_varlen


class Event(object):
    """
    Base class for all MIDI events.
    
    """
    length = 0
    name = "Generic MIDI Event"
    statusmsg = 0x0
    # By default, events may be transmitted using running status,
    #  but this is disabled for some event types
    allow_running = True

    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            if name not in ['Event', 'MetaEvent', 'NoteEvent']:
                EventFactory.register_event(cls, bases)

    def __init__(self):
        self.type       = self.__class__.__name__
        """ Event type derived from class name """
        self.channel    = 0
        """ Midi channel """
        self.tick       = 0
        """ Time of the event in midi ticks """
        self.msdelay    = 0
        """ Delay in ms """
        self.data       = ''
        """ Data after status message """
        self.track      = 0
        """ Track number (gets set when event is added to a stream) """
        self.order      = None
        """ Sort order """

    def copy(self):
        return copy.deepcopy(self)

    def is_event(cls, statusmsg):
        """
        Checks whether this is of an event identified by the given 
        status message.
        
        """
        return (cls.statusmsg == (statusmsg & 0xF0))
    is_event = classmethod(is_event)

    def __str__(self):
        return "%s @%d %dms C%d T%d" % (self.name, 
                            self.tick,
                            self.msdelay,
                            self.channel,
                            self.track)

    def __cmp__(self, other):
        if self.tick < other.tick: return -1
        elif self.tick > other.tick: return 1
        return 0

    def adjust_msdelay(self, tempo):
        rtick = self.tick - tempo.tick
        self.msdelay = int((rtick * tempo.mpt) + tempo.msdelay)
     
    def encode(self, last_tick=0, running=False):
        """
        Produces an encoding of this event for writing to a MIDI stream.
        Includes the delta and status message.
        
        @type last_tick: int/long
        @param last_tick: tick value of the previous event that was 
            encoded in the stream. The timing of this event will be 
            stored as a delta, so we need to know when the last thing 
            happened.
        @type running: bool
        @param running: omits the status message if true, since it is 
            assumed that the status is carried over from the previous 
            event.
        
        """
        encstr = ''
        if not running:
            encstr += chr((self.statusmsg & 0xF0) | (0x0F & self.channel))
        return self.encode_delta_tick(last_tick=last_tick) + encstr + self.encode_data()

    def decode(self, tick, statusmsg, track, runningstatus=''):
        """
        Reads MIDI data from the track stream, from which the tick 
        and status message have already been read. Removes as many 
        bytes from the track as this event type needs.
        Sets instance variables according to data read from the stream.
        
        @param tick: tick time of the event (already read from the stream)
        @param statusmsg: the status message that was read from the 
            stream for this event. This is expected to be of the correct 
            type for this event type.
        @param track: data stream from which to continue reading as 
            much data as is needed for this event.
        @param runningstatus: if this event had a running status in the 
            input stream, the byte that was read off the stream to 
            try to get a status for this event (which turned out not 
            to be a status message) goes in here and gets treated as 
            the first byte of the data.
        
        """
        assert(self.is_event(statusmsg))
        self.tick = tick
        self.channel = statusmsg & 0x0F
        self.data = ''
        if runningstatus:
            self.data += runningstatus
        remainder = self.length - len(self.data)
        if remainder:
            self.data += str.join('',[track.next() for x in range(remainder)])
        self.decode_data()

    def encode_delta_tick(self, last_tick=0):
        """
        this function should be renamed "encode_delta_tick"; it doesn't
        encode the tick value of the event. 
        Returns the varlen data to use to represent the timing of this 
        event relative to the last event.
        
        @param last_tick: time of the previous event in the stream.
        
        """
        delta_tick = self.tick - last_tick
        return write_varlen(delta_tick)

    def decode_data(self):
        """
        Takes the data that's been read into C{data} instance variable 
        and sets instance attributes from the values in it. What this 
        does is specific to the event type.
        
        At the simplest, it could do nothing, just leaving the raw data 
        in C{data}, but more likely it will decode values from the 
        data.
        
        """
        pass

    def encode_data(self):
        """
        Produces byte data to represent this event on the basis of 
        instance variables. This is the data that will be written to 
        a MIDI stream (not including the tick and status message).
        
        @return: byte data as a string
        
        """
        return self.data
    

    
class MetaEvent(Event):
    """
    MetaEvent is a special subclass of Event that is not meant to
    be used as a concrete class.  It defines a subset of Events known
    as the Meta events.
    
    """
    statusmsg = 0xFF
    metacommand = 0x0
    name = 'Meta Event'
    allow_running = False
    
    data = ''
    """ Raw data to store in the event """

    def is_event(cls, statusmsg):
        return (cls.statusmsg == statusmsg)
    is_event = classmethod(is_event)

    def is_meta_event(cls, metacmd):
        return (cls.metacommand == metacmd)
    is_meta_event = classmethod(is_meta_event)

    def encode(self, last_tick=0, running=False):
        tick = self.encode_delta_tick(last_tick=last_tick)
        data = self.encode_data()
        datalen = write_varlen(len(data))
        smsg = chr(self.statusmsg)
        mcmd = chr(self.metacommand)
        return str.join("", (tick, smsg, mcmd, datalen, data))

    def decode(self, tick, command, track):
        assert(self.is_meta_event(command))
        self.tick = tick
        self.channel = 0
        if not hasattr(self, 'order'):
            self.order = None
        len = read_varlen(track)
        self.data = str.join('', [track.next() for x in range(len)])
        self.decode_data()


class EventFactory(object):
    """
    EventFactory is a factory for getting MIDI events out of a data 
    stream.
    
    """
    EventRegistry = []
    MetaEventRegistry = []
    
    def __init__(self):
        self.RunningStatus = None
        self.RunningTick = 0

    def register_event(cls, event, bases):
        if MetaEvent in bases:
            cls.MetaEventRegistry.append(event)
        elif (Event in bases) or (NoteEvent in bases):
            cls.EventRegistry.append(event)
        else:
            raise ValueError, "Unknown bases class in event type: "+event.name
    register_event = classmethod(register_event)

    def parse_midi_event(self, track):
        """
        Reads bytes out of a data stream and returns a representation 
        of the next MIDI event. All events in a stream should be read 
        in turn using the same EventFactory, which keeps track 
        of things like running status.
        
        @param track: data stream to read bytes from
        @return: L{Event} subclass instance for the next MIDI event in 
            the track.
        
        """
        # first datum is varlen representing delta-time
        tick = read_varlen(track)
        self.RunningTick += tick
        # next byte is status message
        stsmsg = ord(track.next())
        # is the event a MetaEvent?
        if MetaEvent.is_event(stsmsg):
            # yes, figure out which one
            cmd = ord(track.next())
            for etype in self.MetaEventRegistry:
                if etype.is_meta_event(cmd):
                    evi = etype()
                    evi.decode(self.RunningTick, cmd, track)
                    return evi
            else:
                raise Warning, "Unknown Meta MIDI Event: " + `cmd`
        # not a Meta MIDI event, must be a general message
        else:
            for etype in self.EventRegistry:
                if etype.is_event(stsmsg):
                    self.RunningStatus = (stsmsg, etype)
                    evi = etype()
                    evi.decode(self.RunningTick, stsmsg, track)
                    return evi
            else:
                if self.RunningStatus:
                    cached_stsmsg, etype = self.RunningStatus
                    evi = etype()
                    evi.decode(self.RunningTick, 
                            cached_stsmsg, track, chr(stsmsg))
                    return evi
                else:
                    raise Warning, "Unknown MIDI Event: " + `stsmsg`

class NoteEvent(Event):
    """
    Abstract base class for L{NoteOnEvent} and L{NoteOffEvent}.
    
    """
    length = 2
    
    # Event attributes
    pitch = 60
    """ Note number (0-127) """
    velocity = 64
    """ How hard the note is played or how quickly it's released (0-127) """

    def __str__(self):
        return "%s [ %s(%s) %d ]" % \
                            (super(NoteEvent, self).__str__(),
                                NOTE_VALUE_MAP_SHARP[self.pitch],
                                self.pitch,
                                self.velocity)

    def decode_data(self):
        self.pitch = ord(self.data[0])
        self.velocity = ord(self.data[1])

    def encode_data(self):
        return chr(self.pitch) + chr(self.velocity)

class NoteOnEvent(NoteEvent):
    """
    Note-on event. Starts a note playing.
    
    """
    statusmsg = 0x90
    name = 'Note On'

class NoteOffEvent(NoteEvent):
    """
    Note-off event. Stops a note playing.
    
    """
    statusmsg = 0x80
    name = 'Note Off'

class AfterTouchEvent(Event):
    """
    Changes the pressure of aftertouch on a note.
    
    """
    statusmsg = 0xA0
    length = 2
    name = 'After Touch'
    
    # Event attributes
    pitch = 60
    """ Note number (0-127) """
    pressure = 0
    """ How hard to apply aftertouch (0-127) """

    def __str__(self):
        return "%s [ %s %s ]" % \
                            (super(AfterTouchEvent, self).__str__(),
                                hex(self.pitch),
                                hex(self.pressure))

    def decode_data(self):
        self.pitch = ord(self.data[0])
        self.pressure = ord(self.data[1])

    def encode_data(self):
        return chr(self.pitch) + chr(self.pressure)

class ControlChangeEvent(Event):
    """
    Sets the value of one of the 128 controllers available to a device.
    
    """
    # To do: properly print out bank changes, with msb and lsb calculated correctly.

    statusmsg = 0xB0
    length = 2
    name = 'Control Change'
    
    # Event attributes
    control = 0
    """ Which controller's value to set """
    value = 0
    """ Value to assign to the controller """
    
    def __str__(self):
        return "%s [ %s %s ]" % \
                            (super(ControlChangeEvent, self).__str__(),
                                constants.CONTROL_MESSAGE_DICTIONARY[self.control],
                                (self.value))

    def decode_data(self):
        self.control = ord(self.data[0])
        self.value = ord(self.data[1])

    def encode_data(self):
        return chr(self.control) + chr(self.value)

def all_notes_off_event(channel):
    """
    Creates an All Notes Off event. This is really a specialized control 
    change event and uses one of the reserved controller numbers.
    
    """
    ev = ControlChangeEvent()
    ev.channel = channel
    # This controller is reserved specially for this purpose
    ev.control = 123
    # I believe this is the only value that's valid
    ev.value = 0
    return ev

class ProgramChangeEvent(Event):
    """
    Changes the patch (voice) number of the instrument.
    
    """
    statusmsg = 0xC0
    length = 1
    name = 'Program Change'
    
    # Event attributes
    value = 0
    """ New patch number to select """

    def __str__(self):
        return "%s [ %s ]" % \
                            (super(ProgramChangeEvent, self).__str__(),
                                self.value)

    def decode_data(self):
        self.value = ord(self.data[0])

    def encode_data(self):
        return chr(self.value)

class ChannelAfterTouchEvent(Event):
    """
    Channel pressure (after-touch). Most often sent by pressing down 
    on the key after it "bottoms out". Different from polyphonic 
    after-touch. Use this message to send the single greatest pressure 
    value (of all the current depressed keys).
    
    """
    statusmsg = 0xD0
    length = 1
    name = 'Channel After Touch'
    
    # Event attributes
    pressure = 0
    """ Pressure value to set the channel's after touch to """

    def __str__(self):
        return "%s [ %s ]" % \
                            (super(ChannelAfterTouchEvent,self).__str__(),
                                hex(self.pressure))
                                
    def decode_data(self):
        self.pressure = ord(self.data[0])

    def encode_data(self):
        return chr(self.pressure)

class PitchWheelEvent(Event):
    """
    Change the pitch-bend wheel value. Given as a 14-bit value 
    (0-16,383), 8,192 being the neutral value.
    """
    statusmsg = 0xE0
    length = 2
    name = 'Pitch Wheel'
    
    # Event attributes
    value = 0x2222
    """ Pitch wheel position (0-16,383, middle 8,192). """

    #to do: multiply the pitch bend amount by the sensitivity to properly
    #display the amount of pitch bend
    def __str__(self):
        return "%s [ %s ]" % \
                            (super(PitchWheelEvent, self).__str__(),
                                self.value/8192.)

    def decode_data(self):
        first = ord(self.data[0])
        second = ord(self.data[1])
        if (first & 0x80) or (second & 0x80):
            raise Warning ("Pitch Wheel data out of range")
        self.value = ((second << 7) | first) - 0x2000

    def encode_data(self):
        value = self.value + 0x2000
        first = chr(value & 0x7F)
        second = chr((value >> 7) & 0xFF)
        return first + second

class SysExEvent(Event):
    """
    System exclusive MIDI event. Generic event type for sending data 
    to a system in a format that it recognizes, but which may not be 
    recognized by any other device.
    
    Some standards are defined for sub-event types of sysex. Tuning 
    messages are one example. This class implements encoding/decoding 
    for tuning messages.
    
    Other sysex events are treated just as raw data, between the initial
    F0 and the final F7.
    
    @todo: we should possibly terminate the sysex data on finding any 
    1-initial byte. Sysex messages are supposed to end with a 0xF7, but 
    the data can only contain 0-initial bytes (7-bit values).
    
    """
    statusmsg = 0xF0
    name = 'SysEx'
    subtype = 0
    allow_running = False
    
    SUBTYPE_NONE = 0
    SUBTYPE_SINGLE_NOTE_TUNING_CHANGE = 1
    
    # Event attributes
    data = ''
    """
    Data stored in the SysEx. This can be any data in a format that
    the device will recognise.
    """

    def is_event(cls, statusmsg):
        return (cls.statusmsg == statusmsg)
    is_event = classmethod(is_event)

    def decode(self, tick, statusmsg, track, runningstatus=''):
        assert(self.is_event(statusmsg))
        self.tick = tick
        if runningstatus != '':
            # SysEx events should not be used with running status
            raise MidiReadError, "sysex event was encountered with running status"
        length = read_varlen(track)
        self.data = ''
        # Keep getting data until we have the number of bytes specified
        self.data = ''.join([track.next() for i in range(length)])
        # Check we got the end marker, or at least a 1-initial byte
        #  at the end
        ender = ord(self.data[-1])
        self.data = self.data[:-1]
        if ender & 0x80 == 0:
            raise MidiReadError, "sysex didn't end with a status byte "\
                "(got %s, data %s)" % (hex(ender), " ".join([hex(b) for b in self.data]))
        self.decode_data()
            
    def encode(self, last_tick=0, running=False):
        if running:
            raise MidiWriteError, "sysex event cannot be encoded with running status"
        data = self.encode_data()
        return self.encode_delta_tick(last_tick=last_tick) + chr(self.statusmsg) + write_varlen(len(data)+1) + data + chr(0xF7)
        
    def decode_data(self):
        if len(self.data) >= 6 and \
                ord(self.data[0]) == 0x7F and \
                ord(self.data[2]) == 0x08 and \
                ord(self.data[3]) == 0x02:
            # This is a single note tuning change sysex event, as 
            #  defined by the MIDI standard on tuning messages
            self.init_subtype(SysExEvent.SUBTYPE_SINGLE_NOTE_TUNING_CHANGE)
            # First byte is the device id
            self.device_id = ord(self.data[1])
            self.tuning_program = ord(self.data[4])
            num_changes = ord(self.data[5])
            change_data = self.data[6:]
            if len(change_data) % 4 != 0:
                raise MidiReadError, "incomplete tuning change data in single note tuning change"
            # Get the data for each change
            self.changes = [(ord(change_data[i*4]), 
                             ord(change_data[i*4+1]),
                             (ord(change_data[i*4+2])<<7) + ord(change_data[i*4+3])
                            ) for i in range(len(change_data)/4)]
            if len(self.changes) != num_changes:
                raise Warning, "tuning change event reported wrong number of changes"
            
    def encode_data(self):
        if self.subtype == SysExEvent.SUBTYPE_SINGLE_NOTE_TUNING_CHANGE:
            data = chr(0x7F) + chr(self.device_number) + chr(0x08) + chr(0x02)
            data += chr(self.tuning_program)
            data += chr(len(self.changes))
            for key,semitone,freq in self.changes:
                data += chr(key)
                data += chr(semitone & 0x7F) + chr((freq >>7) & 0x7F) + chr(freq & 0x7F)
            return data
        else:
            return self.data
            
    def init_subtype(self, subtype):
        if subtype == SysExEvent.SUBTYPE_NONE:
            pass
        elif subtype == SysExEvent.SUBTYPE_SINGLE_NOTE_TUNING_CHANGE:
            self.name = 'Single Note Tuning Change'
            self.subtype = SysExEvent.SUBTYPE_SINGLE_NOTE_TUNING_CHANGE
            self.device_number = 0x7F
            self.tuning_program = 0
            self.changes = []
        else:
            raise MidiReadError, "unknown SysEx subtype identifier: %d" % subtype
            
    def __str__(self):
        out = super(SysExEvent, self).__str__()
        if self.subtype == SysExEvent.SUBTYPE_SINGLE_NOTE_TUNING_CHANGE:
            for key,semitone,freq in self.changes:
                out += " [ %d -> st %d + %f cents ]" % (key, semitone, float(freq)*100/(2**14))
        return out

def single_note_tuning_event(note_changes, device_number=None, tuning_program=None):
    """
    Returns a SysExEvent which will encode single note tuning changes 
    according to the MIDI tuning messages standard.
    
    note_changes should be a list of note changes, specified as triples:
     - (<note number>, <semitone>, <cents>)
    where:
     - <key number> is a note number (0-127) to retune, 
     - <semitone> is the nearest equal-temperament semitone below the 
     desired frequency (also a note number, 0-127), and 
     - <cents> is a float >= 0 and < 100 representing the number of 
     cents above the semitone's pitch to retune it to.
    
    """
    ev = SysExEvent()
    ev.init_subtype(SysExEvent.SUBTYPE_SINGLE_NOTE_TUNING_CHANGE)
    # Leave these as the defaults if no values are given
    if device_number is not None:
        ev.device_number = device_number
    if tuning_program is not None:
        ev.tuning_program = tuning_program
    ev.changes = [(key,semitone,int(float(cents)/100*(2**14))) for (key,semitone,cents) in note_changes]
    return ev


class SequenceNumberEvent(MetaEvent):
    """
    Defines the pattern number of a Type 2 MIDI file or the number of 
    a sequence in a Type 0 or Type 1 MIDI file. Should always have a 
    delta time of 0.
    
    """
    name = 'Sequence Number'
    metacommand = 0x00

class TextEvent(MetaEvent):
    """
    Defines some text which can be used for any reason including track 
    notes, comments. The text string is usually ASCII text, but may be 
    any character.
    
    """
    name = 'Text'
    metacommand = 0x01
    
    def __str__(self):
        return "%s [ %s ]" % \
                            (super(TextEvent, self).__str__(),
                            self.data)
    def encode_data(self):
        return self.data

class CopyrightEvent(MetaEvent):
    """
    Defines copyright information including the copyright symbol 
    (0xA9), year and author. Should always be in the first track chunk, 
    have a delta time of 0.
    
    """
    name = 'Copyright Notice'
    metacommand = 0x02

class TrackNameEvent(MetaEvent):
    """
    Defines the name of a sequence when in a Type 0 or Type 2 MIDI file 
    or in the first track of a Type 1 MIDI file. Defines a track name 
    when it appears in any track after the first in a Type 1 MIDI file. 
    
    """
    name = 'Track Name'
    metacommand = 0x03
    order = 3

    def __str__(self):
        return "%s [ %s ]" % \
                            (super(TrackNameEvent, self).__str__(),
                            self.data)

class InstrumentNameEvent(MetaEvent):
    """
    Defines the name of an instrument being used in the current track 
    chunk. This event can be used with the MIDI Channel Prefix meta 
    event to define which instrument is being used on a specific channel.
    
    """
    name = 'Instrument Name'
    metacommand = 0x04
    order = 4

    def __str__(self):
        return "%s [ %s ]" % \
                            (super(InstrumentNameEvent, self).__str__(),
                            self.data)


class LyricsEvent(MetaEvent):
    """
    Defines the lyrics in a song and usually used to define a syllable 
    or group of works per quarter note. This event can be used as an 
    equivalent of sheet music lyrics or for implementing a karaoke-style 
    system. 
    
    """
    name = 'Lyrics'
    metacommand = 0x05

    def __str__(self):
        return "%s [ %s ]" % \
                            (super(LyricsEvent, self).__str__(),
                            self.data)


class MarkerEvent(MetaEvent):
    """
    Marks a significant point in time for the sequence. Usually found 
    in the first track, but may appear in any. Can be useful for 
    marking the beginning/end of a new verse or chorus.
    
    """
    name = 'Marker'
    metacommand = 0x06

class CuePointEvent(MetaEvent):
    """
    Marks the start of some type of new sound or action. Usually found 
    in the first track, but may appear in any. Sometimes used by 
    sequencers to mark when playback of a sample or video should begin. 
    
    """
    name = 'Cue Point'
    metacommand = 0x07

class UnknownEvent(MetaEvent):
    name = 'whoknows?'
    metacommand = 0x09

class ChannelPrefixEvent(MetaEvent):
    """
    Associates a MIDI channel with following meta events. Its effect 
    is terminated by another MIDI Channel Prefix event or any non-meta 
    event. Often used before an Instrument Name Event to specify which 
    channel an instrument name represents. 
    
    """
    name = 'Channel Prefix'
    metacommand = 0x20

    def __str__(self):
        return "%s [ %s ]" % \
                            (super(ChannelPrefixEvent, self).__str__(),
                            ord(self.data))

class PortEvent(MetaEvent):
    """
    Specifies which MIDI port should be used to output all subsequent 
    events.
    
    """
    name = 'MIDI Port/Cable'
    metacommand = 0x21
    order = 5
    
    # Event attributes
    port = 0
    """ MIDI port to switch to. """

    def __str__(self):
        return "%s [ port: %d ]" % \
                            (super(PortEvent, self).__str__(),
                            self.port)

    def decode_data(self):
        if len(self.data) != 1:
            raise MidiReadError, "port event data should be 1 byte long"
        self.port = ord(self.data[0])

    def encode_data(self):
        return chr(self.port)

class TrackLoopEvent(MetaEvent):
    name = 'Track Loop'
    metacommand = 0x2E

class EndOfTrackEvent(MetaEvent):
    """
    Appears and the end of each track to mark the end.
    
    Note that you don't need to add this to tracks in an L{EventStream} - 
    it gets added automatically.
    
    """
    name = 'End of Track'
    metacommand = 0x2F
    order = 2

class SetTempoEvent(MetaEvent):
    """
    Change the tempo of events played after this point. In the MIDI 
    data, the tempo is stored in microseconds per quarter note (MPQN), 
    but you may also specify it in beats per minute via the C{tempo} 
    attribute.
    
    """
    name = 'Set Tempo'
    metacommand = 0x51
    order = 1
    
    # Event attributes
    tempo = 120
    """ Tempo value in beats per minute (MM) """
    mpqn = int(float(6e7) / 120)
    """ Tempo value in microseconds per quarter note """

    def __str__(self):
        return "%s [ mpqn: %d tempo: %d ]" % \
                            (super(SetTempoEvent, self).__str__(),
                            self.mpqn, self.tempo)

    def __setattr__(self, item, value):
        if item == 'mpqn':
            self.__dict__['mpqn'] = value
            self.__dict__['tempo'] = float(6e7) / value 
        elif item == 'tempo':
            self.__dict__['tempo'] = value
            self.__dict__['mpqn'] = int(float(6e7) / value)
        else:
            self.__dict__[item] = value

    def decode_data(self):
        if len(self.data) != 3:
            raise MidiReadError, "tempo event data should be 3 bytes long"
        self.mpqn = (ord(self.data[0]) << 16) + (ord(self.data[1]) << 8) \
                        + ord(self.data[2])

    def encode_data(self):
        self.mpqn = int(float(6e7) / self.tempo)
        return chr((self.mpqn & 0xFF0000) >> 16) + \
                    chr((self.mpqn & 0xFF00) >> 8) + \
                    chr((self.mpqn & 0xFF))

class SmpteOffsetEvent(MetaEvent):
    """
    Designates the SMPTE start time (hours, minutes, secs, frames, 
    subframes) of the track. Should be at the start of the track. 
    The hour should not be encoded with the SMPTE format as it is in 
    MIDI Time Code. In a format 1 file, the SMPTE OFFSET must be stored 
    with the tempo map (ie, the first track). The final byte contains 
    fractional frames in 100ths of a frame.
    
    Data should be encoded as 5 bytes: 
    <hour> <min> <sec> <frame> <fractional-frames>.
    
    @note: encoding is not currently implemented, so you need to do 
    it manually and set the C{data} attribute.
    
    """
    name = 'SMPTE Offset'
    metacommand = 0x54

class TimeSignatureEvent(MetaEvent):
    """
    Expressed as 4 numbers: 
    <numerator> <denominator> <metronome> <thirtyseconds>.
    
    <numerator> and <denominator> represent the parts of the 
    signature as notated on sheet music. The denominator must be a 
    power of 2: 2 = quarter note, 3 = eighth, etc.
    
    <metronome> expresses the number of MIDI clocks in a metronome click. 
    
    <thirtyseconds> expresses the number of notated 32nd notes in a MIDI 
    quarter note (24 MIDI clocks).
    
    This event allows a program to relate what MIDI thinks of as a 
    quarter, to something entirely different.
    
    """
    name = 'Time Signature'
    metacommand = 0x58
    order = 0
    
    # Event attributes
    numerator = 4
    """ Top part of the time signature. """
    denominator = 4
    """ Bottom part of the time signature (must be a power of 2). """
    metronome = 24
    """ Number of MIDI clocks in a metronome click. """
    thirtyseconds = 8
    """ Number of 32nd notes in 24 MIDI clocks. """

    def __str__(self):
        return "%s [ %d/%d  metro: %d  32nds: %d ]" % \
                            (super(TimeSignatureEvent, self).__str__(),
                                self.numerator, self.denominator,
                                self.metronome, self.thirtyseconds)

    def decode_data(self):
        if len(self.data) != 4:
            raise MidiReadError, "time signature event data should be 4 bytes long"
        self.numerator = ord(self.data[0])
        # Weird: the denominator is two to the power of the data variable
        self.denominator = 2 ** ord(self.data[1])
        self.metronome = ord(self.data[2])
        self.thirtyseconds = ord(self.data[3])

    def encode_data(self):
        return chr(self.numerator) + \
                    chr(int(log(self.denominator,2))) + \
                    chr(self.metronome) + \
                    chr(self.thirtyseconds)


class KeySignatureEvent(MetaEvent):
    """
    Sets the key signature, made up of a number of sharps/flats and 
    either major or minor.
    
    """
    name = 'Key Signature'
    metacommand = 0x59
    
    # Event attributes
    accidentals = 0
    """ Number of sharps/flats. Positive sharps, negative flats. """
    major = True
    """ Major or minor: True for major, False for minor. """
    
    def __str__(self):
        return "%s [ %d%s %s ]" % \
                            (super(KeySignatureEvent, self).__str__(),
                                abs(self.accidentals),
                                self.accidentals >= 0 and "#" or "b",
                                self.major and "major" or "minor")

    def decode_data(self):
        self.accidentals = ord(self.data[0])
        self.major = ord(self.data[1]) == 0

    ##should encode 0 for major, 1 for minor.
    def encode_data(self):
        return chr(self.accidentals) + chr(not self.major)

class BeatMarkerEvent(MetaEvent):
    name = 'Beat Marker'
    metacommand = 0x7F

class SequencerSpecificEvent(MetaEvent):
    """
    Specifies information specific to a hardware or software sequencer. 
    The first data byte (or three bytes if the first byte is 0) 
    specifies the manufacturer's ID and the following bytes contain 
    information specified by the manufacturer.
    
    Individual manufacturers may document this in their manuals. 
    
    """
    name = 'Sequencer Specific'
    metacommand = 0x7F


class TempoMap(list):
    def __init__(self, stream):
        self.stream = stream

    def add_and_update(self, event):
        self.add(event)
        self.update()

    def add(self, event):
        # get tempo in microseconds per beat
        tempo = event.mpqn
        # convert into milliseconds per beat
        tempo = tempo / 1000.0
        # generate ms per tick
        event.mpt = tempo / self.stream.resolution
        self.append(event)

    def update(self):
        self.sort()
        # adjust running time
        last = None
        for event in self:
            if last:
                event.msdelay = last.msdelay + \
                    int(last.mpt * (event.tick - last.tick))
            last = event

    def get_tempo(self, offset=0):
        if len(self) == 0:
            # Default tempo is 120 bpm
            # No tempo exists in the tempo map, so use a default
            def_tempo = SetTempoEvent()
            def_tempo.tempo = 120
            # Set the mpt, as if this has been added to the map
            def_tempo.mpt = def_tempo.mpqn / 1000.0 / self.stream.resolution
            return def_tempo
        else:
            last = self[0]
            for tm in self[1:]:
                if tm.tick > offset:
                    return last
                last = tm
            return last

class EventStreamIterator(object):
    def __init__(self, stream, window):
        self.stream = stream
        self.trackpool = stream.trackpool
        self.window_length = window
        self.window_edge = 0
        self.leftover = None
        self.events = self.stream.iterevents()
        # First, need to look ahead to see when the
        # tempo markers end
        self.ttpts = []
        for tempo in stream.tempomap[1:]:
            self.ttpts.append(tempo.tick)
        # Finally, add the end of track tick.
        self.ttpts.append(stream.endoftrack.tick)
        self.ttpts = iter(self.ttpts)
        # Setup next tempo timepoint
        self.ttp = self.ttpts.next()
        self.tempomap = iter(self.stream.tempomap)
        self.tempo = self.tempomap.next()
        self.endoftrack = False

    def __iter__(self):
        return self

    def __next_edge(self):
        if self.endoftrack:
            raise StopIteration
        lastedge = self.window_edge
        self.window_edge += int(self.window_length / self.tempo.mpt)
        if self.window_edge > self.ttp:
            # We're past the tempo-marker.
            oldttp = self.ttp
            try:
                self.ttp = self.ttpts.next()
            except StopIteration:
                # End of Track!
                self.window_edge = self.ttp
                self.endoftrack = True
                return
            # Calculate the next window edge, taking into
            # account the tempo change.
            msused = (oldttp - lastedge) * self.tempo.mpt
            msleft = self.window_length - msused
            self.tempo = self.tempomap.next()
            ticksleft = msleft / self.tempo.mpt
            self.window_edge = ticksleft + self.tempo.tick

    def next(self):
        ret = []
        self.__next_edge()
        if self.leftover:
            if self.leftover.tick > self.window_edge:
                return ret
            ret.append(self.leftover)
            self.leftover = None
        for event in self.events:
            if event.tick > self.window_edge:
                self.leftover = event
                return ret
            ret.append(event)
        return ret


class EventStream(object):
    """
    Class used to describe a collection of MIDI events, organized into 
    tracks.
    
    """
    def __init__(self):
        self.format = 1
        self.tempomap = TempoMap(self)
        self._curtrack = None
        self.trackpool = []
        self.tracklist = {}
        self.timemap = []
        self.endoftracks = {}
        self.beatmap = []
        self.resolution = 220
        self.tracknames = {}

    def __set_resolution(self, resolution):
        # XXX: Add code to rescale notes
        assert(not self.trackpool)
        self.__resolution = resolution
        self.beatmap = []
        for value in BEATVALUES:
            self.beatmap.append(int(value * resolution))

    def __get_resolution(self):
        return self.__resolution
    resolution = property(__get_resolution, __set_resolution, None,
                                "Ticks per quarter note")

    def add_track(self):
        # Move on to the next, new track (track 0 if none exists yet)
        self._curtrack = len(self)
        self.endoftrack = None
        self.tracklist[self._curtrack] = []
        # Type 0 midi files only support one track
        # If adding more than one track, make this a type 1 file
        if len(self) > 1:
            self.format = 1

    def get_current_track_number(self):
        return self._curtrack

    def get_track_by_number(self, tracknum):
        return self.tracklist[tracknum]

    def get_current_track(self):
        return self.tracklist[self._curtrack]

    def get_track_by_name(self, trackname):
        tracknum = self.tracknames[trackname]
        return self.get_track_by_number(tracknum)

    def replace_current_track(self, track):
        self.tracklist[self._curtrack] = track
        self.__refresh()

    def replace_track_by_number(self, tracknum, track):
        self.tracklist[tracknumber] = track
        self.__refresh()

    def replace_track_by_name(self, trackname, track):
        tracknum = self.tracklist[tracknum]
        self.repdeletelace_track_by_number(tracknum, track)

    def delete_current_track(self):
        del self.tracklist[self._curtrack]
        self.__refresh()

    def delete_track_by_number(self, tracknum):
        del self.tracklist[tracknum]
        self.__refresh()

    def delete_track_by_name(self, trackname, track):
        tracknum = self.tracklist[trackname]
        self.delete_track_by_number(tracknum, track)

    def add_event(self, event):
        if not isinstance(event, EndOfTrackEvent):
            event.track = self.curtrack
            self.trackpool.append(event)
            self.track.append(event)
        self.__adjust_endoftrack(event)
        
        if isinstance(event, TrackNameEvent):
            self.__refresh_tracknames()
        if isinstance(event, SetTempoEvent):
            self.tempomap.add_and_update(event)
            self.__refresh_timemap()
        else:
            tempo = self.tempomap.get_tempo(event.tick)
            event.adjust_msdelay(tempo)
    
    def _add_event_without_timemap(self, event):
        """
        Like add_event, but doesn't update the timemap after adding the event.
        You shouldn't usually use this, since it leaves the timemap in an 
        inconsistent state, but it's used internally when adding a lot of 
        events in a row. If you use it, you should ensure that _refresh_timemap 
        gets called afterwards.
        
        """
        if not isinstance(event, EndOfTrackEvent):
            event.track = self.curtrack
            self.trackpool.append(event)
            self.track.append(event)
        self.__adjust_endoftrack(event)
        
        if isinstance(event, TrackNameEvent):
            self.__refresh_tracknames()
        if isinstance(event, SetTempoEvent):
            self.tempomap.add_and_update(event)

    def get_tempo(self, offset=0):
        return self.tempomap.get_tempo(offset)

    def timesort(self):
        self.trackpool.sort()
        for track in self.tracklist.values():
            track.sort()
    
    def textdump(self):
        for event in self.trackpool:
            print event

    def __iter__(self):
        return iter(self.tracklist.values())

    def iterevents(self, mswindow=0):
        self.timesort()
        if mswindow:
            return EventStreamIterator(self, mswindow)
        return iter(self.trackpool)
        
    @property
    def duration(self):
        """
        The length of the stream in midi ticks.
        Note that this is not the same as len(stream), which gives the 
        number of tracks.
        
        """
        if len(self.trackpool):
            return max(self.trackpool).tick
        else:
            return 0
        
    def __get_trackcount(self):
        return len(self.tracklist)
    trackcount = property(__get_trackcount)

    def __len__(self):
        return self.trackcount

    def __getitem__(self, intkey):
        return self.tracklist[intkey]

    def __refresh(self):
        self.__refresh_trackpool()
        self.__refresh_tempomap()
        self.__refresh_timemap()
        self.__refresh_tracknames()

    def __refresh_tracknames(self):
        self.tracknames = {}
        for tracknum in self.tracklist:
            track = self.tracklist[tracknum]
            for event in track:
                if isinstance(event, TrackNameEvent):
                    self.tracknames[event.data] = tracknum
                    break

    def __refresh_trackpool(self):
        self.trackpool = []
        for track in self.tracklist.values():
            for event in track:
                self.trackpool.append(event)
        self.trackpool.sort()

    def __refresh_tempomap(self):
        self.tempomap = TempoMap(self)
        
        for tracknum,track in self.tracklist.items():
            self.endoftracks[tracknum] = None
            
            eots = []
            for event in track:
                if isinstance(event, SetTempoEvent):
                    self.tempomap.add(event)
                elif isinstance(event, EndOfTrackEvent):
                    eots.append(event)
            # Only allow one EOT in each track
            eots.sort()
            if len(eots) > 1:
                for eot in eots[:-1]:
                    track.remove(eot)
                    self.trackpool.remove(eot)
            if len(eots):
                self.__adjust_endoftrack(eots[-1], track=tracknum)
        self.tempomap.update()

    def __refresh_timemap(self):
        for event in self.trackpool:
            if not isinstance(event, SetTempoEvent):
                tempo = self.tempomap.get_tempo(event.tick)
                event.adjust_msdelay(tempo)
    _refresh_timemap = __refresh_timemap

    def __adjust_endoftrack(self, event, track=None):
        """
        Track defaults to the current track.
        The event itself is assumed to be in the track already.
        
        """
        if track is None:
            track = self.curtrack
        
        if self.endoftracks[track] is None:
            if isinstance(event, EndOfTrackEvent):
                eot_event = event
            else:
                # We don't have an EOT event for this track and the 
                #  given event isn't one itself, so make a new one
                eot_event = EndOfTrackEvent()
                eot_event.tick = event.tick
            eot_event.track = self.curtrack
            self.trackpool.append(eot_event)
            self.tracklist[track].append(eot_event)
            self.endoftracks[track] = eot_event
        else:
            # Update the time of the EOT event already in use
            self.endoftracks[track].tick = max(event.tick+1, self.endoftracks[track].tick)
        if self.tempomap:
            tempo = self.tempomap.get_tempo(self.endoftracks[track].tick)
            self.endoftracks[track].adjust_msdelay(tempo)
    
    def __get_endoftrack(self):
        return self.endoftracks[self.curtrack]
    def __set_endoftrack(self, eot):
        self.endoftracks[self.curtrack] = eot
    endoftrack = property(__get_endoftrack, __set_endoftrack)
    
    def __get_track_num(self):
        return self._curtrack
    def __set_track_num(self, num):
        if num not in self.tracklist:
            raise ValueError, "track number %d does not exist" % num
        self._curtrack = num
    curtrack = property(__get_track_num, __set_track_num, 
            delete_current_track, 
            """The track number of the current track""")
    
    track = property(get_current_track, replace_current_track, 
            delete_current_track, 
            """The current track""")
    
    def remove_event(self, ev, track=None):
        """
        Remove the first occurence of an event matching the 
        given event from the event stream. Raises a 
        ValueError a match is not found in the stream.
        
        @type track: int
        @param track: track number to look for the event in. If not 
            given, all tracks are searched.
        
        """
        if track is None:
            tracks = self.tracklist.values()
        else:
            tracks = [self.tracklist[track]]
        
        for trck in tracks:
            if ev in trck:
                trck.remove(ev)
                self.__refresh()
                return
                
        if track is None:
            track_mess = ""
        else:
            track_mess = ", track %d" % track
        raise ValueError, "remove_event: event %s not found in stream%s" % \
                            (ev, track_mess)
                            
    def remove_event_instance(self, ev, track=None):
        """
        Removes the event instance from a stream, if it exists. Raises a 
        ValueError a match is not found in the stream.
        
        Note that this is different from L{remove_event}, which looks 
        for a match to the argument, whereas this requires identity.
        
        @type track: int
        @param track: track number to look for the event in. If not 
            given, all tracks are searched.
        
        """
        if track is None:
            tracks = self.tracklist.values()
        else:
            tracks = [self.tracklist[track]]
        
        for trck in tracks:
            track_ids = [id(e) for e in trck]
            if id(ev) in track_ids:
                trck.pop(track_ids.index(id(ev)))
                self.__refresh()
                return
                
        if track is None:
            track_mess = ""
        else:
            track_mess = ", track %d" % track
        raise ValueError, "remove_event: event %s not found in stream%s" % \
                            (ev, track_mess)
    
    def remove_event_instances(self, evs):
        """
        Has the same effect as calling L{remove_event_instance} on each members 
        of C{evs}, but is a lot faster if removing many events in one go.
        
        Note that this won't raise an exception if any of the events aren't 
        found.
        
        """
        remove_ids = [id(e) for e in evs]
        
        for tracknum in self.tracklist.keys():
            self.tracklist[tracknum] = \
                [ev for ev in self.tracklist[tracknum] if id(ev) not in remove_ids]
        self.__refresh()
    
    def slice(self, start, end=None):
        from slice import EventStreamSlice
        return EventStreamSlice(self, start, end)

    def clean_midi(self):
        """
        Unimplemented. Will check for redundant messages and delete them,
        such as control changes that are followed by a "Reset Controllers"
        message before a note on.
        
        """
        pass

class EventStreamWriter(object):
    """
    Takes care of writing MIDI data from an L{EventStream} to an output 
    stream, such as a file.
    
    """
    def __init__(self, midistream, output):
        if isinstance(output, str):
            output = open(output, 'w')
        self.output = output
        self.midistream = midistream
        self.write_file_header()
        for i,track in enumerate(self.midistream):
            self.write_track(track)
    
    def write(cls, midistream, output):
        cls(midistream, output)
    write = classmethod(write)
        
    def write_file_header(self):
        # First four bytes are MIDI header
        packdata = pack(">LHHH", 6,    
                            self.midistream.format, 
                            self.midistream.trackcount, 
                            self.midistream.resolution)
        self.output.write('MThd%s' % packdata)
            
    def write_track_header(self, trklen):
        self.output.write('MTrk%s' % pack(">L", trklen))

    def write_track(self, track):
        buf = ''
        track = copy.copy(track)
        track.sort()
        last_tick = delta = 0
        smsg = 0
        chn = 0
        for event in track:
            running = (event.allow_running and (smsg == event.statusmsg) and (chn == event.channel))
            this_encoding=event.encode(last_tick=last_tick, running=running)
            buf += this_encoding
            last_tick = event.tick
            # Only allow status to run if the event is of an appropriate type
            if event.allow_running:
                smsg = event.statusmsg 
                chn = event.channel
            else:
                # Some events cannot have running status
                # They cancel any previous running status
                smsg = 0
                chn = 0
        self.write_track_header(len(buf))
        self.output.write(buf)

class EventStreamReader(object):
    """
    Reads MIDI data in from an input stream, probably a file, and 
    produces an L{EventStream} to represent it internally.
    
    """
    def __init__(self, instream, outstream, force_resolution=None):
        self.eventfactory = None
        self.force_resolution = force_resolution
        self.parse(instream, outstream)

    def read(cls, instream, *args, **kwargs):
        if len(args) > 0:
            outstream = args[0]
        else:
            outstream = kwargs.pop('outstream', None)
        if not outstream:
            outstream = EventStream()
        cls(instream, outstream, *args, **kwargs)
        return outstream
    read = classmethod(read)
    
    def parse(self, instream, outstream):
        self.midistream = outstream
        if isinstance(instream, str):
            instream = open(instream)
        self.instream = instream
        if isinstance(instream, file):
            self.instream = StringIO(instream.read())
            self.cursor = 0
        # XXX: unicode?
        else:
            # Assume this is a file-like object (like a StringIO)
            #  without checking the type
            self.instream = instream
        self.parse_file_header()
        for track in range(self.tracks_to_read):  
            trksz = self.parse_track_header()
            self.eventfactory = EventFactory()
            self.midistream.add_track()
            self.parse_track(trksz)
        # We didn't do this while adding each event, so do it once now instead
        self.midistream._refresh_timemap()
        
    def parse_file_header(self):
        # First four bytes are MIDI header
        magic = self.instream.read(4)
        if magic != 'MThd':
            raise MidiReadError, "Bad header in MIDI file."
        # next four bytes are header size
        # next two bytes specify the format version
        # next two bytes specify the number of tracks
        # next two bytes specify the resolution/PPQ/Parts Per Quarter
        # (in other words, how many ticks per quater note)
        data = unpack(">LHHH", self.instream.read(10))
        hdrsz = data[0]
        self.midistream.format = data[1]
        # Let the trackcount be calculated from the number of tracks we find
        self.tracks_to_read = data[2]
        self.midistream.resolution = self.force_resolution or data[3]
        # XXX: the assumption is that any remaining bytes
        # in the header are padding
        if hdrsz > DEFAULT_MIDI_HEADER_SIZE:
            self.instream.read(hdrsz - DEFAULT_MIDI_HEADER_SIZE)
            
    def parse_track_header(self):
        # First four bytes are Track header
        magic = self.instream.read(4)
        if magic != 'MTrk':
            raise MidiReadError, "Bad track header in MIDI file: " + magic
        # next four bytes are header size
        trksz = unpack(">L", self.instream.read(4))[0]
        return trksz

    def parse_track(self, trksz):
        track = iter(self.instream.read(trksz))
        while True:
            try:
                event = self.eventfactory.parse_midi_event(track)
                # Don't refresh the timemap for every event
                # It's very important that _refresh_timemap gets called after 
                #  this (in parse()), since we don't do it here
                self.midistream._add_event_without_timemap(event)
            except Warning, err:
                print "Warning: %s" % err
            except StopIteration:
                break
                
def check_midi(mid):
    """
    Midi debugger. Checks through a midi event stream for things 
    that might be wrong with it.
    
    @todo: add more possible problems to the checks.
    
    @type mid: L{EventStream}
    @param mid: midi stream to check
    @return: list of tuples, consisting of a string problems identifier,
        a descriptive message and a tuple of midi events that generated 
        the problem.
    
    """
    problems = []
    for event in mid.trackpool:
        if event.tick < 0:
            # Negative timing
            problems.append(
                ("Negative time", "negative time value: %d" % event.tick, (event,)) )
        if event.msdelay < 0:
            # Negative timing in the MS time
            problems.append(
                ("Negative MS time", "negative millisecond time value: %s" % event.msdelay, (event,)) )
        # Check for more potential problems
    return problems

def new_stream(tempo=120, resolution=480, format=1):
    stream = EventStream()
    stream.format = format
    stream.resolution = resolution
    stream.add_track()
    tempoev = SetTempoEvent()
    tempoev.tempo = tempo
    tempoev.tick = 0
    stream.add_event(tempoev)
    return stream

read_midifile = EventStreamReader.read
"""
Reads in a MIDI file given by a file object or filename and returns 
an L{EventStream}.
"""
write_midifile = EventStreamWriter.write
"""
Writes an L{EventStream} out to a MIDI file.
"""

class MidiReadError(Exception):
    """
    Usually raised on encountering invalid MIDI data while parsing.
    Some mildly bad things may be overlooked, but critical errors in 
    the data will cause the reader to raise a MidiReadError.
    
    """
    pass
    
class MidiWriteError(Exception):
    pass
