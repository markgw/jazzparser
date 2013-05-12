"""Chord type mappings

Chord supertaggers use mappings from the input chord vocabulary to a smaller 
one. Various mappings are available and may be selected at model training 
time.

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

from jazzparser.utils.options import ModuleOption, choose_from_dict

NAMED_MAPPINGS = {}

class NamedMapping(dict):
    """
    Just a dictionary with a name.
    """
    def __init__(self, name, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.name = name

# Mapping to a small set of chord labels
SMALL_MAPPING = NamedMapping("small", {
    ""     : "",
    "m"    : "m", 
    "M7"   : "", 
    "o7"   : "o7",
    "%7"   : "o7", 
    "aug"  : "aug",
    "m,b5" : "o7",
    "b5"   : "7",
    "m,M7" : "m",
    "7"    : "7",
    "m7"   : "m7",
    "aug7" : "aug",
    "b5,7" : "7",
    "sus4" : "",
    "sus4,7" : "7",
    "aug,M7" : "aug",
    "b5,M7"  : "7",
    "#5,m7"  : "m7",
})

# Mapping to a larger set of chord labels
BIG_MAPPING = NamedMapping("big", {
    ""     : "",
    "m"    : "m", 
    "M7"   : "M7", 
    "o7"   : "o7",
    "%7"   : "o7", 
    "aug"  : "aug",
    "m,b5" : "o7",
    "b5"   : "b5",
    "m,M7" : "m",
    "7"    : "7",
    "m7"   : "m7",
    "aug7" : "aug7",
    "b5,7" : "7",
    "sus4" : "sus4",
    "sus4,7" : "sus4",
    "aug,M7" : "aug",
    "b5,M7"  : "7",
    "#5,m7"  : "m7",
})

# No mapping at all
IDENTITY_MAPPING = NamedMapping("none", {
    ""     : "",
    "m"    : "m", 
    "M7"   : "M7", 
    "o7"   : "o7",
    "%7"   : "%7", 
    "aug"  : "aug",
    "m,b5" : "m,b5",
    "b5"   : "b5",
    "m,M7" : "m,M7",
    "7"    : "7",
    "m7"   : "m7",
    "aug7" : "aug7",
    "b5,7" : "b5,7",
    "sus4" : "sus4",
    "sus4,7" : "sus4,7",
    "aug,M7" : "aug,M7",
    "b5,M7"  : "b5,M7",
    "#5,m7"  : "#5,m7",
})

NAMED_MAPPINGS = dict([(mapping.name, mapping) for mapping in \
    [
        SMALL_MAPPING, 
        IDENTITY_MAPPING, 
        BIG_MAPPING,
    ]
])
MAPPINGS = NAMED_MAPPINGS.keys()
DEFAULT_MAPPING = "small"

def get_chord_mapping(name=None):
    """
    Returns a dictionary chord type mapping identified by its name.
    A list of available mappings can be found in L{MAPPINGS}.
    
    """
    if name is None:
        name = DEFAULT_MAPPING
    return NAMED_MAPPINGS[name]

def get_chord_mapping_module_option(name="chord_mapping"):
    return ModuleOption(name, 
                        filter=choose_from_dict(NAMED_MAPPINGS),
                        help_text="Choose a mapping to apply to chord types "\
                            "to reduce the chord vocabulary",
                        usage="%s=M, where M is one of %s. Default: %s" % \
                            (name, ", ".join(MAPPINGS), DEFAULT_MAPPING),
                        default=get_chord_mapping())
