"""
Interface to the PyGame midi module, which uses Portmidi to access 
system midi devices.
This interface allows data to be sent using the Midi library's 
own representation.

Note that PyGame needs to be installed. An error will be raised if 
you try importing this module without PyGame installed.

@todo: This isn't working yet. It's a nice idea, but it's proving 
very difficult to get the timing to work out right. It seems that 
writing to the midi output stream takes a long time and holds up the 
playback, making a mess of the timings of events.

"""

try:
    import pygame
except ImportError:
    raise ImportError, "PyGame needs to be installed before you can load the sequencer"

from pygame import midi as pgmidi
# Initialize the PyGame midi module
pygame.init()
pgmidi.init()

from pygame import event as pgevent
from threading import Thread
from datetime import datetime, timedelta
from time import sleep

from midi import MetaEvent, SysExEvent, NoteOffEvent, NoteOnEvent

class Sequencer(object):
    """
    Midi sequencer that sends midi events to system midi devices using 
    PyGame's interface to Portmidi.
    
    """
    def __init__(self, output_device=None, latency=None):
        """
        @type output_device: int
        @param output_device: Portmidi device number to use for output. Will 
            use the reported default if not given.
        @type latency: int
        @param latency: latency value to use PortMidi output with. 0 is 
            not permitted, as it prevents us doing timestamped events.
        
        """
        if output_device is None:
            output_device = pgmidi.get_default_output_id()
        self.output_device = output_device
        
        latency = 100
        
        # Check the output device exists
        devs = Sequencer.get_devices()
        if output_device >= len(devs):
            raise SequencerInitializationError, "sequencer tried to use "\
                "non-existent output device: %d. Only %d devices exist." % \
                (output_device, len(devs))
        # Check it can accept output
        if devs[output_device][1][3] == 0:
            raise SequencerInitializationError, "cannot use %s as an "\
                "output device: it doesn't accept output." % \
                devs[output_device][1][1]
        
        # Initialize the output device
        self.output = pgmidi.Output(output_device, latency=latency, buffer_size=1024*50)
        self._sequencer = None
        self._queue = {}

    @staticmethod
    def get_devices(inputs=True, outputs=True):
        """
        Queries available devices. Returns list of pairs 
        C{(index,device_info)}. C{index} is the device number by which 
        it can be accessed. C{device_info} is a tuple in the same 
        format as C{pygame.midi.get_device_info()}:
        (interf, name, input, output, opened)
        
        """
        devices = [(num,pgmidi.get_device_info(num)) for num in range(pgmidi.get_count())]
        if inputs and not outputs:
            devices = [d for d in devices if d[1][2] == 1]
        elif outputs and not inputs:
            devices = [d for d in devices if d[1][3] == 1]
        elif not inputs and not outputs:
            return []
        return devices
    
    def write(self, events, time_offset=0):
        """
        Plays a list of events through the output device. Delta times 
        between the events are preserved, but the first event is played 
        immediately, or after the given offset (in miliseconds)
        
        """
        if len(events) == 0:
            return
        
        # Encode all the events as PyGame needs them
        event_list = []
        raw_events = []
        for ev in events:
            # Ignore meta events, as they only make sense in a file
            if isinstance(ev, (MetaEvent,SysExEvent)):
                # TODO: do something special with sysexs
                continue
            # Set all the deltas to 0 for now
            data = ev.encode(last_tick=ev.tick)
            # Get each byte as an int in a list (ignore the tick)
            data = [ord(b) for b in data[1:]] + [0]*(5-len(data))
            event_list.append((data,ev.msdelay+time_offset))
            raw_events.append(ev)
        
        # Ask for everything to be played this offset from now
        now = pgmidi.time()+4000
        
        # Make all times relative to now
        event_list = [[bytes,time+now] for (bytes,time) in event_list]
        
        ####
        #for bytes,time in event_list:
        #    self.queue_event(bytes, time)
        #
        #self.play()
        #return
        
        for event in event_list[:2000]:
            self.output.write([event])
        return
        ####
        
        ## Split up into chunks not longer than 1024 events
        #ev_chunks = []
        #cursor = 0
        #chunk_size = 100
        #while cursor < len(event_list):
        #    ev_chunks.append(event_list[cursor:cursor+chunk_size])
        #    cursor += chunk_size
        #
        #for chunk in ev_chunks:
        #    self.output.write(chunk)
        #    print "Chunk written"
        #print "Finished writing"
        
    def queue_event(self, midi_event, time):
        self._queue.setdefault(time, []).append(midi_event)
    
    def play_stream(self, stream):
        """
        Sends the whole of an L{EventStream<midi.EventStream>} to the 
        sequencer output.
        
        """
        events = list(sorted(stream.trackpool))
        self.write(events)
    
    def stop(self):
        if self.playing:
            self._sequencer.stop()
            self._sequencer = None
            
    def play(self, latency=0):
        if self.playing:
            self.stop()
        sequencer = SequencerThread(self.output, self._queue)
        sequencer.start()
        self._sequencer = sequencer
        print "playing"
        
    @property
    def playing(self):
        return self._sequencer is not None
        
class SequencerThread(Thread):
    def __init__(self, output, queue, buffer_time=10000, buffer_advance=2000):
        super(SequencerThread, self).__init__()
        self.output = output
        self._queue = queue
        self._stopped = False
        self.buffer_time = buffer_time
        self.buffer_advance = buffer_advance
        
    def stop(self):
        self._stopped = True
        
    def run(self):
        start_time = pgmidi.time() + 3000
        
        times = iter(sorted(self._queue.keys()))
        while True:
            if self._stopped:
                return
            # Get all the events that should be within the buffer
            event_times = []
            now = pgmidi.time()
            while len(event_times) == 0 or event_times[-1]+start_time < now + self.buffer_time:
                event_times.append(times.next())
            
            events = sum([[[bytes,ms_time+start_time] for bytes in self._queue[ms_time]] for ms_time in event_times], [])
            print len(events), now, (now+self.buffer_time)
            print event_times[-1]+start_time
            self.output.write(events)
            finished_time = pgmidi.time()
            print finished_time
            sleep_for = float(event_times[-1]+start_time-finished_time-self.buffer_advance)/1000
            if sleep_for > 0.0:
                sleep(sleep_for)
            print "Continuing"

class SequencerInitializationError(Exception):
    pass

