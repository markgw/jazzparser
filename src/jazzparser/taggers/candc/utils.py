"""Some basic utilities used by the C&C tagger interface.

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

def untag_sequence_data(sequence):
    """
    Given a line read in from a file containing C&C-style tagged 
    data, returns a version of the line with the tags stripped off, 
    leaving just the chord sequence.
    """
    return " ".join([c.partition("|")[0] for c in sequence.split()])
    
def tags_from_sequence_data(sequence):
    return [c.rpartition("|")[2] for c in sequence.split()]

def training_sequence_to_candc(sequence):
    """
    Given a line of data in the format we use for training data, 
    converts it to a format suitable for direct input to the C&C 
    training tool.
    
    Precisely, it removes the first X| from the start of each 
    observation, which in the data format we use is the chord itself.
    
    """
    # Remove the first | and everything before it
    return " ".join([c.partition("|")[2] for c in sequence.split()])

def training_data_to_candc(lines):
    """
    Performs the same as training_sequence_to_candc, but on a whole 
    data set (list of sequences).
    """
    return [training_sequence_to_candc(seq) for seq in lines]


def _sequence_to_candc_format(formatter, sequence):
    """
    Produces a string representation of observations to be used as 
    training data for a C&C model from a chord sequence internal
    model.
    This is an inner function for the various different formats of 
    C&C data we use.
    
    """
    from jazzparser.utils.base import group_pairs
    # Produce observations from chord pairs
    pairs_list = group_pairs( list(sequence.iterator()) + [None] )
    observation_list = [formatter(*chords) for chords in pairs_list]
    return "%s\n" % " ".join(observation_list)

def _type_format(type, mapping):
    if mapping is None:
        return type
    else:
        return mapping[type]
    
def sequence_to_candc_pos(sequence, type_map=None):
    # Generate POS training data
    def _formatter(chord1, chord2):
        if chord2 is None:
            interval = ""
        else:
            interval = "%d" % ((chord2.root - chord1.root) % 12)
        return "%s-%s|C" % (interval, _type_format(chord1.type, type_map))
    return _sequence_to_candc_format(_formatter, sequence)

def sequence_to_candc_chord_super(sequence, type_map=None):
    # This is our own combined format that includes the observation, 
    #  super-tagger training and the chord itself
    def _formatter(chord1, chord2):
        if chord2 is None:
            interval = ""
        else:
            interval = "%d" % ((chord2.root - chord1.root) % 12)
        return "%s|%s-%s|C|%s" % (chord1.jazz_parser_input, interval, 
                _type_format(chord1.type, type_map), chord1.category or "?")
    return _sequence_to_candc_format(_formatter, sequence)
    
def sequence_to_candc_super(sequence, type_map=None):
    # Generate super-tagger training data
    def _formatter(chord1, chord2):
        if chord2 is None:
            interval = ""
        else:
            interval = "%d" % ((chord2.root - chord1.root) % 12)
        return "%s-%s|C|%s" % (interval, _type_format(chord1.type, type_map), 
                                    chord1.category or "?")
    return _sequence_to_candc_format(_formatter, sequence)

def sequence_index_to_candc_chord_super(si, *args, **kwargs):
    """
    Given a SequenceIndex object containing sequence data, produces 
    C&C training data as a single string.
    
    """
    return "".join([sequence_to_candc_chord_super(s, *args, **kwarg) for s in si.sequences])
    
def sequence_list_to_candc_chord_super(sequences, *args, **kwarg):
    """
    Given a list of sequences, produces 
    C&C training data as a single string.
    
    """
    return "".join([sequence_to_candc_chord_super(s, *args, **kwarg) for s in sequences])
    
def sequence_index_to_training_file(si, type_map=None):
    """
    Given a SequenceIndex object, returns an open temporary file 
    containing all the data in our hybrid C&C training data format.
    This is converted (rather trivially) by the train_model function 
    into C&C's required format.
    
    """
    from tempfile import NamedTemporaryFile
    file = NamedTemporaryFile()
    file.write(sequence_index_to_candc_chord_super(si, type_map=type_map))
    file.flush()
    return file
    
def sequence_list_to_training_file(seqs, type_map=None):
    """
    Given a list of sequences, returns an open temporary file 
    containing all the data in our hybrid C&C training data format.
    This is converted (rather trivially) by the train_model function 
    into C&C's required format.
    
    """
    from tempfile import NamedTemporaryFile
    file = NamedTemporaryFile()
    file.write(sequence_list_to_candc_chord_super(seqs, type_map=type_map))
    file.flush()
    return file

def generate_tag_list(filename, grammar=None):
    """
    Generates a list of possible tags to be stored along with a C&C model.
    It contains all tags that are in the grammar.
    
    """
    from jazzparser.grammar import get_grammar
    if grammar is None:
        # Load the default grammar
        grammar = get_grammar()
    tags = grammar.families.keys()
    data = "\n".join(tags)
    file = open(filename, 'w')
    file.write(data)
    file.close()

def read_tag_list(filename):
    """
    Reads in a tag list generated by L{generate_tag_list}.
    
    """
    with open(filename, 'r') as f:
        data = f.read()
    return data.split("\n")
