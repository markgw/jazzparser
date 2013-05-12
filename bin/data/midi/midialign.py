#!/usr/bin/env ../../jazzshell
import sys, os.path

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.data.midi import SequenceMidiAlignment

from midi import read_midifile, write_midifile
from optparse import OptionParser
    
def main():
    usage = "%prog [options] <seq-file>:<index> <midi-file> <midi-out>"
    description = "Aligns a chord sequence with a MIDI file and inserts "\
        "marker events into the MIDI data to mark where chord changes "\
        "are. Alignment parameters will be loaded from a file (not "\
        "implemented yet), but can be overridden using the script's "\
        "options."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("--mbpb", "--midi-beats-per-beat", dest="beats_per_beat", type="int", help="number of midi beats to align with a single sequence beat (see SequenceMidiAlignment.midi_beats_per_beat)")
    parser.add_option("--ss", "--sequence-start", dest="sequence_start", type="int", help="number of midi ticks after the first note-on event when the chord sequence begins (see SequenceMidiAlignment.sequence_start)")
    parser.add_option("--repeats", dest="repeats", help="repeat spans, in the form 'start_chord,end_chord,count', separated by semicolons (see SequenceMidiAlignment.repeat_spans)")
    parser.add_option("--lyrics", dest="lyrics", action="store_true", help="use lyrics events instead of marker events to mark the chords")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 3:
        print "You must specify a sequence file, midi file and output midi filename"
        sys.exit(1)
        
    # Get the chord sequence
    filename,__,index = arguments[0].partition(":")
    index = int(index)
    seq = SequenceIndex.from_file(filename).sequence_by_index(index)
    
    # Load the input midi data
    mid = read_midifile(arguments[1])
    
    outfile = arguments[2]
    
    # For now, just create a new default alignment
    # TODO: load the alignment parameters from a file or from the 
    #  sequence data itself
    alignment = SequenceMidiAlignment()
    
    # Override alignment parameters if options are given
    if options.beats_per_beat is not None:
        alignment.midi_beats_per_beat = options.beats_per_beat
    if options.sequence_start is not None:
        alignment.sequence_start = options.sequence_start
    if options.repeats is not None:
        repeats = []
        try:
            for string_triple in options.repeats.split(":"):
                start,end,count = string_triple.split(",")
                start,end,count = int(start), int(end), int(count)
                repeats.append((start,end,count))
        except:
            print "Error parsing repeat spans:"
            raise
        alignment.repeat_spans = repeats
    
    alignment.align(seq, mid, lyrics=options.lyrics)
    
    write_midifile(mid, outfile)
    
if __name__ == "__main__":
    main()
