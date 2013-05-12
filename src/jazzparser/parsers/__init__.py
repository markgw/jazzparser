"""Parser modules for the Jazz Parser.

Subpackages of this define parser modules. Each may implement its own 
parsing algorithm and operates independently of the formalism and 
tagger, which have strictly defined interfaces through which the parser 
accesses them.

To add a new parser, create the parser class in a new subpackage and 
add the package's name to the PARSERS constant below.

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


PARSERS = [
    'cky',
    'pcfg',
    'tagrank',
    'fail',
]

class RuleApplicationError(Exception):
    """
    Thrown if there's an error during application of a rule to categories.
    """
    pass

class ParseError(Exception):
    """
    Thrown if it's not possible to carry out a parse, for some reason.
    E.g. the word might not be in the morphology.
    """
    pass

class ParserInitializationError(Exception):
    """
    Thrown when initializing the parser if something in the 
    configuration prevents correct initialization.
    """
    pass
