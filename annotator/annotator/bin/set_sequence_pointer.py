## I've just added a sequence foreign key to the chord model.
## This goes through all the chords in the sequences and sets their 
## sequence fk to point to the correct sequence.

import sys

from apps.sequences.models import Chord, ChordSequence

def set_sequence_pointers():
    for sequence in ChordSequence.objects.all():
        print "Setting pointers on %s" % sequence.name
        chord = sequence.first_chord
        while chord is not None:
            chord.sequence = sequence
            chord.save()
            chord = chord.next
    print "Done all sequences"
    
def main():
    sys.exit(set_sequence_pointers())
    
if __name__ == "__main__":
    main()
