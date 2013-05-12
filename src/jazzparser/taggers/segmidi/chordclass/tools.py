"""Interactive shell tools for the chordclass tagger.

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

class StateGridTool(Tool):
    name = "State grid displayer"
    commands = [ "states" ]
    usage = ('states [<time>]', "Show the most probable states for the given timestep, or all timesteps")
    help = """\
Displays the most probable states from the HMM decoding.
"""
    
    def run(self, args, state):
        top_tags = state.tagger.top_tags
        
        if len(args):
            time = int(args[0])
            timesteps = [(time, top_tags[time])]
        else:
            timesteps = enumerate(top_tags)
        
        # Print out the states for each timestep
        for time, tags in timesteps:
            print "### Time %d ###" % time
            for (prob, (schema, root)) in tags:
                print " %s, %d   (%f)" % (schema, root, prob)
            print
