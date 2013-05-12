"""Command-line output printing utilities.

Utilities for formatting output to be printed to the command line.

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

def confusion_matrix(matrix):
    """
    Given a confusion matrix as a dictionary, outputs it as a table.
    
    The matrix should be in the format of a dictionary, keyed by 
    correct values (strings), containing dictionaries, keyed by 
    incorrect values (string), of integers. The integers represent 
    the number of times the incorrect value was mistaken for the 
    correct value.
    
    """
    from jazzparser.utils.tableprint import pprint_table
    import sys
    # Convert the matrix into table data
    rows = []
    for cor,incor_table in matrix.items():
        for incor,count in incor_table.items():
            rows.append([cor,incor,count])
    rows = list(reversed(sorted(rows, key=lambda r:r[2])))
    rows = [[cor,incor,str(count)] for cor,incor,count in rows]
    header = [['Correct','Incorrect','Count'],['','','']]
    return pprint_table(sys.stdout, header+rows, separator=" | ", outer_seps=True, justs=[True,True,False])

global __colorama_inited
__colorama_inited = False
__COLORAMA_PARAMS = {
    'autoreset' : True, # Not colorama default
    'strip' : None,     # Colorama default
    'convert' : None,   # Colorama default
    'wrap' : True,      # Colorama default
} # Default parameters for initing colorama: not the same as colorama's own defaults

def init_colors(**kwargs):
    """
    Initializes colorama - terminal output color package. Only initializes it 
    once. If called more than once, does nothing after the first time.
    
    Use kwargs to override colorama init params.
    
    """
    global __colorama_inited
    if not __colorama_inited:
        from colorama import init
        params = __COLORAMA_PARAMS.copy()
        params.update(kwargs)
        init(**params)
        __colorama_inited = True

def deinit_colors():
    """
    De-initializes colorama. See the colorama docs for why you'd want to do 
    this. Only does anything if colorama has been inited using L{init_colors}.
    
    @see: http://pypi.python.org/pypi/colorama
    
    """
    global __colorama_inited
    if __colorama_inited:
        from colorama import deinit
        deinit()
        __colorama_inited = False

def remove_ansi_colors(string):
    """
    Strip all ANSI color commands from the string.
    
    """
    import re
    ansisequence= re.compile(r'\x1B\[[^A-Za-z]*[A-Za-z]')
    return ansisequence.sub('', string)
