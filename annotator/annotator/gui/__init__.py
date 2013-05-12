"""GUI for sequence annotation.

This is a GUI for annotating chord sequences and aligning them with 
midi data.

I originally build the Django web interface for annotation and for that 
it served me well. However, I'm now trying to align the data with midi 
files and it's really important that the interface design lets me do it 
quickly. Rather than continuing to build on the web interface, I've 
decided to have a shot at building a Gtk interface instead.

"""
"""
============================== License ========================================
 Copyright (C) 2008, 2010-11 University of Edinburgh, Mark Granroth-Wilding
 
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

import gtk, sys, gobject
from apps.sequences.models import Song, MidiData
from jazzparser.utils.gtk import get_text_from_dialog

class SongListWindow(gtk.Window):
    """
    The first window that opens, displaying a list of the songs in the 
    database.
    
    """
    def __init__(self, *args, **kwargs):
        super(SongListWindow, self).__init__(gtk.WINDOW_TOPLEVEL, *args, **kwargs)
        # Connect the basic event handlers
        self.connect("destroy", self.destroy)
        
        # Read the songs from the database
        songs = Song.objects.all()
        
        ####### Window furniture
        # Set up the appearance of the window
        self.set_default_size(300, 800)
        self.set_title("Jazznotate - The Jazz Parser Annotation GUI")
        # A box to put all the widgets in
        vbox = gtk.VBox()
        self.add(vbox)
        
        ######## The song list
        # Set up the tree to contain the songs and their sequences
        treestore = gtk.TreeStore(gobject.TYPE_STRING)
        # Add all the songs from the database to the store
        self.songs = []
        for song in songs:
            song_pos = treestore.append(None, [song.name])
            song_seqs = []
            for sequence in song.chordsequence_set.all():
                treestore.append(song_pos, [sequence.sequence_distinguisher])
                song_seqs.append(sequence)
            self.songs.append((song,song_seqs))
        treeview = gtk.TreeView(treestore)
        self.treeview = treeview
        
        # Let the list respond to clicks
        self.treeview.connect("button_press_event", self.list_clicked)
        
        # Add a column to the treeview to display the song names
        name_column = gtk.TreeViewColumn("Song name")
        self.treeview.append_column(name_column)
        # Render the song names as text
        name_renderer = gtk.CellRendererText()
        name_column.pack_start(name_renderer, True)
        name_column.add_attribute(name_renderer, "text", 0)
        # Make it possible to search the signs
        self.treeview.set_search_column(0)
        
        # Put the treeview in scrollbars
        treeview_scroll = gtk.ScrolledWindow()
        treeview_scroll.add_with_viewport(treeview)
        
        vbox.add(treeview_scroll)
        
        # Add buttons at the bottom
        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_END)
        
        midi_button = gtk.Button("Midis")
        midi_button.connect("clicked", self.open_midis)
        edit_button = gtk.Button("Edit sequence")
        edit_button.connect("clicked", self.open_sequence)
        meta_edit_button = gtk.Button("Edit sequence details")
        meta_edit_button.connect("clicked", self.open_sequence_meta)
        song_edit_button = gtk.Button("Edit song details")
        song_edit_button.connect("clicked", self.open_song)
        
        button_box.pack_end(midi_button, expand=False, padding=5)
        button_box.pack_end(song_edit_button, expand=False, padding=5)
        button_box.pack_end(meta_edit_button, expand=False, padding=5)
        button_box.pack_end(edit_button, expand=False, padding=5)
        vbox.pack_end(button_box, expand=False, padding=5)
        
        # Prepare popup menus for right-clicking on the list
        # Two menus for different conditions
        sequence_meta_item = gtk.MenuItem("Edit sequence details")
        sequence_meta_item.connect("activate", self.open_sequence_meta)
        sequence_meta_item.show()
        sequence_edit_item = gtk.MenuItem("Edit sequence")
        sequence_edit_item.connect("activate", self.open_sequence)
        sequence_edit_item.show()
        midis_item = gtk.MenuItem("Show midi records")
        midis_item.connect("activate", self.open_midis)
        midis_item.show()
        song_edit_item = gtk.MenuItem("Edit song details")
        song_edit_item.connect("activate", self.open_song)
        song_edit_item.show()
        
        self.menu_sequence_and_song = gtk.Menu()
        self.menu_sequence_and_song.append(sequence_meta_item)
        self.menu_sequence_and_song.append(sequence_edit_item)
        self.menu_sequence_and_song.append(midis_item)
        self.menu_sequence_and_song.append(song_edit_item)
        
        song_edit_item2 = gtk.MenuItem("Edit song details")
        song_edit_item2.connect("button_press_event", self.open_song)
        song_edit_item2.show()
        self.menu_song = gtk.Menu()
        self.menu_song.append(song_edit_item2)
        
        self.show_all()
        
    def list_clicked(self, treeview, event):
        if event.button == 3:
            # Right click
            # First perform the selection for the click, in case it's not done already
            pthinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                # Now decide what to pop up
                song = self.get_selected_song()
                sequence = self.get_selected_seqeuence()
                if song is not None:
                    if sequence is not None:
                        # Both available: show the full menu
                        self.menu_sequence_and_song.popup(None, None, None, event.button, event.time)
                    else:
                        # Only song available
                        self.menu_song.popup(None, None, None, event.button, event.time)
        
    def open_midis(self, *args, **kwargs):
        sequence = self.get_selected_seqeuence()
        if sequence is not None:
            # Open up the midi list window for this sequence
            editor = MidiListWindow(sequence)
        
    def open_sequence(self, *args, **kwargs):
        sequence = self.get_selected_seqeuence()
        if sequence is not None:
            # Open up the editor window for this sequence
            from sequence_editor import SequenceEditorWindow
            editor = SequenceEditorWindow(sequence)
        
    def open_sequence_meta(self, *args, **kwargs):
        sequence = self.get_selected_seqeuence()
        if sequence is not None:
            # Open up the editor window for this sequence
            from sequence_editor import SequenceDataEditorWindow
            editor = SequenceDataEditorWindow(sequence)
        
    def open_song(self, *args, **kwargs):
        song = self.get_selected_song()
        if song is not None:
            # Open up the editor window for this song
            raise NotImplementedError, "not implemented song editing yet"
            
    def get_selected_song(self):
        """
        Returns the song that's selected in the treeview. If a sequence 
        is selected, returns the song that's the parent of the sequence.
        """
        store,selected = self.treeview.get_selection().get_selected_rows()
        if len(selected) > 0:
            # Just look at the first selection
            selected_item = selected[0]
            if len(selected_item) == 1 or len(selected_item) == 2:
                # Sequence or song selected
                song_index = selected_item[0]
                return self.songs[song_index][0]
            else:
                # Odd
                return
            
    def get_selected_seqeuence(self):
        """
        Return the sequence that's selected in the treeview.
        
        """
        store,selected = self.treeview.get_selection().get_selected_rows()
        if len(selected) > 0:
            # Multiple select shouldn't be allowed, so just look at the 
            #  first in the selection
            selected_item = selected[0]
            if len(selected_item) == 1:
                # Top-level item
                song_index = selected_item[0]
                # If the song only has one sequence, open it
                if len(self.songs[song_index][1]) == 1:
                    return self.songs[song_index][1][0]
                else:
                    # Otherwise do nothing
                    return
            elif len(selected_item) == 2:
                # Sequence selected
                song_index,sequence_index = selected_item
                return self.songs[song_index][1][sequence_index]
            else:
                # Odd
                return
        
    def destroy(self, widget, data=None):
        """Handler for window destruction."""
        gtk.main_quit()

class MidiListWindow(gtk.Window):
    """
    Displays a list of the midi records available for a particular 
    sequence.
    
    """
    def __init__(self, sequence, *args, **kwargs):
        super(MidiListWindow, self).__init__(*args, **kwargs)
        # Connect the basic event handlers
        self.connect("destroy", self.destroy)
        
        # Read the midi records from the database
        midis = list(sequence.mididata_set.all())
        
        ####### Window furniture
        # Set up the appearance of the window
        self.set_default_size(300, 400)
        self.set_title(u"%s midi files - Jazznotate" % sequence.name)
        # A box to put all the widgets in
        vbox = gtk.VBox()
        self.add(vbox)
        
        ######## The song list
        # Set up the tree to contain the songs and their sequences
        liststore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        # Add all the midi records to the store
        for midi in midis:
            liststore.append(["%s" % midi.id, midi.name])
        treeview = gtk.TreeView(liststore)
        self.treeview = treeview
        self.liststore = liststore
        
        # Add a column to the treeview to display the song names
        id_column = gtk.TreeViewColumn("Id")
        name_column = gtk.TreeViewColumn("Name")
        self.treeview.append_column(id_column)
        self.treeview.append_column(name_column)
        # Render the midi names as text
        name_renderer = gtk.CellRendererText()
        name_column.pack_start(name_renderer, True)
        name_column.add_attribute(name_renderer, "text", 1)
        id_renderer = gtk.CellRendererText()
        id_column.pack_start(id_renderer, True)
        id_column.add_attribute(id_renderer, "text", 0)
        
        # Put the treeview in scrollbars
        treeview_scroll = gtk.ScrolledWindow()
        treeview_scroll.add_with_viewport(treeview)
        
        vbox.add(treeview_scroll)
        
        # Add a double-click event to the list, to make opening quicker
        self.treeview.connect("button_press_event", self.list_click)
        
        # Add buttons at the bottom
        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_END)
        
        alignment_button = gtk.Button("Alignment")
        alignment_button.connect("clicked", self.open_alignment)
        rename_button = gtk.Button("Rename")
        rename_button.connect("clicked", self.rename_midi)
        button_box.pack_end(rename_button, expand=False, padding=5)
        button_box.pack_end(alignment_button, expand=False, padding=5)
        
        vbox.pack_end(button_box, expand=False, padding=5)
        
        self.midis = midis
        self.show_all()
        
    def list_click(self, treeview, event):
        # Respond to double-click on the list
        if event.type == gtk.gdk._2BUTTON_PRESS:
            self.open_alignment()
        
    def open_alignment(self, *args, **kwargs):
        midi = self.get_selection()
        if midi is not None:
            from midi_align import MidiAlignmentWindow
            alignment = MidiAlignmentWindow(midi)
            self.destroy()
            
    def rename_midi(self, *args, **kwargs):
        midi = self.get_selection()
        if midi is not None:
            # Also note what item was selected
            model,seliter = self.treeview.get_selection().get_selected()
            text = get_text_from_dialog(
                            prompt="Enter a new name:",
                            initial=midi.name,
                            title="Rename midi"
                        )
            if text is not None:
                midi.name = text
                midi.save()
                # Update the name in the list
                self.liststore.set(seliter, 1, midi.name)
        
    def get_selection(self):
        store,selected = self.treeview.get_selection().get_selected_rows()
        if len(selected) > 0:
            # Multiple select shouldn't be allowed, so just look at the 
            #  first in the selection
            selected_item = selected[0]
            if len(selected_item) == 1:
                # Top-level item
                midi_index = selected_item[0]
                return self.midis[midi_index]
    
    def destroy(self, obj=None):
        super(MidiListWindow, self).destroy()
