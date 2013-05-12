#!/usr/bin/env ../../jazzshell
"""
Interactive MIDI cutter

"""
import sys, os, csv
from optparse import OptionParser
from midi import read_midifile, write_midifile
from midi.slice import EventStreamSlice
from jazzparser.utils.midi import play_stream
from jazzparser.utils.base import ExecutionTimer, check_directory
from jazzparser.data.input import SegmentedMidiBulkInput

############# Utility function we'll need below #########
def _time_to_ticks(mid, time, before=False):
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

def _ticks_to_ticks(mid, ticks, before=False):
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

def _get_time(mid, ticks, before=False):
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

def _parse_time(mid, val, before=False):
    if val.endswith("s"):
        # Value in seconds
        # Convert to ticks
        return _time_to_ticks(mid, float(val[:-1]), before=before)
    else:
        return int(val)
        
def _play(mid, start, end):
    """ Play the selection """
    if start is None:
        start = 0
    # Trim the midi
    trimmed = EventStreamSlice(mid, start, end).to_event_stream(repeat_playing=False)
    # Show info about the clip
    print "Start tick: %s" % start
    print "End tick: %s" % end
    print "First event tick: %s" % _ticks_to_ticks(mid, start)
    print "Last event tick: %s" % _ticks_to_ticks(mid, end, before=True)
    start_time = float(_get_time(mid, start)) / 1000.0
    print "Start time: %ss" % start_time
    print "Last event time: %ss" % (float(_get_time(mid, end, before=True)) / 1000.0)
    print
    print "Playing MIDI. Hit ctrl+C to stop"
    # Record playing time
    timer = ExecutionTimer()
    try:
        play_stream(trimmed, block=True)
    except KeyboardInterrupt:
        length = timer.get_time()
        print "\nPlayed for %.2f seconds (stopped ~%.2fs)" % (length, start_time+length)


