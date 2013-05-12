from __future__ import absolute_import
"""Midi processing for midi chord labeler.

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

from midi import NoteOnEvent
 
def midi_to_emission_stream(segmidi, remove_empty=True, unique_notes=False):
    """
    Get a list of emissions from the midi stream's note on events.
    
    Returns a 2-tuple of the list of emissions and their 
    corresponding start times in midi ticks.
    
    @type segmidi: L{jazzparser.data.input.SegmentedMidiInput}
    @param segmidi: midi input
    @type remove_empty: bool
    @param remove_empty: remove any chunks that have no observations in them 
        (default True)
    
    """
    chunks = []
    start_times = []
    tick_unit = segmidi.tick_unit
    
    for segment in segmidi:
        segment_start = segment.segment_start
        start_times.append(segment_start)
        note_ons = [ev for ev in segment.trackpool if isinstance(ev, NoteOnEvent)]
        
        # Produce an observation for every event
        chunk = []
        for ev in note_ons:
            pc = ev.pitch % 12
            chunk.append(pc)
        chunks.append(chunk)
        
    # Get rid of duplicate values in the chunks (octaves)
    if unique_notes:
        chunks = [list(set(c)) for c in chunks]
    if remove_empty:
        # Remove chunks that have no observations in them
        chunks = [ems for ems in chunks if len(ems) > 0]
    chunks_times = zip(chunks, start_times)
    
    # Return a tuple of the chunks and the start times
    return zip(*chunks_times)

