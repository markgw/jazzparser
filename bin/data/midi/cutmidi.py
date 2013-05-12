#!/usr/bin/env ../../jazzshell
"""
Load a midi and trim it to the required length.

"""
import sys, os
from optparse import OptionParser
from midi import read_midifile, write_midifile
from midi.slice import EventStreamSlice
from jazzparser.utils.midi import play_stream
from jazzparser.utils.base import ExecutionTimer

def main():
    usage = "%prog [options] <midi-input>"
    description = "Trims a MIDI file to the required start and end points. "\
        "By default, plays the trimmed MIDI (for testing) and can also write "\
        "it out to a file."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-s", "--start", dest="start", action="store", help="start point, in ticks as 'x', or in seconds as 'xs'")
    parser.add_option("-e", "--end", dest="end", action="store", help="end point (formatted as -s)")
    parser.add_option("-o", "--output", dest="output", action="store", help="MIDI file to output to. If given, output is stored instead of being played")
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify a MIDI file"
        sys.exit(1)
    mid = read_midifile(arguments[0])
    
    def _time_to_ticks(time, before=False):
        # Find the tick time of the first event after the given time
        #  or the last event before it
        mstime = int(time * 1000)
        if time is not None:
            previous = min(mid.trackpool)
            for ev in sorted(mid.trackpool):
                # Look for the first event after the time
                if ev.msdelay >= mstime:
                    if before:
                        # Return the previous event's tick
                        return previous.tick
                    else:
                        # Return this event's tick
                        return ev.tick
                previous = ev
        return max(mid.trackpool).tick
    
    def _ticks_to_ticks(ticks, before=False):
        # Find the tick time of the first event after the given time
        #  or the last event before it
        if ticks is not None:
            previous = min(mid.trackpool)
            for ev in sorted(mid.trackpool):
                # Look for the first event after the time
                if ev.tick >= ticks:
                    if before:
                        # Return the previous event's tick
                        return previous.tick
                    else:
                        # Return this event's tick
                        return ev.tick
                previous = ev
        return max(mid.trackpool).tick
    
    def _get_time(ticks, before=False):
        # Find the event time of the first event after the given tick time 
        #  or the last event before it
        previous = min(mid.trackpool)
        if ticks is not None:
            for ev in sorted(mid.trackpool):
                # Look for the first event after the time in ticks
                if ev.tick >= ticks:
                    if before:
                        # Return the previous event's time
                        return previous.msdelay
                    else:
                        # Return this event's time
                        return ev.msdelay
                previous = ev
        return max(mid.trackpool).msdelay
    
    def _parse_time(val, before=False):
        if val.endswith("s"):
            # Value in seconds
            # Convert to ticks
            return _time_to_ticks(float(val[:-1]), before=before)
        else:
            return int(val)
    
    # Work out start and end points
    if options.start is not None:
        start = _parse_time(options.start, before=False)
    else:
        start = 0
        
    if options.end is not None:
        end = _parse_time(options.end, before=True)
    else:
        end = None
    
    if end is not None and start > end:
        print "Start time of %d ticks > end time of %d ticks" % (start, end)
        sys.exit(1)
    
    # Cut the stream to the desired start and end
    slc = EventStreamSlice(mid, start, end)
    trimmed_mid = slc.to_event_stream(repeat_playing=False)
        
    # Print out some info
    print "Start tick: %s" % start
    print "End tick: %s" % end
    print
    print "First event tick: %s" % _ticks_to_ticks(start)
    print "Last event tick: %s" % _ticks_to_ticks(end, before=True)
    print
    print "Start time: %ss" % (float(_get_time(start)) / 1000.0)
    print "Last event time: %ss" % (float(_get_time(end, before=True)) / 1000.0)
    print
    print "%d events" % len(trimmed_mid.trackpool)
    
    # Record playing time
    timer = ExecutionTimer()
    
    if options.output is None:
        # Play the output by default
        try:
            play_stream(trimmed_mid, block=True)
        except KeyboardInterrupt:
            print "\nPlayed for %.2f seconds" % timer.get_time()
    else:
        # Output to a file
        outfile = os.path.abspath(options.output)
        write_midifile(trimmed_mid, outfile)
        print "Output written to %s" % outfile

if __name__ == "__main__":
    main()
