"""Dynamic loader for supertagger modules.

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
from jazzparser.settings import DEFAULT_SUPERTAGGER

def get_tagger(name):
	"""
	Returns the tagger class for the tagger with the given name.
	"""
	from . import TAGGERS
	if name not in TAGGERS:
		from .tagger import TaggerLoadError
		raise TaggerLoadError, "The tagger '%s' does not exist" % name
	path = 'jazzparser.taggers.%s.%s' % TAGGERS[name]
	return load_class(path)

def get_default_tagger():
	return get_tagger(DEFAULT_SUPERTAGGER)

class TaggerLoadError(Exception):
    pass
