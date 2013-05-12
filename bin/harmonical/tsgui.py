#!/usr/bin/env ../jazzshell
"""
Load the tonal space gui.

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
from midi.sequencer_pygame import get_midi_devices
from jazzparser.harmonical.tsgui import create_window, TonalSpaceWindow
from jazzparser.harmonical.input import HarmonicalInputFile

import gtk

def main():
    usage = "%prog [options]"
    description = "Loads the interactive tonal space gui."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-d', '--device', dest="device", action="store", type="int", help="select midi device to output to (run devices.py for a list)", default=0)
    parser.add_option('-i', '--instrument', dest="instrument", action="store", help="midi instrument number (0-127). Default: 16 (organ). Use 'N' not to set any instrument", default="16")
    parser.add_option('-f', '--font-size', dest="font_size", action="store", type="float", help="set the font size of the text in the labels")
    parser.add_option('--dims', '--dimensions', dest="dimensions", action="store", help="dimensions of the tonal space: left,bottom,right,top")
    parser.add_option('-c', '--chord-vocab', dest="chord_vocab", action="store", help="chord vocab file to load chord types from")
    parser.add_option('--hs', '--horiz-space', dest="hspace", action="store_true", help="leave space to the sides of the space if the window's big enough", default=False)
    parser.add_option('--vs', '--vert-space', dest="vspace", action="store_true", help="leave space to the top and bottom of the space if the window's big enough", default=False)
    parser.add_option('-t', '--tuner', dest="tuner", action="store_true", help="run the tonal space tuner")
    parser.add_option('--commands', dest="commands", action="store_true", help="display a list of commands available in the UI and instructions for use")
    options, arguments = parser.parse_args()
    
    if options.commands:
        print TonalSpaceWindow.HELP
        sys.exit(0)
    
    kwargs = {}
    if options.font_size is not None:
        kwargs['font_size'] = options.font_size
    if options.chord_vocab is not None:
        # Load chord types
        vocab = HarmonicalInputFile.from_file(options.chord_vocab, 
                                                    ['chord-vocab'])
        kwargs['chord_types'] = vocab.chords
        kwargs['chord_type_order'] = vocab.chord_names
    if options.instrument.lower() != 'n':
        kwargs['instrument'] = int(options.instrument)
    
    if options.dimensions is not None:
        dims = [int(dim) for dim in options.dimensions.split(",")]
        if len(dims) != 4:
            print >>sys.stderr, "Dimensions must be specified as four values: left,bottom,right,top"
            sys.exit(1)
        x0,y0,x1,y1 = dims
    else:
        x0,y0,x1,y1 = -4,-3,4,3
    
    # Output the midi device we're using
    midi_devs = get_midi_devices()
    if options.device >= len(midi_devs):
        print >>sys.stderr, "No midi device %d" % options.device
        sys.exit(1)
    else:
        print >>sys.stderr, "Sending midi events to device %d: %s" % (
                    options.device,
                    ", ".join(str(x) for x in midi_devs[options.device]))
    
    window = create_window(x0,y0,x1,y1, options.device, 
                    hfill=(not options.hspace), vfill=(not options.vspace), 
                    tuner=options.tuner, **kwargs)
    gtk.main()

if __name__ == "__main__":
    main()
