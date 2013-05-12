"""Data structures that mirror the database models.

In order to have a data format that can be passed around without 
needing a database set up to import the data into, we need mirrors 
of the database models that are not themselves dependent on a database.
These classes exactly replicate the data structure of the models in
apps.sequences.models and can be created from those models 
(see model.mirror).

The intention of this is not that this data can be imported back into 
the database, but simply that all the database's chord sequence data 
can be read in (from a pickled file) and output to other formats.
These classes just provide the unified database-independent data models.
It is these exported models that are used for training models, etc.

Use load_pickled_data to read in a file that's been created from the 
database models.

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

from jazzparser.utils.chords import int_to_pitch_class

class Chord(object):
    """
    A single instance of a chord in a sequence. These are chained by 
    their C{next} attribute into a sequence.
    
    """
    def __init__(self, root=None, type=None, additions=None, bass=None, 
                 next=None, duration=None, category=None, sequence=None,
                 treeinfo=None):
        self.root = root            # Int
        self.type = type            # Store as a string
        self.additions = additions  # String
        self.bass = bass            # Int
        self.next = next            # Another Chord mirror
        self.duration = duration    # Int
        self.category = category    # String
        self.sequence = sequence    # Mirror of the sequence model
        self.treeinfo = treeinfo
        
    # The following methods are identical to the model's
    
    def __unicode__(self):
        return unicode('%s%s' % (int_to_pitch_class(self.root), self.type))
        
    def __str__(self):
        return str(unicode(self))
    jazz_parser_input = property(__str__)
    
    def __repr__(self):
        return str(self)
        
    def _get_treeinfo(self):
        if self._treeinfo is not None:
            return self._treeinfo
        else:
            # Return the default info
            return TreeInfo()
    def _set_treeinfo(self, ti):
        if ti is not None:
            ti.chord = self
        self._treeinfo = ti
    treeinfo = property(_get_treeinfo, _set_treeinfo)
        
class TreeInfo(object):
    """
    Additional information about a chord that allows an unambiguous 
    derivation tree to be built.
    
    Stored as a separate class because it's a separate table in the 
    database.
    
    """
    def __init__(self, coord_unresolved=False, coord_resolved=False):
        self.coord_resolved = coord_resolved
        self.coord_unresolved = coord_unresolved
    
class ChordSequence(object):
    """
    A chord sequence in the corpus.
    
    Chords in the sequence are stored in a linked list structure 
    (implemented by L{Chord}). The start of the list is given by 
    C{first_chord}.
    
    You can also iterate over a C{ChordSequence} instance, which will 
    iterate over its chords.
    
    """
    def __init__(self, name=None, key=None, bar_length=None, first_chord=None, 
                 notes=None, analysis_omitted=None, omissions=None, 
                 source=None, id=None):
        self.name = name                # String
        self.key = key                  # String
        self.bar_length = bar_length    # Int
        self.first_chord = first_chord  # Mirror of a Chord
        self.notes = notes              # String
        self.analysis_omitted = analysis_omitted # Bool
        self.omissions = omissions      # String
        self.source = source            # Store as a string
        self.id = id
        
    # The following methods are identical to the model's
    
    def __unicode__(self):
        return unicode(self.name)
        
    def _get_string_name(self):
        return unicode(self).encode('ascii','replace')
    string_name = property(_get_string_name)
    
    def iterator(self):
        chord = self.first_chord
        while chord is not None:
            yield chord
            chord = chord.next
            
    def __iter__(self):
        return self.iterator()
    
    def _get_number_annotated(self):
        total = 0
        annotated = 0
        for chord in self.iterator():
            if chord.category is not None and chord.category != "":
                annotated += 1
            total += 1
        return (annotated, total)
    number_annotated = property(_get_number_annotated)
    
    def _get_percentage_annotated(self):
        annotated, total = self.number_annotated
        return 100.0 * float(annotated) / float(total)
    percentage_annotated = property(_get_percentage_annotated)
    
    def _get_fully_annotated(self):
        """
        True if every chord in the sequence is annotated. This should 
        usually be a bit quicker than checking percentage_annotated.
        """
        for chord in self.iterator():
            if chord.category is None or chord.category == "":
                return False
        return True
    fully_annotated = property(_get_fully_annotated)
    
    def _get_length(self):
        return len(list(self.iterator()))
    length = property(_get_length)
    __len__ = _get_length
    
    @property
    def time_map(self):
        time = 0
        time_map = {}
        for chord in self.iterator():
            time_map[time] = chord
            time += chord.duration
        return time_map

def load_pickled_data(filename):
    """
    Data from the database can be converted into the form of the above 
    models and saved to a file by pickling (see apps.sequences.datautils).
    Without any dependence on the database, we can then read in such a 
    file and access all the sequence data.
    Returns a list of ChordSequence mirrors.
    """
    import os.path, pickle
    filename = os.path.abspath(filename)
    file = open(filename, 'r')
    # Read in the pickled data
    unpick = pickle.Unpickler(file)
    data = unpick.load()
    file.close()
    return data

def save_sequences(filename, sequences):
    """
    Given a list of ChordSequence mirror instances, saves them to a 
    file by pickling.
    This can be done directly from the database using 
    apps.sequences.datautils.pickle_all_sequences.
    
    """
    import pickle, os.path
    filename = os.path.abspath(filename)
    file = open(filename, 'w')
    pickler = pickle.Pickler(file)
    pickler.dump(sequences)
    file.close()

class SequenceIndex(object):
    """
    Stores indexes and provides quick access to mirrored sequences.
    Since we are not accessing the database directly, this provides 
    a reasonably efficent alternative to doing a linear search through 
    sequences every time when need one.
    
    Iterating of a C{SequenceIndex} instance will iterate over its 
    sequences in order of id.
    
    """
    @staticmethod
    def from_file(filename):
        return SequenceIndex(load_pickled_data(filename))
        
    def __init__(self, sequences):
        self._sequences = sequences
        self.prepare_indices()
        
    def _get_sequences(self):
        return list(sorted(self._sequences, key=lambda s:s.id))
    sequences = property(_get_sequences)
        
    def prepare_indices(self):
        self._by_id = dict([(seq.id,seq) for seq in self.sequences])
        
    def sequence_by_id(self, id):
        if id in self._by_id:
            return self._by_id[id]
        else:
            return None
            
    def _get_ids(self):
        return list(sorted(self._by_id.keys()))
    ids = property(_get_ids)
    
    def __len__(self):
        return len(self._sequences)
        
    def sequence_by_index(self, index):
        id = self.id_for_index(index)
        if id is not None:
            return self.sequence_by_id(id)
        return
            
    def id_for_index(self, index):
        if index >= len(self):
            return None
        else:
            return list(sorted(self.ids))[index]
    
    def index_for_id(self, id):
        """
        Get the index in the sequence file of the sequence with the 
        given id. Returns None if the id isn't in the sequence file.
        
        """
        if id not in self.ids:
            return None
        else:
            return list(sorted(self.ids)).index(id)
            
    def __iter__(self):
        return iter(self.sequences)
