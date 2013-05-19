#!/usr/bin/env ../../jazzshell
"""
Divides a midi file into chunks, with a given size and offset, and plays 
the chunks consecutively, with a gap between each.

Designed for testing a segmentation of a midi file for the Raphsto HMM model.

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
from jazzparser.misc.raphsto import MidiHandler
from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.midi import play_stream
from midi import read_midifile, NoteOnEvent
from jazzparser.data.input import command_line_input

def main():
    usage = "%prog [options] <midi-file>"
    description = "Divides a midi file into chunks, with a given size and "\
        "offset, and plays "\
        "the chunks consecutively, with a gap between each."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-g', '--gap', dest="gap", action="store", type="float", help="time to wait between playing each chunk in seconds (potentially float). It will take some time to load the chunk and the sequencer usually pauses before reporting it's done: this is not included in this value", default=0.0)
    parser.add_option('-p', '--print', dest="print_events", action="store_true", help="print out all events for each chunk")
    parser.add_option('--pno', '--print-note-ons', dest="print_note_ons", action="store_true", help="print only note-on events")
    parser.add_option('--force-res', dest="force_res", action="store", type="int", help="force the midi file's resolution to be the given value, rather than using that read from the file")
    parser.add_option('-s', '--start', dest="start", action="store", type="int", help="chunk number to start at", default=0)
    parser.add_option("--filetype", "--ft", dest="filetype", action="store", help="select the file type for the input file (--file). Use '--filetype help' for a list of available types. Default: segmidi", default='segmidi')
    parser.add_option("--file-options", "--fopt", dest="file_options", action="store", help="options for the input file (--file). Type '--fopt help', using '--ft <type>' to select file type, for a list of available options.")
    options, arguments = parse_args_with_config(parser)
    
    if len(arguments) == 0:
        print >>sys.stderr, "Missing filename"
        sys.exit(1)
    filename = arguments[0]
    
    # Load up the input midi file
    input_data = command_line_input(filename=filename, 
                                    filetype=options.filetype,
                                    options=options.file_options,
                                    allowed_types=['segmidi', 'autosegmidi'])
    print "Input type: %s" % options.filetype
    
    # Start at the requested chunk
    if options.start:
        input_data = input_data[options.start:]
        print "Start from chunk %d" % options.start
    print "Total chunks: %d" % len(input_data)
    print "Ctrl+C to exit"
    print
    
    try:
        for i,slc in enumerate(input_data):
            print "Playing chunk %d (%d events)" % (i,len(slc.trackpool))
            if options.print_events:
                print "\n".join("  %s" % ev for ev in sorted(slc.trackpool))
            elif options.print_note_ons:
                print "\n".join("  %s" % ev for ev in sorted(slc.trackpool) \
                                                    if type(ev) is NoteOnEvent)
            
            play_stream(slc, block=True)
            if options.gap > 0.0:
                print "  Waiting %s seconds..." % options.gap
                time.sleep(options.gap)
    except KeyboardInterrupt:
        print "Exiting"

if __name__ == "__main__":
    main()
