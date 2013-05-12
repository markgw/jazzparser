"""Modality hierarchy for the jazz grammars.

This provides classes for defining a hierarchy of modalities that 
will be used in a particular version of the grammar. This is not 
formalism-specific, since the hierarchy itself is entirely defined 
by the XML, even though some formalisms don't use modalities at all.

This also provides an abstract class the slashes with modalities on 
them should inherit from.

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

from xml.dom import Node

class ModalityTreeNode(object):
    """
    A node in the modality tree.
    
    """
    def __init__(self, modality, children=None):
        self.modality = modality
        if children is None:
            children = []
        self.children = children
        
    def contains(self, modality):
        """
        This node contains its own modality and the modalities in all 
        of its subtrees.
        """
        if self.modality == modality:
            # Base case: X always contains X
            return True
        else:
            # X also contains X if it generalizes X
            return self.generalizes(modality)
        
    def generalizes(self, modality):
        """
        This node generalizes anothe modality if the other modality is 
        to be found in any of the nodes in its subtrees.
        """
        for child in self.children:
            if child.contains(modality):
                return True
        # Modality not found in any subtrees
        return False
        
    def __str__(self):
        symbol = "%s" % self.modality
        if symbol == "":
            symbol = "NONE"
        if len(self.children):
            return "<%s: %s>" % (symbol, 
                                 ", ".join(["%s" % child for child in self.children]))
        else:
            return symbol
    
    def find(self, modality):
        """
        Returns a list of all the nodes in this tree (including this 
        node) with the given modality.
        """
        if self.modality == modality:
            found = [self]
        else:
            found = []
        found.extend(sum([child.find(modality) for child in self.children], []))
        return found
    
    @staticmethod
    def from_dom(xml):
        """
        Builds a modality tree node from its DOM XML representation.
        """
        if xml.tagName != "modality":
            from jazzparser.grammar import GrammarReadError
            raise GrammarReadError, "Tried to read a modality node from a %s tag" % xml.tagName
        if not xml.hasAttribute("symbol"):
            from jazzparser.grammar import GrammarReadError
            raise GrammarReadError, "A modality node must have a \"symbol\" attribute"
        modality = xml.getAttribute("symbol")
        child_nodes = [node for node in xml.childNodes if node.nodeType == Node.ELEMENT_NODE and node.tagName == "modality"]
        children = [ModalityTreeNode.from_dom(child) for child in child_nodes]
        return ModalityTreeNode(modality, children)

class ModalityTree(object):
    """
    The tree is a DAG which defines a hierarchy of categories. If a 
    node Y is reachable from X, X generalizes Y. Modality Y can 
    therefore be used anywhere where an X modality is required, since 
    Y is a specialized type of X.
    
    """
    def __init__(self, root_nodes=None):
        if root_nodes is None:
            root_nodes = []
        self.root_nodes = root_nodes
        
    def contains(self, modality):
        return reduce(lambda x,y: x and y, [child.contains(modality) for child in self.root_nodes])
        
    def __str__(self):
        return "<%s>" % ", ".join(["%s" % node for node in self.root_nodes])
        
    def accepts(self, modality_general, modality_specific):
        """
        Returns true if, under the modality hierarchy represented by the 
        tree, modality_specific can be accepted where a modality_general 
        is required. Equivalently, checks whether modality_specific is 
        a specialization of modality_general (including equality).
        """
        general_nodes = self.find(modality_general)
        # Check all of these nodes to find one with modality_specific in a subtree
        for node in general_nodes:
            if node.contains(modality_specific):
                return True
        # No node found anywhere
        return False
        
    def find(self, modality):
        """
        Returns a list of all the nodes in this tree or subtrees with 
        the given modality.
        """
        return sum([child.find(modality) for child in self.root_nodes], [])
        
    @staticmethod
    def from_dom(xml):
        """
        Builds a modality tree from its DOM XML representation.
        """
        if xml.tagName != "modalities":
            from jazzparser.grammar import GrammarReadError
            raise GrammarReadError, "Tried to read modalities from a %s node" % xml.tagName
        child_nodes = [node for node in xml.childNodes if node.nodeType == Node.ELEMENT_NODE and node.tagName == "modality"]
        root_nodes = [ModalityTreeNode.from_dom(child) for child in child_nodes]
        return ModalityTree(root_nodes)

class ModalSlash(object):
    """
    A CCG slash class that wants modalities should inherit (first) from 
    the base Slash (or some subclass) and also from this, to add the 
    modality functionality.
    """
    def __init__(self, modality):
        if modality is None:
            modality = ""
        self.modality = modality
        
    def _extra_eq(self, other):
        """
        An additional requirement for equality.
        """
        return self.modality == other.modality
        
    def __post_string(self):
        """
        Add something to the end of the str to put the modality symbol on the slash.
        If you want some alternative slash representation, you're 
        welcome to override this in the slash subclass.
        """
        return "%s " % self.modality
    _post_string = property(__post_string)
    
    def __pre_string(self):
        return " "
    _pre_string = property(__pre_string)

class ModalComplexCategory(object):
    def set_slash_modality(self, slash_id, modality):
        """
        Look for the slash with id slash_id and set its modality.
        """
        if self.slash.id == slash_id:
            self.slash.modality = modality
        self.argument.set_slash_modality(slash_id, modality)
        self.result.set_slash_modality(slash_id, modality)

class ModalAtomicCategory(object):
    def set_slash_modality(self, slash_id, modality):
        pass
