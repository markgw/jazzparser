#!/usr/bin/env ../../jazzshell
"""
Script for cleaning up midi files to get them in a simpler form for 
use as input to algorithms, etc.

Essentially just filters out a few things like drum tracks, lyrics, 
control changes, etc, that make the music sound better, but won't be 
used by our algorithms and just confuse things by being there.

One specific use of this is to remove the chord superimpositions from 
Raphael and Stoddard's data. Use -r 1 to get rid of them. Use -x to 
get rid of the text events as well.

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

import sys, os
from optparse import OptionParser
from midi import read_midifile, write_midifile

from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.midi import simplify, remove_channels

def main():
    usage = "%prog [options] <input-midi> <output-filename>"
    description = "Cleans up a midi file by getting rid of a load of "\
            "stuff that makes the music sound good, but isn't needed "\
            "by our algorithms. See options for details."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-d', '--remove-drums', dest="remove_drums", action="store_true", help="filter out drum tracks", default=False)
    parser.add_option('-p', '--pc', '--remove-program-change', dest="remove_pc", action="store_true", help="filter out all program change (instrument) events", default=False)
    parser.add_option('-x', '--remove-text', '--txt', dest="remove_text", action="store_true", help="filter out all text events of any type", default=False)
    parser.add_option('-o', '--one-track', dest="one_track", action="store_true", help="reduce everything down to one track", default=False)
    parser.add_option('-t', '--remove-tempo', dest="remove_tempo", action="store_true", help="remove all tempo events", default=False)
    parser.add_option('-c', '--remove-control', dest="remove_control", action="store_true", help="remove all control change events", default=False)
    parser.add_option('--ch', '--one-channel', dest="one_channel", action="store_true", help="use only one channel: every event occurs on channel 0", default=False)
    parser.add_option('--mc', '--remove-misc-control', dest="remove_misc_control", action="store_true", help="filter out a whole load of device control events: aftertouch, channel aftertouch, pitch wheel, sysex, port", default=False)
    parser.add_option('--rno', '--real-note-offs', dest="real_note_offs", action="store_true", help="replace 0-velocity note-ons with actual note-offs. Some midi files use one, some the other", default=False)
    parser.add_option('--remove-duplicates', dest="remove_duplicates", action="store_true", help="tidy up at the end to remove any duplicate notes", default=False)
    parser.add_option('-i', '--invert', dest="invert", action="store_true", help="inverts all options. I.e. applies all filters except those selected by the above options", default=False)
    parser.add_option('-r', '--remove-channels', dest="remove_channels", action="append", type="int", help="filter out all events of the numbered channel. Use multiple options to filter multiple channels at once")
    parser.add_option('--resolution', '--res', dest="resolution", action="store", type="int", help="change the resolution of the midi data from that read in from the file to that given")
    options, arguments = parse_args_with_config(parser)
    
    if len(arguments) < 2:
        print >>sys.stderr, "You must specify an input and output filename"
        sys.exit(1)
    in_filename = os.path.abspath(arguments[0])
    out_filename = os.path.abspath(arguments[1])
    
    # Read in the midi file
    mid = read_midifile(in_filename, force_resolution=options.resolution)
    # Build a dictionary of kwargs to select what operations to apply
    filters = {
        'remove_drums' : options.remove_drums ^ options.invert,
        'remove_pc' : options.remove_pc ^ options.invert,
        'remove_all_text' : options.remove_text ^ options.invert,
        'one_track' : options.one_track ^ options.invert,
        'remove_tempo' : options.remove_tempo ^ options.invert,
        'remove_control' : options.remove_control ^ options.invert,
        'one_channel' : options.one_channel ^ options.invert,
        'remove_misc_control' : options.remove_misc_control ^ options.invert,
        'real_note_offs' : options.real_note_offs ^ options.invert,
    }
        
    print "Filters to be applied:"
    if options.remove_channels is not None:
        print "  removing channels: %s" % ", ".join(str(ch) for ch in options.remove_channels)
    if options.resolution is not None:
        print "  changing resolution to %d" % options.resolution
    print "\n".join("  %s" % name for (name,val) in filters.items() if val)
    filters['remove_duplicates'] = options.remove_duplicates
    
    print "Filtering..."
    # Apply channel filters first
    if options.remove_channels is not None:
        remove_channels(mid, options.remove_channels)
    filtered = simplify(mid, **filters)
    print "Midi output to",out_filename
    write_midifile(filtered, out_filename)
    
if __name__ == "__main__":
    main()
