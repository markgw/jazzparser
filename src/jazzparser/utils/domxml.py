"""Handy XML processing utility functions.

Various XML processing utilities, using minidom, that are used in 
various places throughout the code.

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

from xml.dom import minidom

class XmlReadError(Exception):
    pass

def attrs_to_dict(attrs):
	"""
	Converts a minidom NamedNodeMap that represents the attributes 
	of a node into a dictionary. The keys are attribute names.
	The values are the attributes' string values.
	"""
	return dict([(str(attr.name),attr.value) for attr in attrs.values()])

def remove_unwanted_elements(node_list):
    """
    Minidom node lists include entries for carriage returns, for 
    some reason. This function removes these from a list.
    
    """
    return [node for node in node_list \
            if (node.nodeType != minidom.Node.TEXT_NODE) and \
               (node.nodeType != minidom.Node.COMMENT_NODE)]

def get_single_element_by_tag_name(node, tag_name, optional=False):
    """
    Returns an element that is a child of the given node and that 
    has the tag name given. This method is used where it is assumed
    that one such tag exists.
    If there is none, an exception is 
    raised. If there is more than one, the first is returned.
    
    @return: the child of node with tag name tag_name
    
    """
    from jazzparser.grammar import GrammarReadError
    tags = node.getElementsByTagName(tag_name)
    if len(tags) == 0:
        if optional:
            return None
        else:
            raise XmlReadError, "No %s tag found" % tag_name
    
    return tags[0]

def require_attrs(node, attrs):
    """
    Checks for the existence of the named attributes on the given 
    node and raises an exception if they're not there.
    
    Returns a tuple of their values if they're all found.
    
    """
    return tuple([require_attr(node, attr) for attr in attrs])
    
def require_attr(node, attr):
    """
    Checks for the existence of the named attribute on the given 
    node and raises an exception if it's not there.
    
    Returns its value if it is there.
    
    """
    element = node.attributes.getNamedItem(attr)
    if element is None:
        raise XmlReadError, "required attribute '%s' was not found "\
            "on %s node: %s" % (attr, node.nodeName, node.toxml())
    return element.value