def main():
    usage = "%prog [options] <midi-input1> [<midi-input2> ...]"
    description = "Interactive routine for cutting MIDI files. May take "\
        "multiple MIDI files as input"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-o", "--output", dest="output_dir", action="store", help="directory to send MIDI output to. If not given, they will be sent to a subdirectory 'cut' of that containing the first input")
    parser.add_option("--fragment", dest="fragment", action="store", type="float", help="length in seconds of fragment to play when asked to play a beginning or ending. Default: 3secs", default=3.0)
    parser.add_option("--overwrite", dest="overwrite", action="store_true", help="by default, we skip processing any files where there's a file with the same name in the output directory. This forces us to overwrite them")
    parser.add_option("--ignore", dest="ignore", action="store", help="file containing a list of filenames (not paths), one per line: any input files matching these names will be ignored and inputs marked as 'ignore' will be added to the list")
    parser.add_option("--segfile", dest="segfile", action="store", help="output a list of the MIDI files that get written by this script (just the base filename) in the format of segmidi input lists. The list will contain a basic set of default segmentation parameters. Use play_bulk_chunks to validate these. If the file exists, it will be appended")
    options, arguments = parser.parse_args()
    
    fragment = options.fragment
        
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify at least one MIDI file"
        sys.exit(1)
    # Read in all the MIDI inputs
    filenames = arguments
    print "Processing %d inputs" % len(filenames)
    
    if options.ignore:
        if os.path.exists(options.ignore):
            # Existing list
            # Open the file to read in the current list and add to it
            ignore_file = open(options.ignore, 'r+a')
            ignore_list = [filename.strip("\n") for filename in ignore_file.readlines()]
            print "Loaded ignore list from %s" % options.ignore
        else:
            # No existing list
            # Open the file so we can write new entries
            ignore_file = open(options.ignore, 'w')
            ignore_list = []
            print "Created new ignore list in %s" % options.ignore
    else:
        ignore_file = None
        ignore_list = []
    
    if options.segfile:
        # Open the file for writing segmidi parameters to
        segfile = open(options.segfile, 'a')
        segcsv = csv.writer(segfile)
    else:
        segfile = None
    
    try:
        # Set up the output directory
        if options.output_dir:
            output_dir = options.output_dir
        else:
            # Get the directory of the first input file
            output_dir = os.path.join(os.path.dirname(filenames[0]), "cut")
        check_directory(output_dir, is_dir=True)
        print "Outputing MIDI files to %s" % output_dir
        print
        
        for filename in filenames:
            basename = os.path.basename(filename)
            # Ignore any files in the ignore list
            if basename in ignore_list:
                print "Skipping input %s, as it's in the ignore list" % basename
                continue
            
            out_filename = os.path.join(output_dir, os.path.basename(filename))
            # Check whether the output file already exists
            if os.path.exists(out_filename):
                if options.overwrite:
                    # Just warn
                    print "WARNING: writing out this input will overwrite an existing file"
                else:
                    # Don't continue with this input
                    print "Skipping input %s, since output file already exists" % filename
                    continue
            
            start = 0
            end = None
            
            print "\n####################################"
            print "Processing input: %s" % filename
            # Read in the midi file
            try:
                mid = read_midifile(filename)
            except Exception, err:
                print "Error reading in midi file %s: %s" % (filename, err)
                continue
            print "Output will be written to: %s" % out_filename
            # Start by playing the whole thing
            _play(mid, start, end)
            
            try:
                while True:
                    # Print the header information
                    print "\n>>>>>>>>>>>>>>>>>>>>>>"
                    if end is None:
                        end_str = "open"
                    else:
                        end_str = "%d ticks" % end
                    print "Start: %d ticks. End: %s" % (start, end_str)
                    print ">>>>>>>>>>>>>>>>>>>>>>"
                    print "Set start time (s); set end time (e)"
                    print "Play all (p); play beginning ([); play end (], optional length)"
                    print "Write out and proceed (w); add to ignore list (i); skip to next (n); exit (x)"
                    
                    # Get a command from the user
                    try:
                        command = raw_input(">> ")
                    except KeyboardInterrupt:
                        # I quite often send an interrupt by accident, meaning 
                        #  to stop the playback, but just after it's stopped 
                        #  itself
                        print "Ignored keyboard interrupt"
                        continue
                    
                    command = command.strip()
                    if command.lower() == "p":
                        # Play within the selection again
                        _play(mid, start, end)
                    elif command.lower() == "n":
                        break
                    elif command.lower() == "i":
                        # Add the filename to the ignore list
                        if ignore_file:
                            ignore_file.write("%s\n" % os.path.basename(filename))
                        else:
                            print "No ignore file loaded: could not add this file to the list"
                        break
                    elif command.lower() == "x":
                        sys.exit(0)
                    elif command.lower().startswith("s"):
                        time = command[1:].strip()
                        if len(time) == 0:
                            print "Specify a start tick (T) or time (Ts)"
                            continue
                        start = _parse_time(mid, time)
                    elif command.lower().startswith("e"):
                        time = command[1:].strip()
                        if len(time) == 0:
                            print "Specify an end tick (T) or time (Ts)"
                            continue
                        end = _parse_time(mid, time, before=True)
                    elif command == "[":
                        # Play the opening few seconds
                        start_secs = _get_time(mid, start) / 1000.0
                        frag_end = _time_to_ticks(mid, fragment + start_secs)
                        _play(mid, start, frag_end)
                    elif command.startswith("]"):
                        length = command[1:].strip()
                        if len(length):
                            frag_length = float(length)
                        else:
                            frag_length = fragment
                        # Play the last few seconds
                        end_secs = _get_time(mid, end) / 1000.0
                        frag_start = _time_to_ticks(mid, max(0.0, end_secs-frag_length), before=True)
                        _play(mid, frag_start, end)
                    elif command == "w":
                        # Write the file out
                        if start is None:
                            start = 0
                        # Trim the midi
                        trimmed = EventStreamSlice(mid, start, end).to_event_stream(repeat_playing=False)
                        # Write it out
                        write_midifile(trimmed, out_filename)
                        if segfile is not None:
                            # Also output a row to the segmidi index
                            SegmentedMidiBulkInput.writeln(segcsv, basename)
                        print "Output written to %s" % out_filename
                        # Continue to the next input
                        break
                    else:
                        print "Unknown command: %s" % command
                        continue
            except EOFError:
                # User hit ctrl+D: continue to next input
                print "Continuing to next input..."
                continue
        else:
            print "No more MIDI inputs"
            sys.exit(0)
    finally:
        if ignore_file:
            ignore_file.close()
        if segfile is not None:
            segfile.close()

if __name__ == "__main__":
    main()
