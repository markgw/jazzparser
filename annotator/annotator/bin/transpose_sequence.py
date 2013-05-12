"""
Transpose a whole chord sequence by transposing each of its chords.
Note: does not change the "key" text field of the sequence - do this 
yourself.
"""
import sys

from django.db.models import Count
from apps.sequences.models import ChordSequence

def transpose_sequence(id, semitones):
    try:
        sequence = ChordSequence.objects.get(id=id)
    except ChordSequence.DoesNotExist:
        print "Chord sequence with id %s does not exist" % id
        return 1
    print "Transposing chord sequence \"%s\" by %s semitones" % (sequence.name, semitones)
    chord = sequence.first_chord
    while chord is not None:
        chord.root = ((chord.root + semitones) % 12)
        chord.save()
        chord = chord.next
    print "Done"
    return 0
    
def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print "Please specify a chord sequence id and a number of semitones to tranpose by"
        sys.exit(1)
    id = int(args[0])
    semitones = int(args[1])
    sys.exit(transpose_sequence(id, semitones))
    
if __name__ == "__main__":
    main()
