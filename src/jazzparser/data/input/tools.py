"""Shell tools relating to input data types.

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
from jazzparser.shell import ShellError

class InputTool(Tool):
    name = "Input lister"
    commands = ["input"]
    usage = ("input", "show the input data object")
    help = """\
Very simple tool to display the input data. It doesn't do anything fancy to 
output the contents of the data, but just prints out the data object's 
str.
"""
    
    def run(self, args, state):
        print str(state.input_data)


class PlayMidiChunksTool(Tool):
    name = "Midi chunk player"
    commands = ["play"]
    usage = ("play", "play the MIDI input chunk by chunk")
    help = """\
Input tool specially for segmented MIDI input. Will play the input chunk by 
chunk. Use a keyboard interrupt (Ctrl+C) to stop playback.
"""
    
    def run(self, args, state):
        from jazzparser.data.input import SegmentedMidiInput
        if state.input_data is None or type(state.input_data) != SegmentedMidiInput:
            raise ShellError, "input is not playable"
        
        if len(args) > 0:
            chunk = int(args[0])
        else:
            chunk = None
        
        PlayMidiChunksTool.play_segmidi(state.input_data, chunk=chunk)
        
    @staticmethod
    def play_segmidi(segmidi, chunk=None):
        from jazzparser.utils.midi import play_stream
        # Select an individual chunk if a number is given
        if chunk is None:
            strms = enumerate(segmidi)
        else:
            strms = [(chunk, segmidi[chunk])]
        
        try:
            for i,strm in strms:
                print "Playing chunk %d (%d events)" % (i, len(strm.trackpool))
                play_stream(strm, block=True)
        except KeyboardInterrupt:
            print "Stopping playback"

class PlayBulkMidiChunksTool(Tool):
    name = "Midi chunk player (bulk)"
    commands = ["play"]
    usage = ("play [<input number> [<chunk number>]]", "play the numbered MIDI input (the first by default)")
    help = """\
Input tool specially for segmented MIDI input, bulk input version.

Will play the input chunk by chunk. Use a keyboard interrupt (Ctrl+C) to stop 
playback.
"""
    
    def run(self, args, state):
        from jazzparser.data.input import SegmentedMidiBulkInput
        
        if len(args) == 0:
            inputno = 0
        else:
            try:
                inputno = int(args[0])
            except ValueError:
                raise ShellError, "input number must be an integer"
        
        # Check we have appropriate input
        if state.input_data is None or type(state.input_data) != SegmentedMidiBulkInput:
            raise ShellError, "input is not playable"
            
        if len(args) == 2:
            chunk = int(args[1])
        else:
            chunk = None
        
        segmidi = state.input_data[inputno]
        PlayMidiChunksTool.play_segmidi(segmidi, chunk=chunk)

class PrintMidiChunksTool(Tool):
    name = "Midi chunk printer"
    commands = ["chunk"]
    usage = ("chunk [<chunk>]", "print out the events in chunk <chunk>, or all chunks")
    help = """\
Displays all the MIDI events in a chunk of the input, or all the chunks.
"""
    
    def run(self, args, state):
        input_data = state.input_data
        if len(args):
            chunks = [int(args[0])]
        else:
            chunks = range(len(input_data))
        
        # Print each chunk
        for chunkno in chunks:
            print "### Chunk %d: ###" % chunkno
            print "\n".join([str(ev) for ev in sorted(input_data[chunkno].trackpool)])
