"""Interactive shell tools for the chordlabel tagger.

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

from jazzparser.shell.tools import Tool

class ChordLabelTool(Tool):
    name = "Chord labeler output tool"
    commands = [ "chords" ]
    usage = ('chord', "Show the chords that were assigned to the MIDI input "\
            "by the chord labeler")
    help = """\
Show the chords that were assigned to the MIDI input by the chord labeler 
module. These were used as input to the supertagger (and parser).

"""
    
    def run(self, args, state):
        chords = state.tagger.chords
        for chord in chords:
            print "%s  (%s)" % (chord, chord.duration)