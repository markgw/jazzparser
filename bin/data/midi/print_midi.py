#!/usr/bin/env ../../jazzshell
"""
Dumps a description of the data in a midi file to stdout.

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

import sys
from optparse import OptionParser
from jazzparser.utils.config import parse_args_with_config
from midi import read_midifile
from jazzparser.utils.midi import note_ons_list

def main():
    usage = "%prog [options] <in-file>"
    description = "Dump a description of all the events in a midi file "\
        "to stdout."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("--only-on", "-o", dest="only_on", action="store_true", 
                        help="Only include note-on events")
    parser.add_option("--combine", "-c", dest="combine", action="store_true", 
                        help="Combine all tracks into one")
    options, arguments = parse_args_with_config(parser)
    
    if len(arguments) == 0:
        print "No input MIDI file given"
        sys.exit(1)
    filename = arguments[0]
    
    # Load the midi file
    midi = read_midifile(filename)
    print "Midi file type %d" % midi.format
    print "Resolution: %d" % midi.resolution
    if options.combine:
        tracks = [("All tracks", midi.trackpool)]
    else:
        tracks = [("Track %d" % track, midi[track]) for track in range(len(midi))]
        
    for track,events in tracks:
        print "\n%s" % track
        events = sorted(events)
        if options.only_on:
            events = note_ons_list(events)
        for event in events:
            print "%s" % (event)

if __name__ == "__main__":
    main()
