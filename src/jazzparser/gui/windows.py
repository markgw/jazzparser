"""Graphical interface for the Jazz Parser.

Very much not finished yet, but would be nice to finish in the future. 
Just makes taking input and choosing parameters easier.

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

import gtk, pango, sys, gobject
from jazzparser.data.input import INPUT_TYPES, BULK_INPUT_TYPES, get_input_type
from jazzparser.utils.options import file_option, new_file_option, \
                    zero_to_one_float, choose_from_dict, choose_from_list

class GraphicalJazzParserWindow(gtk.Window):
    """
    Main top-level interface window.
    
    """
    def __init__(self, *args, **kwargs):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL, *args, **kwargs)
        # Window setup
        self.set_border_width(5)
        self.set_title("Jazz Parser")
        
        ### Layout ###
        self._vbox = gtk.VBox(spacing=5)
        self.add(self._vbox)
        ### Input box
        self._input_frame = gtk.Frame(label="Input")
        self._input_box = gtk.VBox(spacing=4)
        self._input_box.set_border_width(5)
        self._input_frame.add(self._input_box)
        self._vbox.add(self._input_frame)
        # Input type selector
        input_type_box = gtk.HBox(spacing=3)
        input_type_label = gtk.Label("Input type:")
        input_type_box.add(input_type_label)
        input_type_selector = gtk.combo_box_new_text()
        for (itype_name,itype) in INPUT_TYPES+BULK_INPUT_TYPES:
            input_type_selector.append_text(itype_name)
        input_type_box.add(input_type_selector)
        self._input_type_selector = input_type_selector
        self._input_box.add(input_type_box)
        # Input file selector
        input_file_box = gtk.HBox(spacing=3)
        self._filename_label = gtk.Label("No file selected")
        input_file_box.add(self._filename_label)
        file_button = gtk.Button("Choose file")
        input_file_box.add(file_button)
        file_button.connect("clicked", self.select_input_file)
        self._input_box.add(input_file_box)
        # Input options editor
        input_options_box = gtk.HBox(spacing=3)
        # TODO: display the current options in here
        input_options_button = gtk.Button("Input options")
        input_options_box.add(input_options_button)
        input_options_button.connect("clicked", self.edit_input_options)
        self._input_box.add(input_options_box)
        ### Tagger box
        self._tagger_frame = gtk.Frame(label="Supertagger")
        self._tagger_hbox = gtk.HBox()
        self._tagger_frame.add(self._tagger_hbox)
        self._vbox.add(self._tagger_frame)
        ### Parser box
        self._parser_frame = gtk.Frame(label="Parser")
        self._parser_hbox = gtk.HBox()
        self._parser_frame.add(self._parser_hbox)
        self._vbox.add(self._parser_frame)
        
        ## Events
        # Stop PyGtk when the window is closed
        self.connect("destroy", self.destroy)
        
    def select_input_file(self, widget, data=None):
        # Prepare and display a file chooser dialog
        chooser = gtk.FileChooserDialog("Select input file", self, 
                            gtk.FILE_CHOOSER_ACTION_OPEN,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        response = chooser.run()
        # If a file was selected, update the display
        if response == gtk.RESPONSE_OK:
            filename = chooser.get_filename()
            self._filename_label.set_text(filename)
            
        chooser.destroy()
    
    def edit_input_options(self, widget, data=None):
        # Get the appropriate options for the input type
        type_name = self._input_type_selector.get_active_text()
        if type_name is None:
            show_error("Select an input type", self)
        else:
            input_type = get_input_type(type_name)
            # Display an edition for the input options
            editor = ModuleOptionsWindow(input_type.FILE_INPUT_OPTIONS, 
                                            self, "Input options")
            editor.show_all()
    
    def update_input_options(self, values):
        ## TODO
        print values
        
    def destroy(self, obj=None):
        gtk.main_quit()

class ModuleOptionsWindow(gtk.Window):
    """
    Generic editing window for module options.
    
    """
    def __init__(self, options, parent, title="Edit options", *args, **kwargs):
        gtk.Window.__init__(self, *args, **kwargs)
        self.set_title(title)
        self.set_modal(True)
        self.set_transient_for(parent)
        self.set_border_width(5)
        self.main_window = parent
        
        # Add widgets for each option
        if len(options) == 0:
            self.add(gtk.Label("No options for this input type"))
        else:
            vbox = gtk.VBox(spacing=3)
            for option in options:
                hbox = gtk.HBox(spacing=5)
                # The input type depends on the filter
                if option.filter == int:
                    # Use an integer selector
                    hbox.add(gtk.Label(option.name))
                    hbox.add(gtk.SpinButton(
                                gtk.Adjustment(value=0, lower=0, upper=9999, 
                                        step_incr=1),
                                0, 0))
                elif option.filter == file_option:
                    # TODO: use a file selector
                    raise NotImplementedError
                elif option.filter == new_file_option:
                    # TODO: do something clever
                    raise NotImplementedError
                elif option.filter == float:
                    # TODO: use a float spinner
                    raise NotImplementedError
                elif option.filter == zero_to_one_float:
                    # TODO: use a float spinner
                    raise NotImplementedError
                elif option.filter == choose_from_dict:
                    # TODO: use a combobox on the keys
                    raise NotImplementedError
                elif option.filter == choose_from_list:
                    # TODO: use a combobox
                    raise NotImplementedError
                else:
                    # Just take string input
                    hbox.add(gtk.Label(option.name))
                    hbox.add(gtk.Entry())
                vbox.add(hbox)
        
            self.add(vbox)
        
        self.connect("destroy", self.destroy)
        self.show_all()
    
    def destroy(self, widget):
        self.main_window.update_input_options({})
        super(ModuleOptionsWindow, self).destroy()

def show_error(message, parent=None):
    dlg = gtk.MessageDialog(parent=parent, 
                            type=gtk.MESSAGE_ERROR, 
                            message_format=message, 
                            buttons=gtk.BUTTONS_OK)
    dlg.run()
    dlg.destroy()
    
