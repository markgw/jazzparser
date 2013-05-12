from __future__ import absolute_import
"""Tonal space GUI interface.

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

# Check we've got the right version of PyGtk
# This check is made when this module first gets loaded
import pygtk
pygtk.require('2.0')

import gtk, sys, gobject, math, copy
from jazzparser.utils.gtk import get_text_from_dialog
from midi.sequencer_pygame import RealtimeSequencer
from midi import ProgramChangeEvent, single_note_tuning_event

from jazzparser.utils.tonalspace import coordinate_to_alpha_name_c
from jazzparser.harmonical.midi import tonal_space_note_events

class TonalSpaceWindow(gtk.Window):
    """
    A window that displays an interactive tonal space.
    
    """
    HELP = """\
The following keyboard commands are available from the GUI:
  F11: toggle fullscreen
  q:   quit
  x:   all notes off
  a:   clear selection
  c:   select a chord to play
  r:   toggle chord replace mode (chords replace all playing notes instead of 
       just adding to them)
  e:   toggle equal temperament. All notes played after this will be tuned 
       to equal temperament. Notes already playing will not be retuned 
       until they're replayed.
  Ctrl+e: select all equal-temperament equivalents of the current selection.
"""
    
    def __init__(self, left, bottom, right, top, sequencer, *args, **kwargs):
        """
        @type left: int
        @param left: leftmost column to include
        @type right: int
        @param right: rightmost column
        @type bottom: int
        @param bottom: lowest row
        @type top: int
        @param top: highest row
        @type sequencer: L{midi.sequencer_pygame.RealtimeSequencer}
        @param sequencer: sequencer to use for playing notes
        @type font_size: int or float
        @kwarg font_size: size in points of the font used to draw the cell labels
        @type chord_types: dict of coordinate lists (3-tuples)
        @kwarg chord_types: chord types to allow the user to add
        @type chord_type_order: list of strings
        @kwarg chord_type_order: ordered list giving the order of the chord types
            (optional)
        @type vfill: bool
        @kwarg vfill: expand the tonal space to fill the vertical size of the 
            window. Default: True.
        @type hfill: bool
        @kwarg hfill: expand the tonal space to fill the horizontal size of 
            the window. Default: True.
        
        """
        font_size = kwargs.pop('font_size', 14)
        self.font_size = font_size
        self.chord_types = kwargs.pop('chord_types', {})
        self.chord_type_order = kwargs.pop('chord_type_order', None)
        vfill = kwargs.pop('vfill', True)
        hfill = kwargs.pop('hfill', True)
        super(TonalSpaceWindow, self).__init__(gtk.WINDOW_TOPLEVEL, *args, **kwargs)
        
        self.sequencer = sequencer
        
        self.left = left
        self.right = right
        self.bottom = bottom
        self.top = top
        
        # Connect the basic event handlers
        self.connect("destroy", self.destroy)
        
        ####### Window furniture
        # Set up the appearance of the window
        DEFAULT_CELL_SIZE = 60
        self.set_default_size(DEFAULT_CELL_SIZE*(right-left), DEFAULT_CELL_SIZE*(top-bottom))
        self.set_title("Tonal Space")
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
        # A box to put all the widgets in
        hbox = gtk.HBox()
        vbox = gtk.VBox()
        hbox.pack_end(vbox, fill=hfill)
        self.add(hbox)
        # Bind keypress events to the window
        self.connect('key_press_event', self.on_key_press)
        
        self._fullscreen = False
        self.playing_cells = set()
        self.selected_cells = set()
        self.playing_midi_notes = {}
        
        self._cell_select_callback = None
        self._point_select_callback = None
        
        self.chords_replace = False
        self.equal_temperament = False
        
        # Create a tonal space grid
        grid = gtk.Table(top-bottom+1, right-left+1, homogeneous=True)
        self.grid = grid
        vbox.pack_end(grid, fill=vfill)
        
        self.cells = {}
        # Add the cells to the layout grid
        self.add_all_cells()
        
        # Create the chords menu
        self.chord_menu = gtk.Menu()
        if self.chord_type_order is None:
            self.chord_type_order = list(sorted(self.chord_types.keys()))
        if len(self.chord_type_order) > 0:
            for chord in self.chord_type_order:
                crd_item = gtk.MenuItem(label=chord)
                crd_item.show()
                # Define a closure to respond to the menu item selection
                def _get_chord_clicked(crd):
                    def _chord_clicked(item):
                        self.play_chord(crd)
                    return _chord_clicked
                crd_item.connect('activate', _get_chord_clicked(chord))
                self.chord_menu.append(crd_item)
        else:
            # No items to add
            dummy_item = gtk.MenuItem(label="No chord vocabularly loaded")
            dummy_item.set_sensitive(False)
            dummy_item.show()
            self.chord_menu.append(dummy_item)
        
        self.show_all()
        
        # Set the current cursor to the centre
        self.cursor = (0,0)
        self.set_cursor((0,0))
        
        # Create some extra cells
        self.create_buffer_cells()
    
    def get_cell_label(self, col, row):
        name = coordinate_to_alpha_name_c((col,row),
                    sharp = u"\u266F",
                    flat  = u"\u266D",
                    plus  = "<sup>+</sup>",
                    minus = "<sup>-</sup>")
        return name
        
    def toggle_fullscreen(self):
        if self._fullscreen:
            self.unfullscreen()
            self._fullscreen = False
        else:
            self.fullscreen()
            self._fullscreen = True
            
    def get_cell(self, x, y):
        """
        Returns the cell for the given 2D tonal space coordinate. Returns 
        None if this cell isn't in the visible region.
        
        """
        if x <= self.right and x >= self.left and \
                y <= self.top and y >= self.bottom:
            return self.cells[(x,y)]
        else:
            return None
    
    def get_point(self, x, y):
        """
        Returns the cell corresponding to the 2D TS coordinate, whether or 
        not it's in the visible region, creating it if necessary.
        
        """
        if (x,y) not in self.cells:
            self.cells[(x,y)] = self.create_cell(x, y)
        return self.cells[(x,y)]
    
    def center_grid(self, x, y):
        """
        Put the coordinate (x,y) in the centre of the visible grid by shifting 
        the portion visible.
        
        """
        width = self.right - self.left + 1
        height = self.top - self.bottom + 1
        # Work out the point we want in the bottom left to put (x,y) central
        left = x - (width / 2)
        bottom = y - (height / 2)
        # Work out how much to shift the space by
        shift_x = self.left - left
        shift_y = self.bottom - bottom
        self.shift_grid(shift_x, shift_y)
    
    def shift_grid(self, x, y):
        """
        Shift the visible portion of the tonal space covered by the grid.
        
        """
        self.remove_all_cells()
        self.left -= x
        self.right -= x
        self.top -= y
        self.bottom -= y
        self.add_all_cells()
        # Create a border of extra prepared cells
        self.create_buffer_cells()
    
    def remove_all_cells(self):
        # Remove all cells in the layout grid
        for cell in self.grid:
            self.grid.remove(cell)
    
    def add_all_cells(self):
        # Add all the cells in the cell matrix
        rows = self.top - self.bottom + 1
        for row,y in enumerate(range(self.bottom, self.top+1)):
            for col,x in enumerate(range(self.left, self.right+1)):
                self.grid.attach(self.get_point(x,y), 
                                 col, col+1, rows-row-1, rows-row,
                                 xoptions=(gtk.EXPAND|gtk.SHRINK|gtk.FILL),
                                 yoptions=(gtk.EXPAND|gtk.SHRINK|gtk.FILL) )
    
    def create_cell(self, col, row):
        return TonalSpaceCell(self.get_cell_label(col, row), 
                              self.sequencer, 
                              self,
                              coord=(col,row),
                              font_size=self.font_size)
    
    def create_buffer_cells(self):
        """ 
        Create some extra cells around the edge while we're not doing 
        anything else, so it doesn't take time when we need them.
        
        """
        for x in range(self.left-2, self.right+3):
            for y in range(self.bottom-2, self.top+3):
                self.get_point(x, y)
        
    def on_key_press(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        control = event.state & gtk.gdk.CONTROL_MASK
        if keyname == "F11":
            # Toggle fullscreen when F11 is pressed
            self.toggle_fullscreen()
        elif keyname == "x":
            # Cancel all playing notes
            self.all_notes_off()
        elif keyname == "q":
            # Exit
            print "Exiting"
            gtk.main_quit()
        elif keyname == "a":
            self.clear_selection()
        elif keyname == "c":
            # Pop up the chord menu
            self.show_chord_menu(event)
        elif keyname == "r":
            self.chords_replace = not self.chords_replace
            print "Chord replace mode %s" % ("on" if self.chords_replace else "off")
        elif control and keyname == "e":
            self.add_et_equivs()
        elif keyname == "e":
            self.equal_temperament = not self.equal_temperament
            if self.equal_temperament:
                print "Equal temperament"
            else:
                print "True tonal space intonation"
        elif keyname == "Right":
            self.set_cursor((1,0))
        elif keyname == "Left":
            self.set_cursor((-1,0))
        elif keyname == "Up":
            self.set_cursor((0,1))
        elif keyname == "Down":
            self.set_cursor((0,-1))
        elif keyname == "space":
            # This isn't right, but I don't really care
            pos = self.get_cell(*self.cursor).window.get_position()
            def _get_positioner(x,y):
                def _positioner(menu):
                    return x,y,False
                return _positioner
            self.get_cell(*self.cursor).menu.popup(None, None, _get_positioner(*pos), 0, event.time)
        elif keyname == "F1":
            self.center_grid(*self.cursor)
        elif keyname == "Home":
            self.center_grid(0,0)
            self.set_cursor((0,0), absolute=True)
        
    def destroy(self, widget, data=None):
        """Handler for window destruction."""
        gtk.main_quit()
        
    def all_notes_off(self):
        playing_cells = copy.copy(self.playing_cells)
        for cell in playing_cells:
            cell.all_off()
    
    def clear_selection(self):
        selection = copy.copy(self.selected_cells)
        for cell in selection:
            cell.deselect()
    
    def select_et_equivs(self, coord):
        """
        Select all equal-temperament equivalents of the given coord (not 
        including the coord itself).
        
        """
        start_col = self.left + (coord[0]-self.left) % 4
        # Each fourth column
        for col in range(start_col, self.right+1, 4):
            spacex = int(math.floor(float(col-coord[0])/4))
            start_row = self.bottom + (coord[1]-self.bottom-spacex) % 3
            # Each third row, shifted down one for each column right
            for row in range(start_row, self.top+1, 3):
                # Skip the coordinate itself
                if (col,row) != (coord[0],coord[1]):
                    # Select this point
                    self.get_cell(col, row).select()
        
    def add_et_equivs(self):
        """
        Add to the current selection all equal-temperament equivalents of the 
        notes currently selected.
        
        """
        selection = copy.copy(self.selected_cells)
        for cell in selection:
            self.select_et_equivs(cell.coord)
            
    def show_chord_menu(self, event):
        # Pop up the chord menu next to the mouse
        time = event.time
        self.chord_menu.popup(None, None, None, 0, time)
        return True
        
    def cell_clicked(self, cell, event):
        """
        Called by each cell when it gets clicked. If we return True here, 
        it means the cell shouldn't do its usual click actions, because we're 
        doing something that replaces them. Otherwise, the cell can go ahead 
        and do its usual thing.
        
        """
        callback = getattr(self, '_cell_select_callback')
        if callback is not None:
            # Call the callback on this cell and event
            return callback(cell, event)
        return False
        
    def point_selected(self, cell, octave, item):
        """
        Works like cell_clicked, but called when a 3D position (i.e., cell 
        plus octave) is selected.
        
        """
        callback = getattr(self, '_point_select_callback')
        if callback is not None:
            return callback(cell, octave, item)
        return False
        
    def play_chord(self, chord_name):
        """
        Set the notes of a particular chord going.
        
        The first thing this does is to wait for the user to select a chord 
        root. Then it positions the note cluster around the root and plays 
        those notes.
        
        """
        # Set up a callback to happen when the user next clicks a cell
        def _callback(cell, octave, item):
            # If chords_replace is toggled, clear all playing notes before 
            #  adding the new ones
            if self.chords_replace:
                self.all_notes_off()
            root = (cell.coord[0], cell.coord[1], octave)
            # Get the notes of this chord type
            notes = self.chord_types[chord_name]
            # Shift all the notes so the chord is rooted at the selected point
            def _sum3d(c1, c2):
                return (c1[0]+c2[0], c1[1]+c2[1], c1[2]+c2[2])
            notes = [_sum3d(root, n) for n in notes]
            # Set all the notes playing
            for note in notes:
                self.play_note(note)
            # Don't do this next time a point is selected
            self._point_select_callback = None
            return True
        self._point_select_callback = _callback
        
    def play_note(self, coord):
        """
        Set the note playing corresponding to a 3D coordinate, if that 
        note is in the current portion of the tonal space.
        
        """
        x,y,z = coord
        cell = self.get_cell(x, y)
        if cell is not None:
            # Only start it playing if it's not already playing
            if z not in cell.playing:
                cell.toggle_note(z)
    
    def set_cursor(self, coord, absolute=False):
        """
        Set the 2D coord to be under the current cursor. By default, 
        relative to the previous.
        
        """
        # Calculate the relative cursor position
        if not absolute:
            coord = [self.cursor[0]+coord[0], self.cursor[1]+coord[1]]
            # Check whether the coordinate is off the showing grid
            if coord[0] < self.left:
                coord[0] = self.left
            elif coord[0] > self.right:
                coord[0] = self.right
            if coord[1] < self.bottom:
                coord[1] = self.bottom
            elif coord[1] > self.top:
                coord[1] = self.top
        # Undraw the old cursor
        old_cell = self.cursor_cell.unset_cursor()
        # Draw the new cursor marking
        self.cursor = tuple(coord)
        self.cursor_cell.set_cursor()
    
    @property
    def cursor_cell(self):
        return self.get_point(*self.cursor)

class TonalSpaceCell(gtk.EventBox):
    """
    Widget to draw a single point in the tonal space.
    
    """
    def __init__(self, label, sequencer, parent, font_size=14.0, coord=(0,0)):
        gtk.EventBox.__init__(self)
        
        self.sequencer = sequencer
        self.coord = coord
        self.parent_window = parent
        self._selected = False
        
        self.unselected_color = gtk.gdk.color_parse("white")
        self.unselected_text_color = gtk.gdk.color_parse("black")
        self.selected_color = gtk.gdk.color_parse("#C45656")
        self.selected_text_color = gtk.gdk.color_parse("white")
        self.playing_color = gtk.gdk.color_parse("#C2D0E0")
        
        # Set the background colour to black to get the border
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
        
        # Add another event box for the white area in the middle
        self.white_box = gtk.EventBox()
        self.white_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))
        self.white_box.set_border_width(1)
        self.add(self.white_box)
        
        self.vbox = gtk.VBox()
        self.white_box.add(self.vbox)
        
        # Add the text in a label
        self.label = gtk.Label()
        # Set the text size
        font_size = int(font_size * 1000)
        markup = u'<span size="%s">%s</span>' % (font_size, label)
        self.label.set_markup(markup)
        self.vbox.pack_start(self.label, expand=True)
        
        # Display playing notes at the bottom
        self.playing_box = gtk.HBox()
        self.vbox.pack_end(self.playing_box, expand=False)
        
        # Keep track of which notes (octaves of this coord) are playing
        self.playing = []
        self.playing_labels = {}
        
        # Prepare a menu to appear when we click on the cell
        # Calculate what octave we're in relative to (0,0)
        octave = int(math.floor(math.log(1.5**coord[0] * 1.25**coord[1], 2)))
        # Make the choice of octaves be centred on the octave (0,0) is in
        center = -1*octave
        
        self.menu = gtk.Menu()
        for i in range(center-2, center+3):
            if i > 0:
                label = "+%d" % i
            else:
                label = str(i)
            menuitem = gtk.MenuItem(label=label)
            menuitem.show()
            # Respond to selecting this by toggling the note playing
            def _get_note_toggler(octave):
                def _note_toggler(widget):
                    finished = self.parent_window.point_selected(self, octave, widget)
                    if not finished:
                        self.toggle_note(octave)
                    return True
                return _note_toggler
            menuitem.connect("activate", _get_note_toggler(i))
            self.menu.append(menuitem)
        
        # Respond to a click event
        self.connect("button_press_event", self.button_press_event)
        self.set_events(self.get_events() | gtk.gdk.BUTTON_PRESS_MASK)
        self.show_all()
    
    def button_press_event(self, widget, event):
        # Let the main window do what it likes
        finished = self.parent_window.cell_clicked(self, event)
        if not finished:
            if event.button == 3:
                # Right click
                self.toggle_selected()
            else:
                # Pop up the menu next to the mouse
                time = event.time
                self.menu.popup(None, None, None, event.button, time)
        return True
        
    def toggle_note(self, octave):
        """Start or stop a note playing"""
        # Get the events (note on and off) for this coordinate
        tuning, note_on, note_off = tonal_space_note_events(
                                        (self.coord[0], self.coord[1], octave),
                                        0, 0)
        if octave in self.playing:
            self.playing.remove(octave)
            del self.parent_window.playing_midi_notes[note_on.pitch]
            self.sequencer.send_event(note_off)
            # If no more notes playing, remove ourselves from the global playing record
            if len(self.playing) == 0:
                self.parent_window.playing_cells.remove(self)
        else:
            # If another instance of this ET note is playing, stop it, because 
            #  it will get retuned by this tuning event :-(
            if note_on.pitch in self.parent_window.playing_midi_notes:
                oldcell,oldoctave = self.parent_window.playing_midi_notes[note_on.pitch]
                oldcell.toggle_note(oldoctave)
            # Start the note playing
            self.playing.append(octave)
            if self.parent_window.equal_temperament:
                # Return the note to its default tuning (ET)
                tuning = single_note_tuning_event(
                                    [(note_on.pitch, note_on.pitch, 0)])
            self.sequencer.send_event(tuning)
            self.sequencer.send_event(note_on)
            # Note globally that we're playing
            self.parent_window.playing_cells.add(self)
            self.parent_window.playing_midi_notes[note_on.pitch] = (self, octave)
            
        self.refresh_playing()
    
    def retune_note(self, octave):
        """Retune the given note without playing it."""
        # Get the tuning event for this coordinate
        tuning, note_on, note_off = tonal_space_note_events(
                                        (self.coord[0], self.coord[1], octave),
                                        0, 0)
        self.sequencer.send_event(tuning)
    
    def select(self):
        """Set this cell to be part of the current selection."""
        self._selected = True
        self.parent_window.selected_cells.add(self)
        self.white_box.modify_bg(gtk.STATE_NORMAL, self.selected_color)
        self.label.modify_fg(gtk.STATE_NORMAL, self.selected_text_color)
        
    def deselect(self):
        """Removes this cell from the current selection."""
        self._selected = False
        self.parent_window.selected_cells.remove(self)
        # Use the playing colour if a note is playing
        if len(self.playing) > 0:
            self.white_box.modify_bg(gtk.STATE_NORMAL, self.playing_color)
        else:
            self.white_box.modify_bg(gtk.STATE_NORMAL, self.unselected_color)
        self.label.modify_fg(gtk.STATE_NORMAL, self.unselected_text_color)
    
    def toggle_selected(self):
        if self._selected:
            self.deselect()
        else:
            self.select()
    
    def set_cursor(self):
        """Display the cursor on this cell"""
        self.white_box.set_border_width(3)
    
    def unset_cursor(self):
        self.white_box.set_border_width(1)
        
    def all_off(self):
        """Cancel all playing notes."""
        for octave in copy.copy(self.playing):
            self.toggle_note(octave)
    
    def refresh_playing(self):
        """
        Refreshes the display of which notes are playing.
        
        """
        # Remove notes no longer playing
        not_playing = set(self.playing_labels.keys()) - set(self.playing)
        for octave in not_playing:
            self.playing_labels[octave].destroy()
            del self.playing_labels[octave]
        # Add notes playing but not displayed
        new_playing = set(self.playing) - set(self.playing_labels.keys())
        for octave in new_playing:
            # Put the label in an event box, so we can click on it
            eb = gtk.EventBox()
            eb.set_visible_window(False)
            label = gtk.Label(str(octave))
            eb.add(label)
            eb.add_events(gtk.gdk.BUTTON_PRESS_MASK)
            # Add the label to the list
            self.playing_box.add(eb)
            # Define an action to trigger the note off when the label's clicked on
            def _get_note_toggler(i):
                def _note_toggler(widget, event):
                    self.toggle_note(i)
                    return True
                return _note_toggler
            eb.connect("button_press_event", _get_note_toggler(octave))
            eb.show()
            label.show()
            # Keep this so we can remove it later
            self.playing_labels[octave] = eb
        # Set the colour depending on whether we're playing
        if not self._selected:
            if len(self.playing) == 0:
                # No note playing: set the normal unselected colour
                self.white_box.modify_bg(gtk.STATE_NORMAL, self.unselected_color)
            else:
                # Something's playing: use the playing colour
                self.white_box.modify_bg(gtk.STATE_NORMAL, self.playing_color)

def create_window(left, bottom, right, top, device_id, tuner=False, **kwargs):
    sequencer = RealtimeSequencer(device_id)
    instr = kwargs.pop('instrument', None)
    if instr is not None:
        pc = ProgramChangeEvent()
        pc.value = instr
        sequencer.send_event(pc)
    if tuner:
        from .tstuner import TonalSpaceRetunerWindow
        cls = TonalSpaceRetunerWindow
    else:
        cls = TonalSpaceWindow
    return cls(left, bottom, right, top, sequencer, **kwargs)
