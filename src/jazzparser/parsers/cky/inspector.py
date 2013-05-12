"""Chart inspector, for viewing the chart during parsing.

A graphical interface to observe the state of a chart during parsing.
A chart inspector runs alongside the parser in a separate thread 
and updates its representation of the chart from the actual one being 
manipulated by the parser whenever the user asks for an update.

The inspector shows the number of signs in each cell of the chart 
and allows inspection of what those signs are and even the derivation 
trace (if available) for each one.

Note that this module uses PyGtk, which is not required for most of 
the project. You should not import anything from this module at the 
top level, but only when you need it. That way, if PyGtk is not 
installed, an error will only occur when you try to use it.

You can also read a pickled chart in from a file and use the chart 
inspector to examine it.

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
import copy
from threading import Thread

LAST_UPDATE_COLOR = "#f0d0d0"

class CellInspectorWindow(gtk.Window):
    """
    A small window that gives more information about a particular cell 
    in the chart. Displays a list of the signs in that cell.
    This gets popped up when you click on a cell.
    
    """
    def __init__(self, signs, from_node, to_node, parent=None, *args, **kwargs):
        """
        Creates a new mini inspector window to show information about a 
        cell in the chart.
        
        @type signs: list of signs
        @param signs: the signs contained in the cell
        @type from_node: int
        @param from_node: the start node of the chart edge represented 
            by this cell.
        @type to_node: int
        @param to_node: the end node of the edge.
        @type parent: gtk.Window
        @param parent: the parent window of this small dialog. If 
            omitted, the window will be considered top-level.
        
        """
        super(CellInspectorWindow, self).__init__(*args, **kwargs)
        self.signs = signs
        self.from_node = from_node
        self.to_node = to_node
        
        ####### Window furniture
        # Set up the appearance of the windw
        self.set_modal(True)
        self.set_default_size(400, 800)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_title("Cell (%d,%d) of chart - The Jazz Parser" % (from_node, to_node))
        # A box to put all the widgets in
        vbox = gtk.VBox()
        self.add(vbox)
        
        if parent is not None:
            # Make this like a dialog window subject to a parent window
            self.set_transient_for(parent)
            self.set_destroy_with_parent(True)
            
        ######## The list
        # Set up the list to contain the signs
        liststore = self._create_column_data()
        self.liststore = liststore
        
        treeview = gtk.TreeView(liststore)
        self.treeview = treeview
        # Create the column definitions
        self._create_columns()
        # Put the treeview in scrollbars
        treeview_scroll = gtk.ScrolledWindow()
        treeview_scroll.add_with_viewport(treeview)
        # Connect a click event to the list
        treeview.connect("button_press_event", self.popup_item_menu)
        
        ######## Context menu
        # Create a context menu to appear when right-clicking on an item
        menu = gtk.Menu()
        # Add any menu items
        deriv_item = gtk.MenuItem("Show derivation trace")
        deriv_item.show()
        deriv_item.connect("activate", self.show_derivation_window)
        menu.append(deriv_item)
        
        vbox.add(treeview_scroll)
        
        # Keep references to things we might need
        self.context_menu = menu
        
        self.show_all()
        
    def _create_column_data(self):
        """
        Creates the data for the TreeView.
        This allows the display to be overridden by subclasses.
        
        """
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        # Add all the signs to the store
        for sign in self.signs:
            liststore.append(["%s" % sign])
        return liststore
        
    def _create_columns(self):
        """
        Instantiates the TreeView's columns and adds them to the 
        TreeView self.treeview.
        This allows the display to be overridden by subclasses.
        
        """
        # Add a column to the treeview to display the signs
        sign_column = gtk.TreeViewColumn("Signs on edge (%d,%d)" % (self.from_node, self.to_node))
        self.treeview.append_column(sign_column)
        # Render the signs as text
        sign_renderer = gtk.CellRendererText()
        sign_renderer.set_property('family', 'monospace')
        sign_column.pack_start(sign_renderer, True)
        sign_column.add_attribute(sign_renderer, "text", 0)
        # Make it possible to search the signs
        self.treeview.set_search_column(0)
        
    def popup_item_menu(self, treeview, event):
        """
        Handler for right-click event on items in the list.
        
        """
        if event.button == 3:
            # Get the coordinates of the click
            x, y = int(event.x), int(event.y)
            time = event.time
            # Work out what was clicked
            pthinfo = treeview.get_path_at_pos(x, y)
            # Only do something if an item was clicked on
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                # Show the context menu
                self.context_menu.popup(None, None, None, event.button, time)
                return True
        return False
        
    def show_derivation_window(self, widget):
        """
        Handler for selecting the derivation window menu item.
        
        """
        # Get the selected sign from the list
        sign = self.get_selected_sign()
        if hasattr(sign, 'derivation_trace') and sign.derivation_trace is not None:
            dt_window = DerivationTraceWindow(sign)
        else:
            # No DT available
            md = gtk.MessageDialog(self, buttons=gtk.BUTTONS_OK, \
                    message_format="The sign has no derivation trace.\n\n"\
                        "This may be because no derivation "\
                        "traces are being stored during parsing. Try the "\
                        "-d option.")
            md.run()
            md.destroy()
        
    def get_selected_sign(self):
        """
        @return: the sign represented by the value currently selected 
            in the list, or None is none is selected.
        
        """
        index,column = self.treeview.get_cursor()
        if index is None:
            # Nothing selected
            return None
        else:
            # index is a tuple, because TreeView can display trees
            # We only ever have one item, because we only display lists
            return self.signs[index[0]]

class ChartInspectorWindow(gtk.Window):
    """
    A window that displays a summary of the chart and allows inspection 
    of it in greater detail.
    
    """
    """Class to create the cell inspector. May be overridden by subclasses."""
    CELL_INSPECTOR_IMPL = CellInspectorWindow
    
    def __init__(self, chart=None, input_strs=None, filename=None, *args, **kwargs):
        """
        Creates a new ChartInspectorWindow.
        Either chart or filename must be given. If filename is given, 
        the chart will be loaded from a pickled representation in the 
        named file and this will be reloaded when the chart is updated.
        
        @type chart: Chart
        @param chart: the chart to inspect
        @type input_strs: list of strings
        @param input_strs: a string representation of the input, for 
            display.
        @type filename: string
        @param filename: the location of a file to load the chart from.
        
        """
        self.filename = filename
        if filename is not None:
            self._load_chart_file()
        else:
            self.chart = chart
        self._chart_matrix = None
        # Matrix to note whether a cell's highlighted
        self.highlighted = [[False for i in range(len(row))] for row in self.chart._table]
        self.update_chart()
        
        # Init the window
        super(ChartInspectorWindow, self).__init__(gtk.WINDOW_TOPLEVEL, *args, **kwargs)
        
        # Setup the displayed window
        self.set_border_width(5)
        self.set_title("Chart inspector - The Jazz Parser")
        
        vbox = gtk.VBox(spacing=5)
        self.add(vbox)
        # Display the input string if one was given
        if input_strs is not None:
            input_label = gtk.Label()
            input_label.set_markup("<span font-family=\"monospace\">Input: %s</span>" % " ".join(input_strs))
            # Give it a horizontal scrollbar
            input_scroll = gtk.ScrolledWindow()
            input_scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_NEVER)
            input_scroll.add_with_viewport(input_label)
            vbox.pack_start(input_scroll, expand=False)
        #### The table itself
        # Add scrollbars
        self.scroll_container = gtk.ScrolledWindow()
        self.scroll_container.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        vbox.pack_start(self.scroll_container, expand=True)
        # Put a table in the window to display the chart summary in
        chart_size = self.chart.size
        self.table = gtk.Table(rows=chart_size+1, columns=chart_size+1, homogeneous=True)
        self.table.set_col_spacings(5)
        self.table.set_row_spacings(5)
        self.scroll_container.add_with_viewport(self.table)
        
        # Add labels to the axes of the table
        # "From" down the side
        for i in range(chart_size):
            label = gtk.Label()
            label.set_markup("<b>%d</b>" % i)
            self.table.attach(label, 0, 1, i+1, i+2, xoptions=0, yoptions=0)
            label.show()
        # "To" along the top
        for i in range(chart_size):
            label = gtk.Label()
            label.set_markup("<b>%d</b>" % (i+1))
            self.table.attach(label, i+1, i+2, 0, 1, xoptions=0, yoptions=0)
            label.show()
        
        def _get_inspect_cell(x, y):
            # This creates a closure for x and y to use in the click callback
            def _inspect_cell(widget, event):
                cell_window = self.CELL_INSPECTOR_IMPL(self._chart_matrix[x][y-x], x, y+1)
                cell_window.show()
            return _inspect_cell
            
        # Put a label in every cell whose text we can set
        self._label_matrix = []
        for i in range(chart_size):
            lab_row = []
            for j in range(chart_size):
                # Create an empty label in the table cell
                label = gtk.Label()
                # We need to put it in an EventBox so it can receive click events
                box = gtk.EventBox()
                box.add(label)
                # Put the label in the tabular layout
                self.table.attach(box, j+1, j+2, i+1, i+2, xoptions=0, yoptions=0)
                label.show()
                box.show()
                box.set_events(gtk.gdk.BUTTON_PRESS_MASK)
                if i <= j:
                    # Only do these things for cells that correspond to actual edges
                    # Create a tooltip for this label so we can easily work out what it is
                    label.set_tooltip_text("(%d,%d)" % (i,j+1))
                    # Bind the click event to a callback to show the cell inspector
                    box.connect('button_press_event', _get_inspect_cell(i, j))
                # Keep a ref to it in the matrix
                lab_row.append(label)
            self._label_matrix.append(lab_row)
            
        self.length = chart_size
            
        # Make the window nice and big
        self.set_default_size(600,600)
        
        # Bind key presses
        def _key_pressed(widget, event):
            keyname = gtk.gdk.keyval_name(event.keyval)
            if keyname == "F5":
                # Update and redraw the chart
                self.draw_chart()
                return True
            else:
                # Fall through to any other handlers
                return False
        self.connect('key_press_event', _key_pressed)
        
        # Draw the chart as it currently stands
        self.draw_chart(update=False)
        
        # Stop PyGtk when the window is closed
        self.connect("destroy", self.kill)
        
        # Show everything
        self.show_all()
        
    def _load_chart_file(self):
        from .chart import load_chart
        # Load the pickled chart object
        self.chart = load_chart(self.filename)
        
    def __set_cell_contents(self, row, col, value):
        """Put a string in the cell with the given coordinate."""
        if row >= self.length or col >= self.length:
            # Outside the bounds of the table
            raise IndexError, "tried to put something in (%d,%d) of a "\
                "chart of size %d" % (row,col,self.length)
        value = str(value)
        # Apply any formatting we want
        if value == "0":
            # Make 0s grey
            value = '<span foreground="#999">%s</span>' % value
        # Set the text of the label in that cell
        self._label_matrix[row][col].set_markup(value)
        
    def __set_cell_color(self, row, col, color):
        """Sets the text of a cell to a particular colour."""
        self._label_matrix[row][col].modify_fg(gtk.STATE_NORMAL, color)
    
    def update_chart(self):
        """
        Recopies the information needed from the chart object into the 
        local cache. If the chart was loaded from a file, reloads the 
        file first.
        
        """
        if self.filename is not None:
            # Reload the chart from the file
            self._load_chart_file()
        # This is hacky
        # If the chart's being updated and this falls flat, just try again.
        # A better solution would be to lock the chart.
        # This rarely happens, so maybe not worth locking
        self._old_chart_matrix = self._chart_matrix
        while True:
            try:
                # Refresh the copy of the chart that we're using to draw
                # Take a copy of the state of the chart
                # No need to copy the signs themselves as they won't change
                self._chart_matrix = [[copy.copy(hash_set.values()) for hash_set in row] for row in self.chart._table]
            except RuntimeError:
                # We probably caught the chart at a bad time: try again
                print "WARNING: thread error while copying chart"
                continue
            else:
                break
                
        # Check which values have changed and flag them as highlighted
        if self._old_chart_matrix is not None:
            for i in range(len(self._chart_matrix)):
                for j in range(len(self._chart_matrix[i])):
                    self.highlighted[i][j] = \
                        (self._old_chart_matrix[i][j] != self._chart_matrix[i][j])
        
    def draw_chart(self, update=True):
        """
        Refresh the values in the displayed table representing the chart.
        By default this will update the chart representation. If you 
        just want to draw and not update first, set update=False.
        
        """
        if update:
            self.update_chart()
        # Colours to use below
        highlighted = gtk.gdk.color_parse("red")
        unhighlighted = gtk.gdk.color_parse("black")
        
        # Put the number of signs in each cell
        for from_node in range(self.length):
            for to_node in range(from_node+1, self.length+1):
                new_value = self._chart_matrix[from_node][to_node-from_node-1]
                # Only update the label if the value's changed (it's time-consuming)
                if self._old_chart_matrix is None or \
                        new_value != self._old_chart_matrix[from_node][to_node-from_node-1]:
                    self.__set_cell_contents(from_node, to_node-1, \
                            "%d" % len(new_value) )
                # Update the colour depending on whether it's highlighted
                if self.highlighted[from_node][to_node-from_node-1]:
                    self.__set_cell_color(from_node, to_node-1, highlighted)
                else:
                    self.__set_cell_color(from_node, to_node-1, unhighlighted)
    
    def kill(self, obj=None):
        """
        Stops the thread in which the inspector is running.
        
        """
        gtk.main_quit()
        
class DerivationTraceWindow(gtk.Window):
    """
    Simple window to spew out a derivation trace for a sign in the 
    chart. Just gives a space to display the plain text representation - 
    no need to do anything more fancy.
    
    """
    def __init__(self, sign, *args, **kwargs):
        super(DerivationTraceWindow, self).__init__(*args, **kwargs)
        
        # Set up the appearance of the windw
        self.set_modal(True)
        self.set_default_size(600, 600)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_title("Derivation trace - The Jazz Parser")
        
        # Put a text area in the window in scrollbars
        scroller = gtk.ScrolledWindow()
        scroller.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.add(scroller)
        text_view = gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        scroller.add_with_viewport(text_view)
        # Set the font in which the text is displayed
        font = pango.FontDescription("monospace")
        text_view.modify_font(font)
        
        # Put the derivation trace in the buffer
        text_view.get_buffer().set_text(str(sign.derivation_trace))
        
        self.show_all()
    
class ChartInspectorThread(Thread):
    """
    A thread to display a window at the same time as parsing is going 
    on. The window contains information about the chart. This is taken 
    from a copy of the chart, so it will only update when the user 
    requests an update.
    
    The thread will end when the window is closed.
    
    """
    """The class to use to create the inspector window. May be overridden by subclasses."""
    INSPECTOR_IMPL = ChartInspectorWindow
    
    def __init__(self, chart, input_strs=None, *args, **kwargs):
        super(ChartInspectorThread, self).__init__(*args, **kwargs)
        self.chart = chart
        # Create a window
        # This will be displayed immediately
        # Note that it gets displayed from the main thread, but future
        #  interactions take place in the new thread
        self.window = self.INSPECTOR_IMPL(self.chart, input_strs=input_strs)
        
    def run(self):
        # Prepare Gtk to run neatly in a thread and not hold the global lock
        gtk.gdk.threads_init()
        gobject.threads_init()
        # Go to the main loop, which will only end if the window's closed
        gtk.main()
        
def inspect_chart_file(filename, inspector_cls=None):
    """
    Load a pickled chart from a file and display the chart inspector 
    to examine it.
    
    @type filename: string
    @param filename: the filename of the file to load
    @type inspector_cls: class
    @param inspector_cls: the class of the inspector window to load the 
        chart in. By default, uses the CKY inspector, but you may want 
        to use subclasses.
    
    """
    # Start up the chart inspector
    if inspector_cls is None:
        inspector = ChartInspectorWindow(filename=filename)
    else:
        inspector = inspector_cls(filename=filename)
    gtk.main()
