"""Unit tests for jazzparser.data.input module

"""
"""
============================== License ========================================
 Copyright (C) 2008, 2010-12 University of Edinburgh, Mark Granroth-Wilding
 
 This file is part of The Jazz Parser.
 
 The Jazz Parser is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 The Jazz Parser is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 
 You should have received a copy of the GNU General Public License
 along with The Jazz Parser.  If not, see <http://www.gnu.org/licenses/>.

============================ End license ======================================

"""
__author__ = "Mark Granroth-Wilding <mark.granroth-wilding@ed.ac.uk>" 

import unittest, os
from jazzparser import settings

from jazzparser.data.input import DbInput, ChordInput, DbBulkInput, \
								ChordBulkInput, SegmentedMidiInput, \
								SegmentedMidiBulkInput, detect_input_type, \
								input_type_name, InputTypeError, INPUT_TYPES, \
								BULK_INPUT_TYPES, is_bulk_type
from jazzparser.data.db_mirrors import SequenceIndex

DB_SEQUENCES_FILE = os.path.join(settings.TEST_DATA_DIR, "dbsequences")
CHORDS_FILE = os.path.join(settings.TEST_DATA_DIR, "text_chords")
CHORD_SEQS_FILE = os.path.join(settings.TEST_DATA_DIR, "text_chord_list")
CHORDS = "IM7 IV7 IM7 I7 IV7"
MIDI_FILE = os.path.join(settings.TEST_DATA_DIR, "afine.mid")
SEGMENTED_MIDI = (
	os.path.join(settings.TEST_DATA_DIR, "afternoon.mid"),
	2, 
	240
)
SEGMENTED_MIDIS = os.path.join(settings.TEST_DATA_DIR, "segmidi.csv")

class TestDbInput(unittest.TestCase):
	"""
	Tests for loading a DbInput.
	
	"""
	def test_from_sequence(self):
		# Load the sequence index file
		index = SequenceIndex.from_file(DB_SEQUENCES_FILE)
		# Pick out a sequence
		seq = index.sequences[0]
		# Construct a DbInput from this sequence
		dbi = DbInput.from_sequence(seq)
		
	def test_from_file(self):
		# Select a sequence out of the sequence index file using the "index" option
		options = {
			'index' : 0,
		}
		# Just load the sequence up from the file
		dbi = DbInput.from_file(DB_SEQUENCES_FILE, options)

class TestChordInput(unittest.TestCase):
	"""
	Test for loading a ChordInput.
	
	"""
	def test_from_file(self):
		# Just load the file
		ci = ChordInput.from_file(CHORDS_FILE, options={'roman':True})
	
	def test_from_string(self):
		ci = ChordInput.from_string(CHORDS, roman=True)
	
class TestSegmentedMidiInput(unittest.TestCase):
	"""
	Test for loading a SegmentedMidiInput from a MIDI file.
	
	"""
	def test_from_file(self):
		""" Load a file with default options. """
		options = SegmentedMidiInput.process_option_dict({})
		mid = SegmentedMidiInput.from_file(MIDI_FILE, options=options)
		
	def test_from_file_with_options(self):
		""" Load a file with time unit and offset options. """
		options = SegmentedMidiInput.process_option_dict({
			'time_unit' : SEGMENTED_MIDI[1],
			'tick_offset' : SEGMENTED_MIDI[2],
		})
		mid = SegmentedMidiInput.from_file(SEGMENTED_MIDI[0], options=options)

class TestDbBulkInput(unittest.TestCase):
	"""
	Test for loading a DbBulkInput.
	
	"""
	def test_from_file(self):
		# Simply load a sequence index file
		bulk = DbBulkInput.from_file(DB_SEQUENCES_FILE)
		# We can get the sequences just but converting the iter to a list
		seqs = list(bulk)
		# There should be a non-zero number of sequences loaded
		self.assertNotEqual(len(seqs), 0)
		# Check the type of the first one
		self.assertIsInstance(seqs[0], DbInput)

class TestChordBulkInput(unittest.TestCase):
	"""
	Tests for loading a ChordBulkInput (text chord sequences).
	
	"""
	def test_from_file(self):
		# Load up the chord sequence list from a file
		bulk = ChordBulkInput.from_file(CHORD_SEQS_FILE, options={'roman':True})
		# Get a list of the sequences
		seqs = list(bulk)
		# Check some sequences were loaded
		self.assertNotEqual(len(seqs), 0)
		# Check the type of the first one
		self.assertIsInstance(seqs[0], ChordInput)
		
		# There should be some sequences with names (though not all)
		self.assertTrue(any(seq.name is not None for seq in seqs))

class TestSegmentedMidiBulkInput(unittest.TestCase):
	"""
	Tests for loading a list of MIDI files from a CSV.
	
	"""
	def test_from_file(self):
		options = SegmentedMidiBulkInput.process_option_dict({})
		mids = SegmentedMidiBulkInput.from_file(SEGMENTED_MIDIS, options=options)

class TestUtilities(unittest.TestCase):
	"""
	Tests the utility functions.
	
	"""
	def test_detect_input_type(self):
		# Load some input: DbInput
		dbi = DbInput.from_file(DB_SEQUENCES_FILE, {'index':0})
		# Run it through the preprocessor
		datatype,obj = detect_input_type(dbi)
		# Get the datatype from the type name lists
		datatype2 = input_type_name(type(obj))
		self.assertEqual(datatype, datatype2)
		
		# Do the same with ChordInput
		ci = ChordInput.from_file(CHORDS_FILE, options={'roman':True})
		datatype,obj = detect_input_type(ci)
		datatype2 = input_type_name(type(obj))
		self.assertEqual(datatype, datatype2)
		
		# Try some bulk input
		bulk = DbBulkInput.from_file(DB_SEQUENCES_FILE)
		datatype,obj = detect_input_type(bulk, allow_bulk=True)
		datatype2 = input_type_name(type(obj))
		self.assertEqual(datatype, datatype2)
		
		# Try restricting the allowed type
		datatype,obj = detect_input_type(ci, allowed=['chords'])
		# And this one should get rejected
		self.assertRaises(InputTypeError, detect_input_type, (ci,), {'allowed':'db'})

class TestTypeLists(unittest.TestCase):
	"""
	Some sanity checks on the type lists.
	
	"""
	def test_input_types(self):
		# Check INPUT_TYPES doesn't have bulk input types
		for datatype,cls in INPUT_TYPES:
			self.assertFalse(is_bulk_type(cls))
		# Check there are no duplicate names
		names,__ = zip(*(INPUT_TYPES+BULK_INPUT_TYPES))
		self.assertEqual(len(names), len(set(names)), msg="Duplicate input type names")
			
	def test_bulk_input_types(self):
		# Check BULK_INPUT_TYPES is only bulk types
		for datatype,cls in BULK_INPUT_TYPES:
			self.assertTrue(is_bulk_type(cls))
