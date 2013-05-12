"""
Interface to the PyGame mixer module, which is able to play fully 
formed midi files using Timidity.
We play midi streams simply by outputing to a temporary midi file and 
playing that.

The alternative approach explored in sequencer_portmidi is much nicer 
in principle, but doesn't work.

@note: Requires PyGame to be installed
@note: PyGame requires SDL to be installed and configured to play 
midi files. It uses a nasty old version of Timidity and requires you 
to have GUS-compatible patches installed.

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

try:
    import pygame
except ImportError:
    raise ImportError, "PyGame needs to be installed before you can load the sequencer"
import pygame.midi

from midi import write_midifile, read_midifile, NoteOnEvent, NoteOffEvent, \
                ProgramChangeEvent, MetaEvent, SysExEvent

import time
from tempfile import TemporaryFile
from threading import Thread, Event
from pygame import mixer, event, USEREVENT
# Initialize the PyGame mixer module
pygame.init()
mixer.init()

class Sequencer(object):
    """
    Midi sequencer that outputs midi to a temporary file and plays it 
    using PyGame's interface to the SDL mixer.
    
    """
    def __init__(self, stream=None):
        self.playing = False
        self._music_temp = None
        if stream is not None:
            self.load_stream(stream)

    def load_stream(self, stream):
        """
        Loads the whole of an L{EventStream<midi.EventStream>}.
        Call L{play} to start playback.
        
        """
        temp_file = TemporaryFile(suffix=".mid")
        write_midifile(stream, temp_file)
        temp_file.seek(0)
        mixer.music.load(temp_file)
        self._music_loaded = True
    
    def stop(self):
        if self.playing:
            mixer.music.stop()
            
    def play(self, block=False):
        if not self.playing and self._music_loaded:
            if block:
                # Create a condition that will be notified when the music stops
                ev = Event()
            else:
                ev = None
            on_music_end(self._cleanup, event=ev)
            mixer.music.play()
            self.playing = True
            
            if block:
                # Don't just wait, because then we'd fail to receive signals 
                #  in this thread (this is a Python bug)
                # Instead, wake up a few times a second and start waiting again
                # wait() returns False if the timeout fired
                while not ev.wait(0.3):
                    pass
            
    def pause(self):
        if self.playing:
            mixer.music.pause()
            
    def unpause(self):
        if self.playing:
            mixer.music.unpause()
    
    def _cleanup(self):
        """ Called once playback is finished """
        # Get rid of the temporary file
        if self._music_temp is not None:
            self._music_temp.close()
            self._music_temp = None
        self.playing = False
            
    @property
    def music_loaded(self):
        return self._music_temp is not None

class MusicEndWaiter(Thread):
    """
    Sets an endevent on the PyGame mixer so that it gets notified when 
    the music comes to an end. Executes a callback function when this 
    happens.
    
    """
    def __init__(self, callback, event=None):
        super(MusicEndWaiter, self).__init__()
        self.daemon = True
        self.callback = callback
        
        self.event = event
        
    def run(self):
        mixer.music.set_endevent(USEREVENT)
        while True:
            error = False
            try:
                ev = event.wait()
            except:
                # If anything went wrong with the queue, just give up waiting
                error = True
            
            if error or ev.type == USEREVENT:
                # This usually gets fired a bit too early, so wait a 
                #  bit before we call the cleanup
                time.sleep(0.1)
                self.__dict__["callback"]()
                if self.event is not None:
                    self.event.set()
                return

def on_music_end(callback, event=None):
    waiter = MusicEndWaiter(callback, event=event)
    waiter.start()

class RealtimeSequencer(object):
    """
    Sends realtime midi events to midi devices through Pygame.
    
    This class takes care of converting our native event representation into 
    what PyGame needs.
    
    """
    def __init__(self, device=0):
        self.device = device
        
        # Initialize the midi module
        pygame.midi.init()
        
        # Prepare an output to the requested device
        self.output = pygame.midi.Output(device)
    
    def send_event(self, event):
        """
        Sends the midi event (given in our representation) to the midi device.
        
        """
        # Ignore meta events
        if isinstance(event, MetaEvent):
            return
        # Handle certain types of events using PyGame's special methods
        if type(event) == NoteOnEvent:
            self.output.note_on(event.pitch, 
                                velocity=event.velocity, 
                                channel=event.channel)
        elif type(event) == NoteOffEvent:
            self.output.note_off(event.pitch,
                                 velocity=event.velocity,
                                 channel=event.channel)
        elif type(event) == ProgramChangeEvent:
            self.output.set_instrument(event.value,
                                       channel=event.channel)
        elif type(event) == SysExEvent:
            # Send the sysex data
            data = [0xF0] + [ord(b) for b in event.encode_data()] + [0xF7]
            self.output.write_sys_ex(0, data)
        else:
            # Convert this to binary form to write to the device
            data = event.encode_data()
            status = (event.statusmsg & 0xF0) | (0x0F & event.channel)
            midi_bytes = [ [[status] + [ord(b) for b in data], 0] ]
            self.output.write(midi_bytes)

def get_midi_devices():
    """
    Returns a list of tuples with information about available midi devices, 
    as returned by PyGame's get_device_info() function.
    
    The list indices correspond to pygame's device ids.
    
    """
    pygame.midi.init()
    return [
        pygame.midi.get_device_info(i) for i in range(pygame.midi.get_count())
    ]
        
