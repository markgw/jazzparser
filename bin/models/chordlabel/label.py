#!/usr/bin/env ../../jazzshell
"""
Applies a trained chord labeling model to MIDI data and prints out the results.

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

import sys, math, os
from optparse import OptionParser
from midi import write_midifile

from jazzparser.utils.options import ModuleOption, options_help_text
from jazzparser.utils.config import parse_args_with_config
from jazzparser.data.input import command_line_input, is_bulk_type

from jazzparser.misc.chordlabel import HPChordLabeler
from jazzparser.misc.chordlabel.realize import ChordSequenceRealizer

def main():
    usage = "%prog [options] <model_name> <in-file>"
    description = "Loads a chord labeling model and uses it to assign chord "\
        "labels to the given MIDI file."
    parser = OptionParser(usage=usage, description=description)
    # File input options
    parser.add_option("--filetype", "--ft", dest="filetype", action="store", help="select the file type for the input file. Same filetypes as jazzparser", default='segmidi')
    parser.add_option("--file-options", "--fopt", dest="file_options", action="store", help="options for the input file. Type '--fopt help', using '--ft <type>' to select file type, for a list of available options.")
    # Labeling options
    parser.add_option("--labeler-options", "--lopt", dest="labeler_options", action="append", help="options for the labeler. Type '--lopt help' for a list of available options.")
    parser.add_option("--no-key", "--nk", dest="no_key", action="store_true", help="merge together labels with the same key (same as --lopt nokey)")
    # Output options
    parser.add_option("--single", "-1", dest="single", action="store_true", help="show only one chord per time segment (same as --lopt n=1, but formats the output in a simpler way)")
    parser.add_option('-r', '--realize', dest="realize", action="store", help="realize the chord sequence as a midi file, overlaid on the input")
    parser.add_option('--chords-only', dest="chords_only", action="store_true", help="only realize the chords: don't overlay on the input midi (only works with -r)")
    options, arguments = parse_args_with_config(parser)
    
    if options.labeler_options is not None and "help" in options.labeler_options:
        print options_help_text(HPChordLabeler.LABELING_OPTIONS, intro="Options for HP chord labeler")
        sys.exit(0)
        
    if len(arguments) < 2:
        print >>sys.stderr, "You must specify a model name and an input "\
            "(MIDI) data file as arguments"
        sys.exit(1)
    filename = os.path.abspath(arguments[1])
    model_name = arguments[0]
    
    # Process the labeler options
    lopt_dict = ModuleOption.process_option_string(options.labeler_options)
    if options.single:
        # No point in getting more than one label, since we only display one
        lopt_dict['n'] = 1
    if options.no_key:
        # Just set the nokey option
        lopt_dict['nokey'] = True
    
    # Check they're valid before doing anything else
    HPChordLabeler.process_labeling_options(lopt_dict)
    
    input_data = command_line_input(filename, 
                                    filetype=options.filetype, 
                                    options=options.file_options,
                                    allowed_types=['segmidi','bulk-segmidi'])
    bulk = not is_bulk_type(type(input_data))
    if bulk:
        input_data = [input_data]
        
    for i,data in enumerate(input_data):
        input_stream = data.stream
        print "Read midi data in %d segments" % len(data)
        
        # Load the model
        model = HPChordLabeler.load_model(model_name)
        # Perform labeling
        labels = model.label(data, options=lopt_dict)
        # Try labeling as it will be passed to the tagger
        labs = model.label_lattice(data, options=lopt_dict)
        
        if options.single:
            # Special output for single label output
            print ", ".join(["%s" % timelabs[0][0] for timelabs in labels])
        else:
            # Print out the labels for each timestep
            for time,timelabs in enumerate(labels):
                print "%d: %s" % (time, 
                    ", ".join(["%s (%.2e)" % (label,prob) for (label,prob) in timelabs]))
        
        if options.realize is not None:
            # Get the single best chord label for each time
            best_labels = [timelabs[0][0] for timelabs in labels]
            # Realize as a midi file
            print "Realizing output chord sequence"
            real = ChordSequenceRealizer(best_labels, 
                                         model.chord_vocab, 
                                         resolution=input_stream.resolution, 
                                         chord_length=data.time_unit,
                                         text_events=True)
            if options.chords_only:
                # Don't overlay
                stream = real.generate(offset=data.tick_offset)
            else:
                stream = real.generate(overlay=input_stream, offset=data.tick_offset)
                
            if bulk:
                filename = "%s-%d" % (options.realize, i)
            else:
                filename = options.realize
            write_midifile(stream, filename)
    
if __name__ == "__main__":
    main()
