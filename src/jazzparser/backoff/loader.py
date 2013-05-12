"""Dynamic loader for backoff modules.

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

def get_backoff_builder(name):
	"""
	Returns the backoff builder class with the given name.
    
	"""
	from . import BUILDERS
	if name not in BUILDERS:
	    raise BackoffLoadError, "The backoff builder '%s' does not exist" \
		% name
	path = 'jazzparser.backoff.%s.%s' % BUILDERS[name]
	return load_class(path)

class BackoffLoadError(Exception):
    pass
