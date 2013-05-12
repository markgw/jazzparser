"""XML processing utilites for the music_halfspan formalism.

These include building internal representations from the XML grammar 
definitions.

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

import re, logging
from jazzparser.utils.chords import ChordError
from jazzparser.grammar import GrammarReadError
from .syntax import AtomicCategory, ComplexCategory, Slash, Sign, HalfCategory
from .semantics import Semantics, DummyLogicalForm, Leftonto, Variable, \
            LexicalCoordinate, multi_apply, multi_abstract, Rightonto, Now, \
            List
from jazzparser.utils.domxml import remove_unwanted_elements, \
                            require_attrs, require_attr

# Get the logger from the logging system
logger = logging.getLogger("main_logger")


def build_sign_from_node(element):
    """
    Given the XML element of a CCG sign, builds the internal 
    representation.
    
    """
    # Assume there's only one child we're interested in (the category)
    child_elements = remove_unwanted_elements(element.childNodes)
    cat_elem = child_elements[0]
    # Get the category structure from the category node
    gramcategory = build_category_from_node(cat_elem)
    
    lf_elems = element.getElementsByTagName("lf")
    if len(lf_elems) == 0 or len(remove_unwanted_elements(lf_elems[0].childNodes)) == 0:
        raise GrammarReadError, "No logical form found for entry: "\
                "%s. What is syntax without semantics?" % cat_elem.toxml()
        # Steedman, 2010 (private correspondence)
    lf_elem = lf_elems[0]
    lf_children = remove_unwanted_elements(lf_elem.childNodes)
    ## Get semantics from the lf node
    sems = build_lf_from_node(lf_children[0])
    if sems is None:
        raise GrammarReadError, "Could not build semantic " \
                "representation for %s." % lf_elem.toxml()
    sems = Semantics(sems)
    
    # Store the full category for this entry
    return Sign(gramcategory, sems)

def build_category_from_node(element):
    """
    Uses an XML DOM node that represents a CCG category (i.e. a structure
    of atomcats and complexcats) to build a CCG category in our internal
    representation.
    
    @return: a Category subclass that is the root of the category structure
    
    """
    halfcat_re = re.compile(r'^(?P<root>.+?)(\[(?P<functions>(T|D|S)(\|(T|D|S))*)\])?$')
    def _load_halfcat(name):
        """Try building a HalfCategory from this string"""
        match = halfcat_re.match(name)
        if match is None:
            raise GrammarReadError, "%s is not a valid half-category. Reading element %s." % (name, element.toxml())
        root = match.groupdict()['root']
        functions = match.groupdict()['functions']
        if functions is None:
            # Default to tonic
            functions = ["T"]
        else:
            functions = functions.split("|")
        return HalfCategory(root, functions)
    
    def _required_attr(el, name):
        attr_el = element.attributes.getNamedItem(name)
        if attr_el is None:
            raise GrammarReadError, "required attribute '%s': %s" % (name, el.toxml())
        return attr_el.value
    
    if (element.nodeName== "atomcat"):
        # Base case: atomic category
            
        # Read the from attribute
        root_name = _required_attr(element, "root")
        half_root = _load_halfcat(root_name)
        
        # All lexical tonic categories have the same start and end
        return AtomicCategory(half_root, half_root.copy())
    elif (element.nodeName == "complexcat"):
        # Complex category
        
        # Read the argument and result attributes
        arg_name = _required_attr(element, "arg")
        result_name = _required_attr(element,"res")
        direction = _required_attr(element,"dir")
        if (direction == "/"):
            forward = True
        elif (direction == "\\"):
            forward = False
        else:
            raise GrammarReadError, "%s is not a valid slash direction: should be / or \\" % direction
        
        mode_el = element.attributes.getNamedItem("modality")
        # Default to modality=None if one hasn't been set and let Slash default
        if mode_el is not None:
            modality = mode_el.value
        else:
            modality = None
        slash = Slash(forward, modality=modality)
        
        result = _load_halfcat(result_name)
        argument = _load_halfcat(arg_name)
        
        category = ComplexCategory(result, slash, argument)
        return category
    else:
        # Not recognised as an atomcat or complexcat
        raise GrammarReadError, "Unrecognised category node %s" % element
    
def build_lf_from_node(elem):
    """
    Given the "lf" node of a lexical entry, builds a logical form
    representing it internally.
    
    @return: a LogicalForm built from the node
    
    """
    name = elem.nodeName
    if name == "point":
        # A point in the (as yet equally tempered) tonal space, 
        #  relative to the chord of the chord
        x,y = require_attrs(elem, ["x", "y"])
        x,y = int(x), int(y)
        
        if not 0 <= x < 4 or not 0 <= y < 3:
            raise GrammarReadError, "equal temperament tonal space "\
                "points should be between (0,0) and (3,2): got (%d,%d)" \
                    % (x,y)
        # Shouldn't be any children
        subnodes = remove_unwanted_elements(elem.childNodes)
        if len(subnodes) != 0:
            raise GrammarReadError, "A tonal space point cannot have children."
        
        return LexicalCoordinate((x,y))
    elif name == "list":
        # A path of points (usually just one point)
        subnodes = remove_unwanted_elements(elem.childNodes)
        
        children = [build_lf_from_node(node) for node in subnodes]
        return List(children)
    elif name == "leftonto":
        # A leftonto predicate literal
        
        # Shouldn't be any children
        subnodes = remove_unwanted_elements(elem.childNodes)
        if len(subnodes) != 0:
            raise GrammarReadError, "A leftonto predicate cannot "\
                    "have children."
        
        return Leftonto()
    elif name == "rightonto":
        # A rightonto predicate literal
        
        # Shouldn't be any children
        subnodes = remove_unwanted_elements(elem.childNodes)
        if len(subnodes) != 0:
            raise GrammarReadError, "A rightonto predicate cannot "\
                    "have children."
        
        return Rightonto()
    elif name == "now":
        # A now predicate literal
        
        # Shouldn't be any children
        subnodes = remove_unwanted_elements(elem.childNodes)
        if len(subnodes) != 0:
            raise GrammarReadError, "A now predicate cannot "\
                    "have children."
        
        return Now()
    elif name == "abstraction":
        # Lambda abstraction
        # All children except the last are abstracted variables
        subnodes = remove_unwanted_elements(elem.childNodes)
        if len(subnodes) < 2:
            raise GrammarReadError, "No subexpression in lambda "\
                    "abstraction: %s" % elem.toxml()
        variables = [build_lf_from_node(node) for node in subnodes[:-1]]
        for var in variables:
            if not isinstance(var, Variable):
                raise GrammarReadError, "Can only abstract over "\
                    "variables, not %s" % type(var).__name__
        expression = build_lf_from_node(subnodes[-1])
        
        return multi_abstract(*tuple(variables+[expression]))
    elif name == "application":
        # Function application
        # Recursively build functor and argument LFs
        subnodes = remove_unwanted_elements(elem.childNodes)
        if len(subnodes) < 2:
            raise GrammarReadError, "Function application needs to "\
                    "have at least two subnodes"
        children = [build_lf_from_node(node) for node in subnodes]
        
        return multi_apply(*children)
    elif name == "variable":
        # Variable reference
        varid = require_attr(elem, "name")
        
        return Variable(varid)
    else:
        raise GrammarReadError, "Got invalid node %s in LF" % name
