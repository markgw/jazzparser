"""Generic interface utilities (e.g. interactive command-line processing).

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


def boolean_input(prompt):
    """
    Displays a prompt with a yes/no choice. Returns True is the user 
    selects yes, False otherwise.
    
    """
    response = raw_input("%s [y/N] " % prompt)
    if response.lower() == "y":
        return True
    else:
        return False

def input_iterator(prompt):
    """
    Creates an iterator that will accept command line input indefinitely 
    and terminate when Ctrl+D is received.
    
    The iterator uses C{raw_input}, so you can use it in conjunction with 
    C{readline}.
    
    """
    # Define an iterator (via a generator) to get cmd line input
    def _get_input():
        try:
            while True:
                yield raw_input(prompt)
        except EOFError:
            return
    return iter(_get_input())
