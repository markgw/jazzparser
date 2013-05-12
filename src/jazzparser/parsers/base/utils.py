"""Utils for chart-related processing

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

class SpanCombiner(object):
    """
    For various purposes, we want to combine adjacent identical spanning 
    edges into one before adding them to the chart. This class makes it 
    easy to keep track of what additional edges should be added when a 
    new edges is added to do this.
    
    Use this by adding edges to this combiner in the order they'd get added 
    to the main chart (from the lexicon). L{combine_edge} returns the additional 
    spans that should be added along with this edge (with the same 
    category). We assume that those additional edges were added - 
    they get added to the combiner for future reference.
    
    """
    def __init__(self):
        self.edges = []
        self._edges_by_start = {}
        self._edges_by_end = {}
        self.edge_properties = {}
        
    def add_edge(self, edge, properties=None):
        self.edges.append(edge)
        self._edges_by_start.setdefault(edge[0], []).append(edge)
        self._edges_by_end.setdefault(edge[1], []).append(edge)
        self.edge_properties[edge] = properties
        
    def combine_edge(self, edge, 
                     properties=None, 
                     prop_combiner=lambda x:None):
        start,end,label = edge
        self.add_edge(edge, properties=properties)
        
        new_edges = []
        # Look for edges that combine with this at the beginning
        start_nodes = []
        for (pre_start, pre_end, pre_label) in self._edges_by_end.get(start, []):
            if pre_label == label:
                # Match: combine these
                pre_props = self.edge_properties[(pre_start,pre_end,label)]
                start_nodes.append((pre_start, pre_props))
                new_edges.append((pre_start, end, 
                                    prop_combiner((pre_props,properties)) ))
        
        # Look for edges that combine at the end
        end_nodes = []
        for (post_start, post_end, post_label) in self._edges_by_start.get(end, []):
            if post_label == label:
                # Match: combine
                post_props = self.edge_properties[(post_start,post_end,label)]
                end_nodes.append((post_end,post_props))
                new_edges.append((start, post_end,
                                    prop_combiner((properties,post_props)) ))
        
        # If we match at the start and end, we can also combine all three 
        #  into one big edge
        for (pre_start,pre_props) in start_nodes:
            for (post_end,post_props) in end_nodes:
                new_edges.append((pre_start, post_end,
                            prop_combiner((pre_props,properties,post_props)) ))
        
        # Add all of these new ones for future reference
        for (nstart, nend, props) in new_edges:
            self.add_edge((nstart, nend, label), properties=props)
        
        return [(start,end) for (start,end,props) in new_edges]
    
