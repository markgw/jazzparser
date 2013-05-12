#!/usr/bin/env ../jazzshell
"""
Loads a ParseResults file and performs various operations on the 
contents.

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

from jazzparser.data.parsing import ParseResults
from jazzparser.utils.tonalspace import coordinates_to_roman_names
from jazzparser.harmonical.tones import path_to_tones
from jazzparser.harmonical.output import play_audio
from jazzparser.harmonical.files import save_wave_data
from jazzparser.formalisms.loader import get_default_formalism

def main():
    usage = "%prog [options] <results-file> [<result-number>=0]"
    parser = OptionParser(usage=usage)
    parser.add_option("-q", "--quiet", dest="quiet", action="store_true", help="only output the requested information, no meta-info.")
    parser.add_option("-p", "--print", dest="printout", action="store_true", help="output the result to stdout.")
    parser.add_option("--path", dest="path", action="store_true", help="display the fully-specified tonal space path.")
    parser.add_option("--play", dest="play", action="store_true", help="use the harmonical to play the root sequence of the result's semantics.")
    parser.add_option("--audio", dest="audio", action="store", help="use the harmonical to render the root sequence, as with --play, and store the result to a wave file.")
    options, arguments = parser.parse_args()
    
    # Just get the default formalism
    formalism = get_default_formalism()
    
    def _print(string=""):
        if not options.quiet:
            print >>sys.stderr, string
        
    if len(arguments) == 0:
        print >>sys.stderr, "Specify a file to read the results from"
        sys.exit(1)
    results = ParseResults.from_file(arguments[0])
    
    if len(arguments) > 1:
        res_num = int(arguments[1])
    else:
        res_num = 0
    prob,result = results.sorted_results[res_num]
    
    if options.printout:
        _print("Result:")
        # Just display the resulting category
        print result
        _print()
        
    if options.path:
        _print("Tonal space path:")
        # Compute the tonal path (coordinates) from the result
        path = formalism.semantics_to_coordinates(result.semantics)
        points,timings = zip(*path)
        print ", ".join(coordinates_to_roman_names(points))
        _print()
        
    if options.play or options.audio is not None:
        _print("Building pitch structure from result...")
        # Convert the semantics into a list of TS points
        path = formalism.semantics_to_coordinates(result.semantics)
        # Decide on chord types
        # For now, since we don't know the original chords, use dom7 
        #  for dom chords, maj for subdoms, and M7 for tonics
        fun_chords = {
            'T' : 'M7',
            'D' : '7',
            'S' : '',
        }
        functions = formalism.semantics_to_functions(result.semantics)
        chord_types = [(fun_chords[f],t) for (f,t) in functions]
        
        tones = path_to_tones(path, chord_types=chord_types, double_root=True)
        
        _print("Rendering audio samples...")
        samples = tones.render()
        if options.audio is not None:
            filename = os.path.abspath(options.audio)
            _print("Writing wave data to %s" % filename)
            save_wave_data(samples, filename)
        if options.play:
            _print("Playing...")
            play_audio(samples, wait_for_end=True)
        _print()

if __name__ == "__main__":
    main()
