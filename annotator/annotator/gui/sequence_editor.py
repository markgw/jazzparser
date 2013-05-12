"""Annotated sequence editor.

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

import pygtk, gtk
from apps.sequences.models import Source

class SequenceEditorWindow(gtk.Window):
    """
    Window that displays the chords of a sequence and allows them to 
    be edited.
    
    """
    def __init__(self, sequence, *args, **kwargs):
        super(SequenceEditorWindow, self).__init__(*args, **kwargs)
        self.sequence = sequence
        
        ####### Window furniture
        # Set up the appearance of the window
        self.set_default_size(800, 600)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_title(u"%s - Sequence Editor - Jazznotate" % sequence.name)
        # A box to put all the widgets in
        vbox = gtk.VBox()
        self.add(vbox)
        
        # 
        
        self.show_all()

class SequenceDataEditorWindow(gtk.Window):
    """
    Window that displays the meta data of a sequence for editing.
    
    """
    def __init__(self, sequence, *args, **kwargs):
        super(SequenceDataEditorWindow, self).__init__(*args, **kwargs)
        self.sequence = sequence
        
        self.sources = [(None, "----")] + [(s, s.name) for s in Source.objects.all()]
        self.source_ids = [None if s is None else s.id for (s,name) in self.sources]
        
        ####### Window furniture
        # Set up the appearance of the window
        #self.set_default_size(600, 600)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_title(u"%s - Sequence Details - Jazznotate" % sequence.name)
        # A box to put all the widgets in
        vbox = gtk.VBox()
        self.add(vbox)
        
        # Create the fields
        self.fields = {}
        form_opts = {
            'xpadding' : 5,
            'ypadding' : 3,
            'xoptions' : gtk.FILL,
        }
        def _left(obj):
            al = gtk.Alignment(xalign=0.0)
            al.add(obj)
            return al
        form = gtk.Table(2,4,False)
        
        # Fields to add to the table
        bar_length_label = gtk.Label("Bar length")
        bar_length_field = gtk.SpinButton()
        bar_length_field.set_numeric(True)
        bar_length_field.set_range(0, 32)
        bar_length_field.set_increments(1,4)
        description_label = gtk.Label("Description")
        description_field = gtk.Entry()
        description_field.set_width_chars(80)
        source_label = gtk.Label("Source")
        source_field = gtk.combo_box_new_text()
        for source,name in self.sources:
            source_field.append_text(name)
            
        analysis_omitted_label = gtk.Label("Analysis omitted")
        analysis_omitted_field = gtk.CheckButton()
        
        # Position the fields
        form.attach(bar_length_label,         0,1, 0,1, **form_opts)
        form.attach(_left(bar_length_field),  1,2, 0,1, **form_opts)
        form.attach(description_label,        0,1, 1,2, **form_opts)
        form.attach(_left(description_field), 1,2, 1,2, **form_opts)
        form.attach(source_label,             0,1, 2,3, **form_opts)
        form.attach(_left(source_field),      1,2, 2,3, **form_opts)
        form.attach(analysis_omitted_label,   0,1, 3,4, **form_opts)
        form.attach(_left(analysis_omitted_field), 1,2, 3,4, **form_opts)
        
        
        # Keep hold of these for later
        self.fields['bar_length'] = bar_length_field
        self.fields['description'] = description_field
        self.fields['source'] = source_field
        self.fields['analysis_omitted'] = analysis_omitted_field
        
        vbox.pack_start(form, expand=False, padding=5)
        
        # Add buttons at the bottom
        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_END)
        
        save_button = gtk.Button("Ok")
        save_button.connect("clicked", self.save_and_exit)
        cancel_button = gtk.Button("Cancel")
        cancel_button.connect("clicked", self.exit)
        
        button_box.pack_end(cancel_button, expand=False, padding=5)
        button_box.pack_end(save_button, expand=False, padding=5)
        vbox.pack_end(button_box, expand=False, padding=5)
        
        self.populate_fields()
        self.show_all()
        
    def populate_fields(self):
        """
        Sets the values of the fields in the interface to match those 
        stored in the associated model.
        
        """
        self.fields['bar_length'].set_value(self.sequence.bar_length)
        if self.sequence.description is not None:
            self.fields['description'].set_text(self.sequence.description)
        if self.sequence.source_id is not None:
            self.fields['source'].set_active(self.source_ids.index(self.sequence.source_id))
        self.fields['analysis_omitted'].set_active(self.sequence.analysis_omitted)
        
    def save_and_exit(self, obj=None):
        self.save()
        self.exit()
        
    def exit(self, obj=None):
        self.destroy()
        
    def save(self):
        """
        Updates and saves the model on the basis of the fields in the 
        form.
        
        """
        self.sequence.bar_length = self.fields['bar_length'].get_value_as_int()
        self.sequence.description = self.fields['description'].get_text()
        self.sequence.source = self.sources[self.fields['source'].get_active()][0]
        self.sequence.analysis_omitted = self.fields['analysis_omitted'].get_active()
        self.sequence.save()
