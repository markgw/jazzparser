"""
Segmented MIDI supertaggers.

These work by taking segmented MIDI input (MIDI divided into bars or the like) 
and telling the parser to create a chart with a node for every segment. The 
tagger then suggests spanning edges for the lexical categories.

The models I'm creating here are those based on Raphael and Stoddard's 
harmonic analysis model. See my 2nd-year review documents and presentation 
(and related documents from autumn 2011) for details of these models.

"""
from chordclass import ChordClassMidiTagger
