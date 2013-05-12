#!/usr/bin/env ../jazzshell
"""
Loads a pickled representation of a chart from a file and displays it 
in the grahpical chart inspector.

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

from optparse import OptionParser
from jazzparser.parsers.cky.inspector import inspect_chart_file, ChartInspectorWindow
from jazzparser.parsers.tagrank.inspector import TagRankChartInspectorWindow

INSPECTORS = {
    'cky' : ChartInspectorWindow,
    'tagrank' : TagRankChartInspectorWindow,
}

def main():
    usage = "%prog [options] <chart-file>"
    parser = OptionParser(usage=usage)
    parser.add_option("-i", "--inspector", dest="inspector", action="store", help="select a non-default inspector type. Default is the standard cky inspector. Possible values: %s" % ", ".join(INSPECTORS.keys()))
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "Specify a file to read the chart from"
        sys.exit(1)
        
    if options.inspector is not None:
        inspector = INSPECTORS[options.inspector]
    else:
        inspector = None
    
    inspect_chart_file(arguments[0], inspector_cls=inspector)

if __name__ == "__main__":
    main()
