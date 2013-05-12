"""File I/O and internal representations for other people's corpora.

This package contains modules for reading in (and potentially writing 
out) data from other people's corpora and classes for representing 
and manipulating the data.

My own data is stored using the classes in the Django database 
definition or those in L{jazzparser.data.db_mirrors}.

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

__kp_info = {
    'location' : ('kostka-payne',),
    'extensions' : ['q.k'],
}

CORPORA = {
    'kostka-payne' : __kp_info,
    'kp' : __kp_info,               # Alias for easier access
}
"""Available corpus datasets, indexed by names by which they can be loaded."""


def get_corpus_file(corpus_name, file_path):
    """
    Load a file from a named corpus that is stored within the project.
    If the file is not found, we'll attempt to append the default 
    file extensions defined for this corpus until we find one that 
    exists.
    
    @type corpus_name: str
    @param corpus_name: name of the corpus
    @type file_path: list of strs or str
    @param file_path: path to file to be loaded, split into a list, or 
        as a string in the style of the local system's paths.
    
    """
    from jazzparser.settings import CORPORA_DIR
    import os
    
    if type(file_path) == str:
        file_path = file_path.split(os.sep)
    
    if corpus_name not in CORPORA:
        raise CorpusError, "unknown corpus '%s'" % corpus_name
    corpus_info = CORPORA[corpus_name]
    
    base_path = os.path.join(CORPORA_DIR, *(corpus_info['location'] + tuple(file_path)))
    # Check whether the file exists and try adding extensions if not
    extensions = [''] + [".%s" % ext for ext in corpus_info['extensions']]
    for ext in extensions:
        filename = "%s%s" % (base_path,ext)
        if os.path.exists(filename):
            return filename
    # No file found at all
    raise IOError, "file '%s' not found in %s corpus" % \
        (os.path.join(*file_path), corpus_name)

def list_corpus_files(corpus_name):
    """
    Produces a list of the files in the corpus with the given name.
    Each file is represented by its path, split into a list.
    
    """
    from jazzparser.settings import CORPORA_DIR
    import os
    
    if corpus_name not in CORPORA:
        raise CorpusError, "unknown corpus '%s'" % corpus_name
    corpus_info = CORPORA[corpus_name]
    
    path = os.path.join(CORPORA_DIR, *(corpus_info['location']))
    corpus_files = []
    # Check all the files in the directory
    for root, dirs, files in os.walk(path):
        # Don't recurse to hidden dirs
        for name in dirs:
            if name.startswith("."):
                dirs.remove(name)
        # Get rid of the base path from the root
        root = [bit for bit in root.lstrip(path).split(os.sep) if bit != '']
        # Exclude hidden files
        corpus_files.extend([root+[name] for name in files if not name.startswith(".")])
    return corpus_files


class CorpusError(Exception):
    pass
