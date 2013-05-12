"""
Computes the perplexity of a supertagger model, as perplexity per 
chord, over ever chord sequence in the database. 

Note that this data 
is usually the model's training data, so we're computing the model 
perplexity over the training set. This is bad, but at least gives 
us an initial upper bound on the perplexity.
"""
import sys, math
from optparse import OptionParser

from jazzparser.utils.tableprint import pprint_table
from jazzparser.taggers.loader import get_tagger
from jazzparser.grammar import Grammar

from apps.sequences.models import ChordSequence

from analysis_utils import sequence_entropy

DEFAULT_TAGGER = 'candc'
    
def main():
    parser = OptionParser()
    parser.add_option("-t", "--tagger", dest="tagger", action="store_true", help="The tagger component to use (full python path to the tagger class). Default: %s" % DEFAULT_TAGGER)
    options, arguments = parser.parse_args()
    
    if options.tagger is not None:
        tagger = options.tagger
    else:
        tagger = DEFAULT_TAGGER
    
    # Use the default grammar
    grammar = Grammar()
    tagger_class = get_tagger(tagger)
    
    total_entropy = 0.0
    total_chords = 0
    # Compile the data for displaying in a table
    data = []
    for sequence in ChordSequence.objects.filter(analysis_omitted=False):
        print "Analyzing entropy of model on %s" % sequence.name
        # Calculate the total word-level entropy of this sequence
        sequence_chords = list(sequence.iterator())
        entropy,sequence_length = sequence_entropy(sequence_chords, grammar, tagger_class)
        data.append( {
            'name' : sequence.name.encode('ascii', 'replace'),
            'entropy' : entropy,
            'length' : sequence_length,
            'entropy_per_chord' : (sequence_length!=0 and (entropy/sequence_length) or 0.0),
        })
        if sequence_length:
            total_entropy += entropy
            total_chords += sequence_length
    
    # Display a table of the results
    table_data = [['Sequence', 'Entropy', 'Chords', 'Entropy per chord']] + [
        [ d['name'], "%.4f" % d['entropy'], "%d" % d['length'], "%.4f" % d['entropy_per_chord'] ] 
            for d in data ]
    pprint_table(sys.stdout, table_data, [True, False, False, False])
    # Calculate the perplexity over the whole set
    perplexity = math.pow(2, total_entropy/total_chords)
    print "### Entropy per chord: %.4f" % (total_entropy/total_chords)
    print "### Perplexity = %.4f" % perplexity
    
if __name__ == "__main__":
    main()
