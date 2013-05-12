#!/usr/bin/env ../../jazzshell
"""
Divides a midi file into chunks, with a given size and offset, and plays 
the chunks consecutively, with a gap between each.
Like play_chunks, but takes as input a bulk segmented midi data input 
and iterates over the inputs, taking the parameters from the CSV file.

Designed for testing a segmentation of a midi file for input to models.

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

import sys, time
from optparse import OptionParser
from jazzparser.utils.config import parse_args_with_config
from jazzparser.data.input import SegmentedMidiBulkInput, command_line_input
from jazzparser.utils.midi import play_stream
from midi import read_midifile, NoteOnEvent

def main():
    usage = "%prog [options] <input>"
    description = "Divides midi files into chunks, with size and offset, "\
        "given in the input file, and plays "\
        "the chunks consecutively. Input is a segmented bulk midi input file."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-g', '--gap', dest="gap", action="store", type="float", help="time to wait between playing each chunk in seconds (potentially float). It will take some time to load the chunk and the sequencer usually pauses before reporting it's done: this is not included in this value", default=0.0)
    parser.add_option('-p', '--print', dest="print_events", action="store_true", help="print out all events for each chunk")
    parser.add_option('--pno', '--print-note-ons', dest="print_note_ons", action="store_true", help="print only note-on events")
    parser.add_option('--fopt', dest="file_options", action="store", help="options for file loading. Use '--fopt help' to see available options")
    options, arguments = parse_args_with_config(parser)
    
    filename = arguments[0]
    # Try getting a file from the command-line options
    input_data = command_line_input(filename=filename, 
                                    filetype='bulk-segmidi',
                                    options=options.file_options)
    
    # Play each input in turn
    input_getter = iter(input_data)
    segmidi = input_getter.next()
    
    while True:
        print "###############################"
        print "Playing '%s'" % segmidi.name
        print "%s-beat chunks with a %d-tick offset\n" % \
                                    (segmidi.time_unit, segmidi.tick_offset)
        slices = list(segmidi)
        
        try:
            for i,strm in enumerate(slices):
                print "Playing chunk %d: %d events" % (i, len(strm.trackpool))
                if options.print_events:
                    print "\n".join("  %s" % ev for ev in sorted(strm.trackpool))
                elif options.print_note_ons:
                    print "\n".join("  %s" % ev for ev in sorted(strm.trackpool) \
                                                    if type(ev) is NoteOnEvent)
                # Play this midi chunk
                play_stream(strm, block=True)
                # Leave a gap before continuing
                if options.gap > 0.0:
                    time.sleep(options.gap)
        except KeyboardInterrupt:
            pass
            
        print "Continue to next song (<enter>); exit (x); play again (p)"
        command = raw_input(">> ").lower()
        if command == "x":
            sys.exit(0)
        elif command == "p":
            # Play again
            continue
        elif command == "":
            # Move to next
            segmidi = input_getter.next()
            continue
        else:
            print "Unknown command: %s" % command
            print "Playing again..."
            continue
    sys.exit(0)

if __name__ == "__main__":
    main()
