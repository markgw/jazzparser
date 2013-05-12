#!/usr/bin/env ../jazzshell
"""
Play music from the tonal space using the harmonical.

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
from jazzparser.harmonical.input import HarmonicalInputFile
from jazzparser.harmonical.files import save_wave_data
from jazzparser.harmonical.output import play_audio
from jazzparser.utils.midi import play_stream
from midi import write_midifile

def main():
    usage = "%prog [options] <in-file>"
    description = "Play music using the Harmonical. This allows you to "\
        "play music specified precisely in the tonal space. By default, "\
        "plays back the input, but can also output to a file."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-o', '--output', dest="outfile", action="store", help="output the result to a wave file instead of playing back.")
    parser.add_option('-m', '--midi', dest="midi", action="store_true", help="generate midi data, not audio. Depends on the input format supporting midi file generation.")
    options, arguments = parse_args_with_config(parser)
    
    filename = arguments[0]
    
    # Load up the input file
    infile = HarmonicalInputFile.from_file(filename)
    if options.midi:
        midi = infile.render_midi()
        
        if options.outfile is not None:
            # Output a midi file
            write_midifile(midi, options.outfile)
            print >>sys.stderr, "Saved midi data to %s" % options.outfile
        else:
            print >>sys.stderr, "Playing..."
            play_stream(midi, block=True)
    else:
        print >>sys.stderr, "Generating audio..."
        audio = infile.render()
        
        if options.outfile is not None:
            # Output to a file instead of playing
            save_wave_data(audio, options.outfile)
            print >>sys.stderr, "Saved data to %s" % options.outfile
        else:
            print >>sys.stderr, "Playing..."
            play_audio(audio, wait_for_end=True)

if __name__ == "__main__":
    main()
