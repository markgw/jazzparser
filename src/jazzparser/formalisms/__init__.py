"""All available formalism modules.

A formalism defines a bundle of grammar components that may interact 
with each other: syntax, semantics, rules, modalities, etc. Each module 
may assume that the others of the same formalism are all in use at once, 
but no code outside the formalism may depend on anything 
formalism-specific.
This means a full formalism module can be added and may specify all the 
details of how the syntax, semantics and rules behave and interact.

This structure has allowed me to develop radically different versions of 
the musical CCG formalism in parallel. However, there currently exists only one 
formalism.

The base package contains a lot of useful base classes for code that is 
either common to all formalisms, or that is frequently used across many 
formalisms.

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

import sys

# Make this easily accessible here
from loader import get_formalism, get_default_formalism
from jazzparser.utils.options import ModuleOption, options_help_text
from jazzparser import settings

# List all formalisms here
FORMALISMS = [
    'music_halfspan',
]

class FormalismBase(object):
    """
    Superclass of all Formalism structures. These tie together all the 
    components of a formalism in an easily accessible way: rules, 
    syntax, semantics, etc.
    """
    literal_functions = {}
    shell_tools = []
    
    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            # Skip all this when the base class if created
            if name != "FormalismBase":
                # Initialize all the output options
                # If they're never set by whatever script is running, this 
                #  ensures that their default values are available
                formalism = cls.get_name()
                opts = ModuleOption.process_option_dict({}, cls.output_options)
                # Store this so it's globally available to the formalism
                settings.OPTIONS.OUTPUT[formalism] = opts
    
    output_options = []
    """
    ModuleOptions that can be used to set global settings that will 
    affect the formatting of output.
    
    Don't use any required options. All options must be able to be initialized 
    to a default.
    
    The values of the options will be set to their default when the formalism 
    class is first encountered. Call L{process_output_options} to customize 
    the options.
    
    Although the options are globally available for simplicity of access, 
    you should only ever access them from within formalism-specific code in 
    practice.
    
    """
    
    @classmethod
    def process_output_options(cls, optdict):
        """
        Makes output options globally available, based on a dictionary.
        
        @see: L{output_options}.
        
        """
        formalism = cls.get_name()
        opts = ModuleOption.process_option_dict(optdict, cls.output_options)
        settings.OPTIONS.OUTPUT[formalism] = opts
        
    @classmethod
    def cl_output_options(cls, string):
        """
        Convenience method so you don't have to do this lots of times over.
        
        Take a string of output options from the command line and set the 
        output options from it.
        
        Should only be used in command-line scripts.
        
        """
        if string is not None and string.lower() == "help":
            print "Available output options"
            print "========================"
            print options_help_text(cls.output_options)
            sys.exit(0)
        optdict = ModuleOption.process_option_string(string)
        cls.process_output_options(optdict)
    
    semantics_to_coordinates = None
    """Function to generate a list of coordinates from a parse result (semantic part)."""
    
    @classmethod
    def sign_to_coordinates(cls, sign):
        """
        Function to generate a list of coordinates from a parse result.
        By default, uses C{semantics_to_coordinates} applied to the semantic 
        part of the sign.
        
        """
        return cls.semantics_to_coordinates(sign.semantics)
    
    semantics_distance_metrics = []
    """
    List of distance metrics available in the formalism. Each item is a 
    subclass of L{jazzparser.formalisms.base.semantics.distance.DistanceMetric}.
    
    """
    PcfgModel = None
    """
    Pcfg model class appropriate for the formalism.
    
    """
    
    @classmethod
    def get_name(cls):
        return cls.__module__.rpartition(".")[2]
        
    class Syntax:
        """
        Formalisms should define override this nested class with their 
        own, which will specify values for these attributes.
        """
        Sign = None
        ComplexCategory = None
        AtomicCategory = None
        DummyCategory = None
        
        @classmethod
        def is_category(cls, obj):
            return isinstance(obj, cls.Category)
            
        @classmethod
        def is_complex_category(cls, obj):
            return isinstance(obj, cls.ComplexCategory)
        
        @classmethod
        def is_atomic_category(cls, obj):
            return isinstance(obj, cls.AtomicCategory)
            
        @staticmethod
        def merge_equal_signs(existing_sign, new_sign):
            pass
        
    class Semantics:
        """
        Formalisms should define override this nested class with their 
        own, which will specify values for these attributes.
        """
        Semantics = None
        apply = None
        compose = None
        
    class Evaluation:
        """
        Functions for evaluating tonal space paths and parse results.
        
        """
        tonal_space_alignment_costs = None
        """
        Performs an alignment of two tonal space paths and returns a dictionary 
        of costs incurred in the optimal alignment.
        The values must include 'deletions', 'substitutions' and 'insertions' 
        and may also include more fine-grained information, like 'root_subs' 
        and 'function_subs'.
        
        """
        tonal_space_distance = None
        """
        Performs an alignment of two tonal space paths and computes a distance 
        metric between them. The metric is assumed to be based on edit distance, 
        so to have a minimum value of 0 (identity) and maximum the length of 
        the longer sequence.
        
        """
