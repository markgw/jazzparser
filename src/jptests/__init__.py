"""Unit tests for the Jazz Parser.

This package contains all unit tests for the Jazz Parser.
A library of unit tests should be gradually built up in here and should 
mirror the package structure of the codebase in the jazzparser package, 
to keep it clear where tests for everything are to be found.

At the time of writing, not many tests exist and will almost certainly 
never get round to writing tests for large parts of the codebase. 
However, there are some parts that are used particularly frequently, 
so I will try to write tests for these first (data structures, utils 
modules, etc). These are also expected to maintain their interface, 
or at least something backward compatible, most of the time, so 
it shouldn't be too big a job to rewrite the tests if they change.

For scripts for running the tests, see C{bin/tests}.

Notes
=====

 1. I've not used the test_*.py naming convention, since the tests are all in a 
  separate code tree, so there's no real need. The scripts for running the tests
  take care of all these sorts of things, so it's best to use them to run tests.

 2. Some tests are for things in a module's __init__.py. Although I'm in most 
  cases mirroring the package structure of the code in the test code, in these 
  cases I call the test files init.py. If they're called __init__.py they get 
  discovered twice by unittest: once as the package import and once as the 
  __init__.py file itself.

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


def prepare_db_input():
    """
    Loads a sequence index file, pulls out some data and prepares it 
    as it using it as input to the parser.
    
    This may be used by tests to get hold of data as example input.
    
    @note: Don't rely on the size of the returned tuple to stay the 
    same. I may add more return items in the future, so access the 
    ones that are being returned currently by index.
    
    @rtype: tuple
    @return: (sequence index, sequence, DbInput instance)
    
    """
    from jazzparser.data.db_mirrors import SequenceIndex
    from jazzparser.data.input import DbInput
    from jazzparser.settings import TEST as settings
    
    seqs = SequenceIndex.from_file(settings.SEQUENCE_DATA)
    seq = seqs.sequences[0]
    
    input_sequence = DbInput.from_sequence(seq)
    
    return seqs, seq, input_sequence
