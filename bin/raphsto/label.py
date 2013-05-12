#!/usr/bin/env ../jazzshell
"""
Use a trained Raphsto model to output harmonic labels for a midi file.

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

from jazzparser.utils.options import ModuleOption, options_help_text
from jazzparser.utils.config import parse_args_with_config
from jazzparser.utils.loggers import create_plain_stderr_logger
from jazzparser.misc.raphsto import format_state_as_chord, format_state, \
                MODEL_TYPES, format_state_as_raphsto
from jazzparser.misc.raphsto.midi import MidiHandler, ChordSequenceRealizer

def main():
    usage = "%prog [options] <model-name> <midi-file>"
    description = "Assigns harmonic labels to a midi file using a trained "\
        "Raphsto model"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-t', '--time-unit', dest="time_unit", action="store", type="float", help="number of beats to take as the basic unit (chunk size) for labelling", default=2)
    parser.add_option('-o', '--tick-offset', dest="tick_offset", action="store", type="int", help="time in midi ticks at which to start labelling", default=0)
    parser.add_option('-d', '--remove-drums', dest="remove_drums", action="store_true", help="ignores any channel 10 events in the midi file", default=False)
    parser.add_option('-c', '--chords', dest="chords", action="store_true", help="displays just chord roots instead of full analysis (default: both)")
    parser.add_option('-a', '--analysis', dest="analysis", action="store_true", help="displays a full analysis without reducing to chord roots (default: both)")
    parser.add_option('-r', '--realize', dest="realize", action="store", help="realize the chord sequence as a midi file (very basic and horrible realization)")
    parser.add_option('--rands', '--raphsto', dest="raphsto", action="store_true", help="displays analysis in the style of the annotations added to MIDI files by the original implementation")
    parser.add_option('--lyrics', dest="lyrics", action="store_true", help="include the chord labels as lyric events in the midi file", default=False)
    parser.add_option('-m', '--model-type', dest="model_type", action="store", help="select a model type: one of %s (default: standard)" % ", ".join(mt for mt in MODEL_TYPES.keys()), default="standard")
    options, arguments = parse_args_with_config(parser)
    
    if len(arguments) < 2:
        print >>sys.stderr, "You must specify a model name and an input midi file as arguments"
        sys.exit(1)
    filename = os.path.abspath(arguments[1])
    model_name = arguments[0]
    
    if options.model_type not in MODEL_TYPES:
        print >>sys.stderr, "Model type must be one of: %s" % ", ".join(mt for mt in MODEL_TYPES)
        sys.exit(1)
    model_cls = MODEL_TYPES[options.model_type]
    
    # Load the model
    model = model_cls.load_model(model_name)
    
    mid = read_midifile(filename)
    bar = mid.resolution * options.time_unit
    handler = MidiHandler(mid, time_unit=options.time_unit, tick_offset=options.tick_offset, remove_drums=options.remove_drums)
    # Decode using the model to get a list of states
    state_changes = model.label(handler)
    states,times = zip(*state_changes)
    
    if options.chords:
        print "\n".join("%s (bar %d)" % (format_state_as_chord(st),time/bar) \
                                            for st,time in state_changes)
    elif options.analysis:
        print "\n".join("%s (bar %d)" % (format_state(st),time/bar) \
                                            for st,time in state_changes)
    elif options.raphsto:
        print "\n".join(format_state_as_raphsto(st, (time/bar)) \
                                            for st,time in state_changes)
    else:
        print "\n".join("%s%s(bar %d)" % \
                                    (format_state(st).ljust(15), 
                                     format_state_as_chord(st).ljust(7),
                                     time/bar) for st,time in state_changes)
    
    if options.realize is not None:
        # Realize as a midi file
        real = ChordSequenceRealizer(states, 
                                     resolution=mid.resolution, 
                                     times=times, 
                                     chord_length=options.time_unit,
                                     text_events=options.lyrics)
        stream = real.generate(overlay=mid, offset=options.tick_offset)
        write_midifile(stream, options.realize)
    
if __name__ == "__main__":
    main()
