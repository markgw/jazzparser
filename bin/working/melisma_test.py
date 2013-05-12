#!../jazzshell
# Test script for the basic melisma interface
from melisma import mftext, polyph, PolyphResult
import sys

midi_data = open('come_fly_with_me-7.mid', 'r').read()
print "Generating note data"
note_data = mftext(midi_data)
# Limit the note data to 100 lines, so this doesn't take too long
note_data = "\n".join(note_data.split("\n")[:200])
print "Running analysis"
analysis = polyph(note_data)
print analysis
