"""Chart inspector for the tag rank parser.

Some small extensions to the CKY chart inspector for the tag rank 
parser.

See L{jazzparser.parsers.cky.inspector} for details.

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

from jazzparser.parsers.cky.inspector import ChartInspectorThread, \
                    ChartInspectorWindow, CellInspectorWindow
# Gtk version check already done in cky.inspector
import gtk, gobject

class TagRankCellInspectorWindow(CellInspectorWindow):
    def _create_column_data(self):
        """
        Override to add extra column to the cell inspector.
        
        """
        liststore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        # Add all the signs to the store
        for sign in reversed(sorted(self.signs, key=lambda s: s.probability)):
            liststore.append(["%f" % sign.probability, "%s" % sign])
        return liststore
            
    def _create_columns(self):
        """
        Override to add extra column.
        
        """
        # Add a column to the treeview to display the probabilities
        prob_column = gtk.TreeViewColumn("Probability")
        self.treeview.append_column(prob_column)
        # Render the probabilities as text
        prob_renderer = gtk.CellRendererText()
        prob_column.pack_start(prob_renderer, True)
        prob_column.add_attribute(prob_renderer, "text", 0)
        
        # Add the sign column as before
        sign_column = gtk.TreeViewColumn("Signs on edge (%d,%d)" % (self.from_node, self.to_node))
        self.treeview.append_column(sign_column)
        # Render the signs as text
        sign_renderer = gtk.CellRendererText()
        sign_renderer.set_property('family', 'monospace')
        sign_column.pack_start(sign_renderer, True)
        sign_column.add_attribute(sign_renderer, "text", 1)
        
        # Search signs by the main column
        self.treeview.set_search_column(1)
    
class TagRankChartInspectorWindow(ChartInspectorWindow):
    CELL_INSPECTOR_IMPL = TagRankCellInspectorWindow

class TagRankChartInspectorThread(ChartInspectorThread):
    INSPECTOR_IMPL = TagRankChartInspectorWindow
