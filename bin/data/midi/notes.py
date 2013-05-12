#!/usr/bin/env ../../jazzshell
"""
Stats about the notes in a MIDI.

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
from subprocess import call
from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.midi import simplify, note_ons
from midi import read_midifile

def main():
    usage = "%prog [options] <in-file>"
    description = "Print out stats about the notes in a MIDI file"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-k', '--key-profile', dest="key_profile", action="store", type="int", help="output a graph of the key profile for the given key as a gnuplot script")
    options, arguments = parse_args_with_config(parser)
    
    if len(arguments) == 0:
        print "No input MIDI file given"
        sys.exit(1)
    filename = arguments[0]
    
    # Load the midi file
    midi = read_midifile(filename)
    print "Midi file type %d" % midi.format
    print "Resolution: %d" % midi.resolution
    print "%d notes" % len(note_ons(midi))
    # Get rid of drums
    midi = simplify(midi, remove_drums=True)
    notes = note_ons(midi)
    print "%d non-drum notes" % len(notes)
    # Analyse the note content
    pcs = dict([(i,0) for i in range(12)])
    for note in notes:
        pcs[note.pitch % 12] += 1
    
    note_names = dict([
        (0, "C"), (1, "C#"), (2, "D"), (3, "D#"), (4, "E"), (5, "F"), 
        (6, "F#"), (7, "G"), (8, "G#"), (9, "A"), (10, "A#"), (11, "B") ])
    # Print the notes
    for pc, count in reversed(sorted(pcs.items(), key=lambda x:x[1])):
        print "%s: %d" % (note_names[pc], count)
    
    if options.key_profile is not None:
        kp_output_file = "key_profile"
        pc_names = ["1", "#1/b2", "2", "#2/b3", "3", "4", "#4/b5", "5", 
            "#5/b6", "6", "#6/b7", "7"]
        # Output the pitch counts
        key = options.key_profile
        # Get the pc frequencies
        pc_freq = [float(pcs[(key+p)%12])/sum(pcs.values()) for p in range(12)]
        # Output them to a CSV
        data = "\n".join("%d\t%s\t%f" % (i,name,freq) for (name,freq,i) in zip(pc_names,pc_freq,range(12)))
        with open("%s.csv" % kp_output_file, 'w') as f:
            f.write(data)
        # Output the Gnuplot script
        gnuplot = """\
set style data lines
set nokey
set xrange [-1:13]
set terminal pdf monochrome
set output "key_profile.pdf"
set xlabel "Pitch class"
plot "key_profile.csv" using 1:3:xticlabel(2)
"""
        with open("%s.p" % kp_output_file, 'w') as f:
            f.write(gnuplot)
        # Run Gnuplot
        call(["gnuplot", "%s.p" % kp_output_file])
        print "Gnuplot plot output to %s.p and %s.pdf" % (kp_output_file,kp_output_file)

if __name__ == "__main__":
    main()
