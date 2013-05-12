"""Latex output utility functions to help with producing valid Latex files.

Utility functions for handling processing and output of Latex.

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

def filter_latex(text):
    """
    Applies necessary filters to Latex text before outputting. Mainly
    involves escaping strings.
    
    """
    text = text.replace("#","\\#")
    text = text.replace("%","\\%")
    text = text.replace("_", "\\_")
    return text

def start_document(title=None, author=None, packages=[], options=[], toc=False):
    output = ""
    output += "\\documentclass[%s]{article}\n" % ",".join(options+['a4paper'])
    for package in packages:
        output += "\\usepackage{%s}\n" % package
    output += "\\begin{document}\n"
    if title is not None:
        output += "\\title{%s}\n" % title
    if author is not None:
        output += "\\author{%s}\n" % author
    else:
        output += "\\author{}\n"
    output += "\\maketitle\n"
    if toc:
        output += "\\tableofcontents\n"
    return output
