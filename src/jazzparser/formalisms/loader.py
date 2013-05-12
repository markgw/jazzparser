"""Dynamic loader for named formalisms.

Some basic tools for the process of loading a named formalism.
A formalism can be loaded by name and the object returned should contain 
all the information you need to use the formalism (i.e. pointers to 
classes and functions).

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

from jazzparser.utils.base import load_class
from jazzparser.settings import DEFAULT_FORMALISM

def get_formalism(name):
	"""
	Returns the Formalism structure for the formalism with the given 
	name.
	"""
	from . import FORMALISMS
	if name not in FORMALISMS:
		raise FormalismLoadError, "The formalism '%s' does not exist" % name
	path = 'jazzparser.formalisms.%s.Formalism' % name
	return load_class(path)

def get_default_formalism():
	return get_formalism(DEFAULT_FORMALISM)

class FormalismLoadError(Exception):
	pass
