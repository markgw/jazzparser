"""Storage of tonal space analyses in a (relatively) quickly-accessible corpus.

Use the script bin/data/parsegs.py to create and store these sets from the 
chord corpus.

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

import os
import cPickle as pickle
from jazzparser import settings

FILE_EXTENSION = "anal"

class TonalSpaceAnalysisSet(object):
    """
    Data structure to hold and store a set of tonal space analyses.
    
    """
    def __init__(self, analyses, name="unnamed"):
        """
        @type analyses: list of (string,analysis) pairs
        @param analyses: pairings of song names and analyses
        
        """
        self.analyses = [(str(song).lower(),anal) for (song,anal) in analyses]
        self.name = name
        
    def get_analyses(self, song_name):
        return [anal for (song,anal) in self.analyses if song==song_name.lower()]
        
    def __get_songs(self):
        return zip(*self.analyses)[0]
    songs = property(__get_songs)
    
    def __len__(self):
        return len(self.analyses)
        
    def __getitem__(self, index):
        return self.analyses[index]
    
    ######### Storage machinery ############
    @staticmethod
    def _get_filename(name):
        return os.path.join(settings.ANALYSIS_DATA_DIR, "%s.%s" % (name, FILE_EXTENSION))
    def __get_my_filename(self):
        return type(self)._get_filename(self.name)
    _filename = property(__get_my_filename)
    
    @classmethod
    def list(cls):
        """ Returns a list of the names of available stored sets. """
        datadir = settings.ANALYSIS_DATA_DIR
        if not os.path.exists(datadir):
            return []
    # Get a listing of the data directory
        names = [name.rpartition(".") for name in os.listdir(datadir)]
    # Return the names of all the files with the correct extension
        return [name for name,__,ext in names if ext == FILE_EXTENSION]
        
    def save(self):
        """ Saves the set data to a file. """
        # Get a picklable form of the set
        data = {
            'analyses' : self.analyses,
        }
        data = pickle.dumps(data, 2)
        filename = self._filename
        # Check the directory exists
        filedir = os.path.dirname(filename)
        if not os.path.exists(filedir):
            os.mkdir(filedir)
        # Write the data into the file
        f = open(filename, 'w')
        f.write(data)
        f.close()
        
    def delete(self):
        """ Removes all the data for the set. """
        fn = self._filename
        if os.path.exists(fn):
            os.remove(fn)
            
    @classmethod
    def load(cls, name):
        filename = cls._get_filename(name)
        # Load the data from a file
        if os.path.exists(filename):
            f = open(filename, 'r')
            data = f.read()
            data = pickle.loads(data)
            f.close()
        else:
            raise TonalSpaceAnalysisSetLoadError, "the tonal space analysis "\
            "set '%s' does not exist" % name
        # Create the object from the loaded data
        obj = TonalSpaceAnalysisSet(data['analyses'], name=name)
        return obj

class TonalSpaceAnalysisSetLoadError(Exception):
    pass

