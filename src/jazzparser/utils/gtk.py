from __future__ import absolute_import
"""PyGtk extensions

Small utilities for use with pygtk.

@warning: pygtk is used by all of these utilities, so it's imported 
at the module level. Don't import this module unless you're sure you 
want your code to depend on pygtk.

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
import gtk

def get_text_from_dialog(prompt=None, description=None, initial="", title=None):
    """
    Displays a Gtk dialog window to request a text entry.
    
    @type prompt: string
    @param prompt: message to display as a prompt
    @type description: string
    @param description: longer string to put in as a secondary prompt
    @type initial: string
    @param initial: value to put in the entry box to start with
    @type title: string
    @param title: window title for the dialog
    
    """
    if prompt is None:
        # Default to something generic
        prompt = "Please enter a value:"
    if title is None:
        title = "Enter value"
    dialog = gtk.MessageDialog(
                    None,
                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    gtk.MESSAGE_QUESTION,
                    gtk.BUTTONS_OK,
                    None )
    dialog.set_markup(prompt)
    dialog.set_title(title)
    # Create the text input field
    entry = gtk.Entry()
    if initial:
        entry.set_text(initial)
    # Allow the user to press enter to confirm
    entry.connect("activate", lambda entry,dia,resp:dia.response(resp), dialog, gtk.RESPONSE_OK)
    if description:
        # Some secondary text
        dialog.format_secondary_markup(description)
    dialog.vbox.pack_end(entry, True, True, 0)
    dialog.show_all()
    # Show the dialog
    dialog.run()
    text = entry.get_text()
    dialog.destroy()
    return text
