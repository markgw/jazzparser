"""Interactive shell tools for the CKY parser.

This provides tools for the debugging shell that are specific to the 
CKY parser.

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

class ChartTool(Tool):
    """
    Tool for examining the chart's contents.
    """
    name = "Inspect CKY Chart"
    commands = ['chart']
    usage = ('chart [<x> [<y>]]', "show final chart. 'x' selects arcs starting from node x. 'x y' selects arc (x,y). Use x='summary' to see a short form of the whole chart.")
    help = """
Show part or all of the chart that was created during parsing.
With no arguments, the whole chart will be printed. Optionally a 
starting node may be given and only arcs starting at this node will 
be displayed. An end node may also be given and only signs on the arc 
between those two nodes will be displayed.
Sign indices are displayed with the entries. These are used to identify 
a particular sign for, for example, rule application.

If x='summary' (that is, the command 'chart summary'), the short 
form of the whole chart will be displayed - the form shown in progress 
reports.

See also:
  apply, for applying rules to the signs in the chart.
  ichart, for displaying the graphical chart inspector.
"""
    
    def run(self, args, state):
        chart = state.parser.chart
        if len(args) == 0:
            # Print the whole chart
            print "%s" % chart
        elif len(args) == 1:
            if args[0] == 'summary':
                print chart.summary
            else:
                # Print just the given row
                print "%s" % chart.to_string(rows=[int(args[0])])
        else:
            # Print just one cell
            print "%s" % chart.to_string(rows=[int(args[0])],cols=[int(args[1])])

class InteractiveChartTool(Tool):
    """
    Tool for examining the chart's contents.
    """
    name = "Graphically inspect CKY Chart"
    commands = ['ichart']
    usage = ('ichart', "show chart in the graphical chart inspector")
    help = """
Show the whole chart in the graphical chart inspector.

See also:
  chart, for print the contents of the chart.
"""
    
    def run(self, args, state):
        chart = state.parser.chart
        # We don't use chart.launch_inspector(), because that uses threading 
        #  and seems to cause a mess
        chart.launch_inspector(block=True)
