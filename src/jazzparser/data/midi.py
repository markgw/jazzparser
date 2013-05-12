from __future__ import absolute_import
"""Processing of MIDI data.

Tools for processing MIDI data. This makes use of the L{midi} library, 
but is not itself generic MIDI processing code (or else I'd add it to 
the library).

This has nothing to do with tonal space MIDI generation. For that, 
see L{jazzparser.harmonical.midi}.

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

from midi import MarkerEvent, LyricsEvent, TextEvent, CuePointEvent

class SequenceMidiAlignment(object):
	"""
	Specification of parameters to align a chord sequence with a 
	MIDI file. This includes things like where repeats should occur 
	in the chord sequence and how many beats to each MIDI beat, 
	so that the chords end up at the right place in the music.
	
	Aligns a L{ChordSequence<jazzparser.data.db_mirrors.ChordSequence>}
	with a L{midi.EventStream}.
	
	"""
	def __init__(self):
		self.midi_beats_per_beat = 1
		"""
		Number of beats in the MIDI file to align with each chord 
		sequence beat. Use negative numbers (<-1) to specify reciprocals
		(i.e. -4 -> 1/4).
		"""
		self.sequence_start = 0
		"""
		Number of MIDI ticks between the first note-on event in the 
		MIDI file and where the chord sequence starts.
		"""
		self.repeat_spans = []
		"""
		Definitions of repeats. Given as (start,end,count). The first 
		I{count} times the I{end}th chord is finished, the 
		sequence will return to the I{start}th chord. Repeats with the 
		same end point will be used in the order they occur in this list.
		
		@note: Counts for inner repeats will not be reset in the outer 
		loop of nested spans.
		"""
	
	def align(self, sequence, mid, lyrics=False):
		"""
		Aligns the sequence with the midi file and adds lyric events 
		into the midi data to indicate where the chords occur.
		This ought to function like a karaoke midi file, showing the 
		chords as the occur.
		
		Note that this modifies the midi sequence in place.
		
		@type lyrics: bool
		@param lyrics: use lyrics events the mark the chords. By default
			uses marker events, which are more appropriate but may not 
			be supported by your player.
		@type sequence: L{ChordSequence<jazzparser.data.db_mirrors.ChordSequence>}
		@param sequence: the chord sequence to take chords from
		@type mid: L{midi.EventStream}
		@param sequence: input midi sequence
		@rtype: L{midi.EventStream}
		@return: the original midi sequence with text added in for the 
			chords.
		
		"""
		if self.midi_beats_per_beat > 0:
			ticks_per_seq_beat = self.midi_beats_per_beat * mid.resolution
		elif self.midi_beats_per_beat < -1:
			ticks_per_seq_beat = mid.resolution / abs(self.midi_beats_per_beat)
		else:
			raise ValueError, "midi_beats_per_beat should be >0 or <-1: "\
				"not %s" % self.midi_beats_per_beat
		
		# Look for the default start time for the chords
		noteon = first_note_on(mid)
		if noteon is None:
			# No note-on events found at all: we'll start at tick 0, 
			#  but the result's going to be nonsensical
			tick = 0
		else:
			# Shift our start point by the requested number of ticks
			tick = noteon.tick + self.sequence_start
			
		cursor = 0
		# Keep track of what repeats we've got to do and where they go
		repeats = {}
		for start,end,count in self.repeat_spans:
			if start >= end:
				raise MidiAlignmentError, "nonsensical repeat span "\
					"ends before it starts: (%d,%d,%d)" % (start,end,count)
			repeats.setdefault(end, []).extend([start] * count)
		
		mid.curtrack = 0
		sequence = list(sequence.iterator())
		while cursor < len(sequence):
			# Get the chord for the current cursor from the sequence
			chord = sequence[cursor]
			# Add a text event to say what the chord is
			if lyrics:
				ev = LyricsEvent()
				ev.data = "%s " % chord
			else:
				ev = MarkerEvent()
				ev.data = "<%d> %s" % (cursor,chord)
			ev.tick = tick
			mid.add_event(ev)
			
			# Move the midi tick cursor on
			tick += chord.duration * ticks_per_seq_beat
			if cursor in repeats:
				# A repeat span ends at this chord: go back to the start
				new_cursor = repeats[cursor].pop(0)
				if len(repeats[cursor]) == 0:
					# No more spans with this end point
					del repeats[cursor]
				cursor = new_cursor
			else:
				# No repeats: just move to the next chord
				cursor += 1
		mid.timesort()
		return mid

def first_note_on(mid):
	"""
	Returns the earliest note-on event in the MIDI file 
	(L{midi.EventStream}). If no note-on events are found, returns 
	None.
	
	"""
	from midi import NoteOnEvent
	
	evs = sorted(mid.trackpool)
	for ev in evs:
		if isinstance(ev, NoteOnEvent):
			return ev
	return None

class MidiAlignmentError(Exception):
	pass
