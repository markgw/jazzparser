"""
generate_model_data.py

Generate a file that will be used as training data for a C&C model.
Various types of files can be generated.

I generated supertagging training data using the command:
./django-admin.py run annotator/bin/data/generate_model_data.py -c ../input/candc/test/chords.super
"""

import sys
from optparse import OptionParser
from apps.sequences.models import ChordSequence
from apps.sequences.utils import get_chord_list_from_sequence
from jazzparser.taggers.candc.utils import sequence_to_candc_pos, \
                    sequence_to_candc_chord_super, sequence_to_candc_super
    
def main():
    usage = "%prog [options] <out-file>"
    parser = OptionParser(usage=usage)
    parser.add_option("-p", "--pos", dest="pos", action="store_true", help="Generate POS tagger training data.")
    parser.add_option("-s", "--super", dest="super", action="store_true", help="Generate super-tagger training data (default)")
    parser.add_option("-c", "--chord-super", dest="chord_super", action="store_true", help="Generate super-tagger "\
                "training data in a combined chord/observation format. This is no good for C&C directly, but is "\
                "used by the Jazz Parser's C&C training interface.")
    options, arguments = parser.parse_args()
    
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify an output file as the first argument"
        sys.exit(1)
    filename = arguments[0]
    
    if options.pos:
        _seq_proc = sequence_to_candc_pos
    elif options.chord_super:
        _seq_proc = sequence_to_candc_chord_super
    else:
        _seq_proc = sequence_to_candc_super
            
    file = open(filename, 'w')
    
    for sequence in ChordSequence.objects.filter(analysis_omitted=False):
        # Put this sequence into the file
        file.write(_seq_proc(sequence).encode('utf-8'))
        
    file.close()
    sys.exit(0)
    
if __name__ == "__main__":
    main()

