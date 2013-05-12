#!/usr/bin/env ../../jazzshell
"""
Divides a midi file into chunks, with a given size and offset, and prints 
out the notes of each chunk in a readable(ish) fashion.

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
from itertools import groupby

from jazzparser.misc.raphsto import MidiHandler
from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.midi import play_stream
from midi import read_midifile, NoteOnEvent, constants

def main():
    usage = "%prog [options] <midi-file>"
    description = "Divides a midi file into chunks, with a given size and "\
        "offset, and print the chunks consecutively."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-t', '--time-unit', dest="time_unit", action="store", type="float", help="size of chunks in crotchet beats (according to the midi file's resolution)", default=4)
    parser.add_option('-o', '--tick-offset', dest="tick_offset", action="store", type="int", help="offset of the first chunk in midi ticks", default=0)
    parser.add_option('--force-res', dest="force_res", action="store", type="int", help="force the midi file's resolution to be the given value, rather than using that read from the file")
    parser.add_option('-i', "--tick-times", dest="tick_times", action="store_true", help="show times as tick values, rather than proportions of the chunk")
    options, arguments = parse_args_with_config(parser)
    
    filename = arguments[0]
    
    # Load up the input midi file
    infile = read_midifile(filename, force_resolution=options.force_res)
    handler = MidiHandler(infile,
                          time_unit=options.time_unit,
                          tick_offset=options.tick_offset)
    slices = handler.get_slices()
    
    print "Printing %d-beat chunks with a %d-tick offset" % (options.time_unit, options.tick_offset)
    print "Total chunks: %d" % len(slices)
    print
    
    chunk_length = options.time_unit * infile.resolution
    
    for i,slc in enumerate(slices):
        strm = slc.to_event_stream()
        # Print the header for this chunk
        print "Chunk %d: %d-%d (%d events)" % \
                (i, slc.start, slc.end,len(strm.trackpool))
        print "".join(str(i).ljust(2) for i in range(11)), \
                "Time   ", "Vel", "Ch", "Tr"
        
        # Only show note-on events
        noteons = [ev for ev in sorted(strm.trackpool) \
                    if type(ev) == NoteOnEvent and ev.velocity > 0]
        # Sorted by time: within same tick, sort by pitch
        for k,grp in groupby(noteons):
            for ev in sorted(list(grp), key=lambda e:e.pitch):
                # Display all the information for this note
                octave = ev.pitch / 12
                name = constants.NOTE_NAMES[ev.pitch % 12].ljust(2)
                indent = "  " * octave
                fill = "  " * (10-octave)
                if options.tick_times:
                    time = str(ev.tick+slc.start).ljust(7)
                else:
                    time = ("%.1f%%" % (100.0 * ev.tick / chunk_length)).ljust(7)
                channel = str(ev.channel).ljust(2)
                track = str(ev.track).ljust(2)
                velocity = str(ev.velocity).ljust(3)
                
                print "%s%s%s %s %s %s %s" % \
                        (indent, name, fill, time, velocity, channel, track)
        print

if __name__ == "__main__":
    main()
