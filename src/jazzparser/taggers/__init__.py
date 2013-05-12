"""Supertagger components."""
from tagger import Tagger, process_chord_input

TAGGERS = {
    'full' : ('full','Tagger'),                     # Full tagger: all signs with equal probability.
    'fail' : ('fail','Tagger'),                     # Fail tagger: no tags ever. For testing only.
    'candc' : ('candc','CandcMultiTagger'),         # C&C tagger: signs weighted by probabilities.
    'candc-best' : ('candc', 'CandcBestTagger'),    # C&C tagger: just the most probable sign for word.
    'baseline1' : ('baseline1', 'Baseline1Tagger'), # Simplest baseline tagging model
    'baseline2' : ('baseline2', 'Baseline2Tagger'), # Another simple baseline tagging model
    'baseline3' : ('baseline3', 'Baseline3Tagger'), # Another simple baseline tagging model
    'ngram' : ('ngram', 'NgramTagger'),             # Ngram tagger model, using bits of NLTK
    'chordclass' : ('segmidi', 'ChordClassMidiTagger'), # Chord class-based HMM tagger for MIDI
    'pretagged' : ('pretagged', 'PretaggedTagger'), # Just returns a predefined set of tags
    'chordlabel' : ('segmidi.chordlabel', 'ChordLabelNgramTagger'), # Chains together the chord labeler with the ngram tagger
    'ngram-multi' : ('ngram_multi', 'MultiChordNgramTagger'), # Ngram chord tagger that can take lattice input
}

class TaggerTrainingError(Exception):
    """ For any problems encountered while training a tagging model. """
    pass
