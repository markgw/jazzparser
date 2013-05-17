"""Utilities for handling local system config stored in files.

Local system setup specific to each installation is stored in files in the 
C{etc/local} directory. 

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

import os
from jazzparser.settings import LOCAL_CONFIG_DIR
from jazzparser.utils.config import ConfigFile

class LocalConfig(object):
    #### Override these #####
    OPTIONS = {} # Option name -> default value
    name = "base"
    #########################
    
    def __init__(self, options={}):
        # Add default values for things that weren't given
        for opt,default in self.OPTIONS.items():
            if opt not in options:
                options[opt] = default
        self.options = options
    
    @staticmethod
    def _get_filename(name):
        return os.path.join(LOCAL_CONFIG_DIR, "%s.conf" % name)
    @classmethod
    def filename(cls):
        return LocalConfig._get_filename(cls.name)
    
    @classmethod
    def read(cls):
        # The file might not exist: then we just return the defaults
        filename = LocalConfig._get_filename(cls.name)
        if os.path.exists(filename):
            return cls(dict(ConfigFile(filename).options))
        else:
            return cls()
        
    def __getattr__(self, att):
        if att in self.options:
            return self.options[att]
        else:
            raise AttributeError, "local conf '%s' does not specify an "\
                "option '%s'" % (self.name, att)
