"""
generate_tagged_input.py

**************
Note: you probably want to use generate_model_data, rather than this 
script. It generates several kinds of C&C model data, but tags 
observations rather than chords.
**************

Generate a file with chord sequences (one per line) tagged in the 
C&C suppertagger input style.
"""

import sys
from optparse import OptionParser
from apps.sequences.models import ChordSequence
from apps.sequences.utils import get_chord_list_from_sequence

    
def main():
    parser = OptionParser(usage='%prog [options] <out-file>')
    options, arguments = parser.parse_args()
    
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify an output file as the first argument"
        sys.exit(1)
    filename = arguments[0]
    
    file_lines = []
    def _format_chord(chord):
        return "%s|%s" % (chord.jazz_parser_input, chord.category)
    
    for sequence in ChordSequence.objects.filter(analysis_omitted=False):
        # The chord sequence
        chord_list = [_format_chord(chord) for chord in sequence.iterator()]
        current_line = " ".join(chord_list)
        
        # Put this sequence into the file
        file_lines.append(current_line)
        
    file = open(filename, 'w')
    file.write(u'\n'.join(file_lines).encode('utf-8'))
    file.close()
    sys.exit(0)
    
if __name__ == "__main__":
    main()

