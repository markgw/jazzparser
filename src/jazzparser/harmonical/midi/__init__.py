from __future__ import absolute_import
"""Tuned MIDI file generation to reflect just intonation.

Uses the MIDI processing library by Giles Hall that I've worked on to 
improve and fix bugs.

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

import math
# Can't by default import from midi, because this module's name clashes
# But absolute_import forces absolute paths to be resolved unless .s are used
from midi import single_note_tuning_event, NoteOnEvent, NoteOffEvent
from jazzparser.utils.tonalspace import coordinate_to_et, \
                        cents_to_pitch_ratio, pitch_ratio_to_cents
from ..tones import tonal_space_pitch

def tonal_space_note_events(coord, start, duration, origin_note=60, velocity=100):
    """
    Creates the MIDI events needed to play the given tonal space 
    coordinate. These will be a single-note tuning event (to retune 
    the appropriate note), a note-on event and a note-off event.
    
    @type coord: tuple
    @param coord: 3D tonal space coordinate
    @type start: int
    @param start: start time of note in ticks
    @type duration: int
    @param duration: length of the note in ticks
    @type origin_note: int
    @param origin_note: midi note number to assume the origin of the 
      tonal space is equal to in pitch (default 60, middle C)
    @rtype: tuple
    @return: (tuning event, note on event, note off event)
    
    """
    # Work out what note to retune for the root and how
    change = tonal_space_tuning(coord)
    note = change[0]
    
    # Create the tuning event
    tuning = single_note_tuning_event([change])
    tuning.tick = start
    # Play the note
    note_on = NoteOnEvent()
    note_on.pitch = note
    note_on.velocity = velocity
    note_on.tick = start
    # Stop the note
    note_off = NoteOffEvent()
    note_off.pitch = note
    note_off.tick = start+duration
    note_off.velocity = velocity
    
    return (tuning, note_on, note_off)

def tonal_space_tuning(coord, origin_note=60):
    """
    Produces MIDI single note tuning event data that will retune the 
    equal temperament equivalent note of the given coordinate to the 
    true pitch of that coordinate. This can, for example, be placed in 
    a stream directly before a note-on event for that note to play 
    the tonal space point.
    
    If the resulting note number is outside the range of midi notes 
    (0-127), it is shifted to the nearest octave that is within the 
    range.
    
    @type origin_note: int
    @param origin_note: midi note number to assume the origin of the 
      tonal space is equal to in pitch (default 60, middle C)
    @rtype: tuple
    @return: (note,semitone,cents), where note is the note to be tuned, 
      and semitone and cents between them define the pitch to tune to.
      This can be used as note change data for a midi single note 
      tuning event.
    
    """
    note = tonal_space_et_note(coord, valid_note=True, origin_note=origin_note)
    # Now work out how to tune this note to the desired pitch
    origin_pitch = 440.0 * cents_to_pitch_ratio((origin_note-69)*100)
    freq = origin_pitch * tonal_space_pitch(coord)
    # First get a base semitone
    semitone = frequency_note_number_floor(freq)
    # Get the number of cents the frequency is above this note
    cents_above = pitch_ratio_to_cents(freq/et_note_frequency(semitone))
    return (note,semitone,cents_above)

def frequency_note_number_floor(freq):
    """
    Given a float frequency, returns the midi note number that 
    represents to nearest ET note below this frequency.
    
    """
    # Calculate the interval between this freq and the A above middle C
    #  in cents
    cents_from_a = pitch_ratio_to_cents(float(freq) / 440.0)
    # Number of semitones above midi note 0
    above_zero = (cents_from_a/100.0) + 69.0
    return int(math.floor(above_zero))

def tonal_space_et_note(coord, valid_note=False, origin_note=60):
    """
    Returns the MIDI note number of the note to which equal temperament 
    maps the given 3D tonal space coordinate.
    
    @type valid_note: bool
    @param valid_note: if True, permits only valid MIDI notes (i.e. 
      in range 0-127). If the true note is outside this range, returns 
      the note in the nearest octave that is in the range
    @type origin_note: int
    @param origin_note: midi note number to assume the origin of the 
      tonal space is equal to in pitch (default 60, middle C)
    
    """
    # Work out the ET midi note number for this point
    note_number = origin_note + coordinate_to_et(coord)
    if valid_note:
        # Make sure it's a valid MIDI note number
        if note_number < 0:
            # Bring up to the lowest octave
            note_number = note_number % 12
        elif note_number > 127:
            # Bring down to the top octave
            chrom_number = note_number % 12
            if chrom_number <= 7:
                note_number = 120 + chrom_number
            else:
                note_number = 108 + chrom_number
    return note_number

def et_note_frequency(note):
    """
    Calculates the frequency in Hz of the given MIDI note number, assuming 
    equal temperament and 440Hz as the A above middle C.
    
    """
    # Work out the pitch ratio between this note and middle A
    ratio = cents_to_pitch_ratio(100.0 * (note - 57))
    return 220.0 * ratio
