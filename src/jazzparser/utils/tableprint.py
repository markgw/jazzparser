"""Pretty-printing tables as strings.

A bit of simple code to output a table to stdout.

Many thanks to 
U{http://ginstrom.com/scribbles/2007/09/04/pretty-printing-a-table-in-python/}
for the basic code that I used to do the core stuff here. I've developed 
on it a bit myself and added the Latex table stuff down the bottom.

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


import locale
from textwrap import TextWrapper

from jazzparser.utils.base import filter_latex

locale.setlocale(locale.LC_NUMERIC, "")

def format_num(num):
    """Format a number according to given places.
    Adds commas, etc. Will truncate floats into ints!
    """

    try:
        inum = int(num)
        return locale.format("%.*f", (0, inum), True)

    except (ValueError, TypeError):
        return str(num)
    
def get_max_width(table, index):
    """
    Get the maximum width of the given column index
    
    """
    return max([max(len(line) for line in row[index].split("\n")) for row in table])

def format_table(*args, **kwargs):
    """
    Like L{pprint_table}, but returns a string containing the formatted table, 
    whilst L{pprint_table} outputs directly to a stream.
    
    Args and kwargs are the same as to L{pprint_table}.
    
    """
    from cStringIO import StringIO
    out = StringIO()
    # Run pprint_table to do the pretty-printing
    pprint_table(out, *args, **kwargs)
    # Get the string that was printed
    string = out.getvalue()
    out.close()
    return string

def pprint_table(out, table, justs=None, separator=None, outer_seps=False, \
        widths=None, blank_row=False, default_just=None, hanging_indent=0):
    """
    Prints out a table of data, padded for alignment.
    Each row must have the same number of columns. 
    
    Cells may include line breaks.
    
    @param out: output stream
    @type out: file-like object
    @param table: table to print.
    @type table: list of lists
    @param outer_seps: Prints separators at the start and end of each row 
        if true.
    @type outer_seps: bool
    @type widths: list of ints
    @param widths: maximum width for each column. None means no maximum is 
        imposed. Words are wrapped if the width exceeds the maximum
    @type default_just: bool
    @param default_just: the default justification to use for all columns 
        if C{justs} is not given or where a column's justification is not 
        given. Default False
    @type hanging_indent: int
    @param hanging_indent: hanging indent to apply to the column if a cell 
        is wrapped (number of spaces)
    
    """
    col_paddings = []
    wrapper = TextWrapper()
    
    if hanging_indent:
        wrapper.indent = ''
        wrapper.subsequent_indent = ' '*hanging_indent
    
    # Format any numbers in the table
    table = [
        [format_num(cell) for cell in row]
            for row in table]

    # Work out the maximum width of each column so we know how much to pad
    for i in range(len(table[0])):
        if widths is not None and widths[i] is not None:
            col_paddings.append(widths[i])
        else:
            col_paddings.append(get_max_width(table, i))
    
    # Work out justification of each column
    coljusts = []
    if default_just is None:
        default_just = False
    for col in range(len(table[0])):
        if justs:
            if justs[col] is not None:
                coljust = justs[col]
            else:
                coljust = default_just
        else:
            coljust = default_just
        coljusts.append(coljust)
    
    # Wrap the long cells that have a max width
    multiline = []
    for row in table:
        mlrow = []
        for col,cell in enumerate(row):
            # If this cell exceeds its max width, put it on multiple lines
            if widths is not None and \
                    widths[col] is not None and \
                    len(cell) > widths[col]:
                wrapper.width = widths[col]
                lines = []
                # Split on manual line breaks in the input as well
                for input_line in cell.split("\n"):
                    lines.extend(wrapper.wrap(input_line))
            else:
                lines = cell.split("\n")
            mlrow.append(lines)
        multiline.append(mlrow)

    for row in multiline:
        if outer_seps:
            print >> out, separator,
        # Find out the cell with the most lines in this row
        max_lines = max(len(cell) for cell in row)
        # Each line of the row
        for line in range(max_lines):
            for col in range(len(row)):
                # If this cell doesn't have this many lines, just pad
                padsize = col_paddings[col] + 2
                if line >= len(row[col]):
                    text = " " * padsize
                else:
                    # There's text: justify it
                    if coljusts[col]:
                        text = row[col][line].ljust(padsize)
                    else:
                        text = row[col][line].rjust(padsize)
                if col != 0 and separator:
                    print >> out, separator,
                print >> out, text,
            if outer_seps:
                print >> out, separator,
            print >>out
        # Add an extra blank line between rows
        if blank_row:
            print >>out
        
def print_latex_table(out, table, justs=None, separator=None, headings=False):
    """
    Prints out the Latex code to display the given
    2D list as a table.
    
    """
    if justs is None:
        justs = ["l"] * len(table[0])
    
    if separator:
        coldiv = " | "
    else:
        coldiv = " "
        
    print >> out, "\\begin{tabular}{%s}" % coldiv.join(justs)
    
    if headings:
        print >> out, " & ".join(["\\textbf{%s}" % filter_latex("%s" % cell) for cell in table[0]]) + "\\\\\n"
        print >> out, "\\\\\n".join([" & ".join([filter_latex("%s" % cell) for cell in row]) for row in table[1:]])
    else:
        print >> out, "\\\\\n".join([" & ".join([filter_latex("%s" % cell) for cell in row]) for row in table])
    
    print >> out, "\\end{tabular}"
        
