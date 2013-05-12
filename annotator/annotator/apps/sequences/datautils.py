"""datautils.py -- data processing utilities for import and export of 
chord sequence data.

"""
"""
============================== License ========================================
 Copyright (C) 2008, 2010 University of Edinburgh, Mark Wilding
 
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
__author__ = "Mark Wilding <mark.wilding@ed.ac.uk>" 

import pickle
import logging

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

def pickle_all_sequences(query=None, filter=None, no_names=False):
    """
    Pickles all sequences in the database and returns the result. 
    Optionally filters using a Django Q query first.
    """
    from apps.sequences.models import ChordSequence
    # Get all the sequences from the database
    seqs = ChordSequence.objects.all()
    if query is not None:
        seqs = seqs.filter(query)
    # Apply a filter if one was given
    if filter is not None:
        seqs = [s for s in seqs if filter(s)]
    # Get the non-database-dependent mirror of each sequence
    mirrors = []
    for s in seqs:
        logger.info(s.string_name)
        mirrors.append(s.mirror)
    if no_names:
        # Replace all the sequences' names
        for mirror in mirrors:
            mirror.name = "sequence-%d" % mirror.id
    # Just pickle this list and we'll get all the instance data stored.
    # Use protocol 2, which is more efficient than its predecessors.
    return pickle.dumps(mirrors, 2)

def save_pickled_data(filename, query=None, filter=None, no_names=False):
    """
    Writes pickled chord sequence data out to the given filename.
    Optionally filters the chord sequences with the given Django Q query.
    """
    import os.path
    filename = os.path.abspath(filename)
    file = open(filename, 'w')
    file.write(pickle_all_sequences(query, filter=filter, no_names=no_names))
    file.close()
