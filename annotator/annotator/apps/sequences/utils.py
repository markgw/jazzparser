
def _chord_list(chord):
    chord_list = [chord.id]
    if chord.next is not None:
        chord_list += _chord_list(chord.next)
    return chord_list
    
def get_chord_list_from_sequence(seq):
    if seq.first_chord is not None:
        return _chord_list(seq.first_chord)
    else:
        return []

class SequenceMidiAlignmentParams(object):
    """
    Specification of parameters to align a chord sequence with a 
    MIDI file. This includes things like where repeats should occur 
    in the chord sequence and how many beats to each MIDI beat, 
    so that the chords end up at the right place in the music.
    
    This does the same thing as 
    L{jazzparser.data.midi.SequenceMidiAlignment}, but acts on and 
    returns database models.
    
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
        Number of MIDI ticks into the file where the chord sequence 
        starts.
        
        @note: This is different to the version in jazzparser.data.midi
        """
        self.repeat_spans = []
        """
        Definitions of repeats. Given as (start,end,count). The first 
        I{count-1} times the I{end}th chord is finished, the 
        sequence will return to the I{start}th chord. Repeats with the 
        same end point will be used in the order they occur in this list.
        
        Note that, according to this definition, a repeat span with 
        count 1 does nothing. The count is the number of times the 
        passage is played. Count 0 spans are also ignored.
        
        @note: Counts for inner repeats will not be reset in the outer 
        loop of nested spans.
        """
        self.gaps = []
        """
        Definitions of positions and lengths of gaps in the sequence.
        Given as (chord,i,beats). Once the I{chord}th chord has been 
        played for the I{i}th time, a gap of I{beats} beats will be 
        inserted before the next chord is played.
        
        """
    
    def align(self, midi_data):
        """
        Aligns the sequence with the midi file and produces 
        MidiChordAlignment objects.
        
        @type mid: L{apps.sequences.models.MidiData}
        @param sequence: input midi sequence
        @rtype: list of L{<apps.sequences.models.MidiChordAlignment>alignments}
        @return: the alignment model instances for the alignment. These 
            are unsaved. Save them to add them to the database.
        
        """
        from apps.sequences.models import MidiChordAlignment
        
        sequence = midi_data.sequence
        mid = midi_data.midi_stream
        
        if self.midi_beats_per_beat > 0:
            ticks_per_seq_beat = self.midi_beats_per_beat * mid.resolution
        elif self.midi_beats_per_beat < -1:
            ticks_per_seq_beat = mid.resolution / abs(self.midi_beats_per_beat)
            print ticks_per_seq_beat
        else:
            raise ValueError, "midi_beats_per_beat should be >0 or <-1: "\
                "not %s" % self.midi_beats_per_beat
        
        # Shift our start point by the requested number of ticks
        tick = self.sequence_start
            
        cursor = 0
        # Keep track of what repeats we've got to do and where they go
        repeats = {}
        for start,end,count in self.repeat_spans:
            if start >= end:
                raise MidiAlignmentError, "nonsensical repeat span "\
                    "ends before it starts: (%d,%d,%d)" % (start,end,count)
            if count > 1:
                repeats.setdefault(end, []).extend([start] * (count-1))
        # Keep track of when the gaps are coming up
        gaps = {}
        for (chord,i,beats) in self.gaps:
            if i > 0 and beats > 0:
                gaps.setdefault(chord, []).append((i,beats))
        
        sequence = list(sequence.iterator())
        alignments = []
        while cursor < len(sequence):
            # Get the chord for the current cursor from the sequence
            chord = sequence[cursor]
            
            # Create an alignment model for this chord at this time
            alignment = MidiChordAlignment()
            alignment.chord = chord
            alignment.midi = midi_data
            alignment.start = tick
            
            # Move the midi tick cursor on
            tick += chord.duration * ticks_per_seq_beat
            
            alignment.end = tick
            alignments.append(alignment)
            
            # Check whether we're supposed to insert a gap after this chord
            if cursor in gaps:
                # Look for any gaps that only needed that chord 1 more time
                gap_now = sum([beats for (i,beats) in gaps[cursor] if i == 1], 0)
                # Reduce the count of occurrences needed for all other gaps
                gaps[cursor] = [(i-1,beats) for (i,beats) in gaps[cursor] if i != 1]
                # Move on the timer to insert a gap
                tick += gap_now * ticks_per_seq_beat
            
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
        return alignments

def first_note_on(mid):
    """
    Returns the earliest note-on event in the MIDI file 
    (L{midi.EventSequence}). If no note-on events are found, returns 
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
    
