"""Interactive shell tools for a temporal semantics.

Any formalism that uses a temporal semantics (see temporal.py) may 
want to use the shell tools defined here.

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

from jazzparser.shell import tools

class TimeOutputTool(tools.Tool):
    """
    Toggles full time output.
    """
    name = "Time Output"
    commands = ['timeoutput']
    usage = ("timeoutput", "toggle output of times associated with every semantic object, "\
                                    "or just tonal denotations.")
    help = """
Toggles display of times in output. By default times are only displayed 
alongside semantic literals, but times are stored for other items in 
the semantics. If time output is turned on, times will be displayed for 
every semantic object that stores a time.

This will also cause the keys of the time assignments to be displayed in 
the form key:time. This is mainly for debugging: in general the times 
will be ordered by key, so you can assume that the ith time in each 
assignment has the same key.
"""
    
    def run(self, args, state):
        from jazzparser import settings
        if settings.OPTIONS.OUTPUT_ALL_TIMES:
            print "Turning time output off"
        else:
            print "Turning time output on"
        settings.OPTIONS.OUTPUT_ALL_TIMES = not settings.OPTIONS.OUTPUT_ALL_TIMES
