## A script to clean up any orphaned chords that aren't in a chord 
## sequence.

import sys

from apps.sequences.models import Chord, ChordSequence
from apps.sequences.utils import get_chord_list_from_sequence

def remove_orphaned_chords():
    # Compile a list of all chord ids that are in sequences
    used_chord_ids = set()
    for sequence in ChordSequence.objects.all():
        used_chord_ids |= set(get_chord_list_from_sequence(sequence))
    all_chord_ids = set( [v['id'] for v in Chord.objects.all().values('id')] )
    unused_chords = all_chord_ids - used_chord_ids
    if len(unused_chords) > 0:
        print "Deleting chords: %s" % ", ".join(["%s" % c for c in unused_chords])
        # Delete all these unused chords
        Chord.objects.filter(id__in=unused_chords).delete()
        print "Done"
    else:
        print "No unused chords to delete"
    return 0
    
def main():
    sys.exit(remove_orphaned_chords())
    
if __name__ == "__main__":
    main()
