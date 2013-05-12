from __future__ import absolute_import
"""Tonal space retuning GUI interface.

Super-cool awesome.

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

import gtk, sys, gobject

from . import tsgui

OCTAVE_REGION = [
    (-1, -1, 1),
    (-1, 0,  1),
    (-1, 1,  1),
    (0,  -1, 1),
    (0,  0,  0),
    (0,  1,  0),
    (1,  -1, 0),
    (1,  0,  0),
    (1,  1,  0),
    (2,  -1, 0),
    (2,  0, -1),
    (2,  1, -1),
]

from jazzparser.utils.tonalspace import coordinate_to_et

class TonalSpaceRetunerWindow(tsgui.TonalSpaceWindow):
    def on_key_press(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        control = event.state & gtk.gdk.CONTROL_MASK
        if keyname == "space":
            # Retune to the currently selected tonal centre
            # Display the region we've tuned to as a selection
            self.clear_selection()
            # Tune each note in the region around the tonal centre
            cursor = self.cursor
            # Centre the grid on this point
            self.center_grid(*self.cursor)
            for rel_col,rel_row,__ in OCTAVE_REGION:
                col = cursor[0]+rel_col
                row = cursor[1]+rel_row
                # Work out the native octave of this point
                note_number = coordinate_to_et((col,row,0)) + 60
                octave_number = note_number / 12
                for keyboard_octave in range(0, 11):
                    # Shift the octave to this keyboard octave and retune the note
                    octave_shift = keyboard_octave-octave_number
                    cell = self.get_cell(col, row)
                    cell.retune_note(octave_shift)
                    cell.select()
        else:
            super(TonalSpaceRetunerWindow, self).on_key_press(widget, event)
