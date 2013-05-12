"""Grammar processing for the Jazz Parser.

This module is used to read the XML grammar files for the parser.
They are stored in the OpenCCG grammar format (roughly). This 
provides the interface to the grammar and the formalism for the parser 
and tagger.

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

import xml.dom.minidom
from jazzparser.formalisms.base.modalities import ModalityTree, \
                                ModalityTreeNode
from jazzparser.utils.domxml import attrs_to_dict, remove_unwanted_elements, \
                                get_single_element_by_tag_name
from jazzparser.utils.chords import generalise_chord_name
from jazzparser.data import Chord
from jazzparser.data.db_mirrors import Chord as DbChord
from jazzparser.formalisms import FORMALISMS
from jazzparser.formalisms.loader import get_default_formalism, get_formalism, \
                                FormalismLoadError

import logging, os, copy
import settings

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class Grammar(object):
    """
    Represents a grammar read in from an XML grammar file.
    Initialised with the location of the XML file.
    Can be consulted to retrieve lexical entries in the grammar.
    
    """
    ######### All public attributes #########
    # These are all create set when the class is instantiated, but are 
    # here so they can be fully documented.
    formalism = None
    """
    Formalism definition (L{jazzparser.formalisms.FormalismBase}) for the 
    formalism used by the grammar instance.
    
    Always set.
    
    """
    grammar_file = None
    """
    Path to the grammar.xml file from which the grammar definition was loaded.
    
    Always set.
    
    """
    literal_functions = None
    """
    Dictionary of builtin semantic literal functions.
    
    May be None.
    
    @deprecated: Only used in very early versions of the grammar. Left here
    for backwards compatibility. May be removed altogether soon.
    
    """
    families = None
    """
    Dictionary of lexical entry families (each a list of lexical signs), 
    keyed by POS.
    
    """
    inactive_families = None
    """
    Like families. Dictionary of families defined in the XML but marked as 
    inactive in their definition.
    
    Always a list. May be empty.
    
    """
    morphs = None
    """
    List of morph entries (L{MorphItem}). Mapping from word classes to 
    families. You probably don't want to access this directly usually, but 
    to use L{Grammar}'s methods like L{get_signs_for_word}.
    
    """
    morph_items = None
    """
    Same as L{morphs}, but a dictionary indexed by the word attribute 
    (identifier of word or word class) for easy lookup.
    
    """
    modality_tree = None
    """
    Instance of L{jazzparser.formalisms.base.modalities.ModalityTree} 
    representing the hierarchical structure of modalities used in this grammar.
    
    """
    rules = None
    """
    List of all the rules used by the grammar. These are instances of the 
    rule classes, instantiated with the correct parameters and ready to apply 
    to signs. Does not include lexical rules: see L{lexical_rules}.
    
    """
    unary_rules = None
    """
    List of unary rules. Subset of L{rules}.
    
    May be empty, but should always be a list.
    
    """
    binary_rules = None
    """
    List of binary rules. Subset of L{rules}.
    
    May be empty, but should always be a list.
    
    """
    rules_by_name = None
    """
    Dictionary of rules, containing same entries as L{rules}, keyed by 
    the internal_name attribute. There should not be more than one rule 
    instance with the same internal name. If multiple are created when the 
    grammar is instantiated, a L{GrammarReadError} will be raised.
    
    """
    lexical_rules = None
    """
    List of special unary rules that are applied to lexical families when the 
    grammar is instantiated to expand the lexicon. The lexicon will then 
    include all the original lexical entries, plus any results of applying 
    these rules to them.
    
    Empty list if no lexical rules are given.
    
    """
    chord_classes = None
    """
    Dict of L{ChordClass} objects, indexed by name.
    
    """
    #########################################
    
    def __init__(self, grammar_name=None):
        """ 
        Creates a new grammar by reading from an XML grammar file.
        
        Words (morph items) are stored in morph_items.
        Families (lexical families) are stored in families.
        
        Instantiate this directly only if you want, for some reason, to be sure 
        of getting a new instance of Grammar. Most of the time, you can 
        load a named grammar using L{get_grammar}, which will cache already 
        loaded grammars and return the same instance again if you ask for the 
        same name.
        
        @type grammar_name: string
        @param grammar_name: name of the grammar definition to be loaded. 
            Call L{get_grammar_names} for a list of available grammars. If 
            None, loads the default grammar.
        
        """
        if grammar_name is None:
            grammar_name = settings.DEFAULT_GRAMMAR
        self.name = grammar_name
        
        filename_base = os.path.join(settings.GRAMMAR_DATA_DIR, grammar_name)
        self.grammar_file = os.path.join(filename_base, "grammar.xml")
        # Read in the grammar
        logger.debug("Grammar: %s" % self.grammar_file)
        
        # Read in the XML from the file
        self.grammar_dom = xml.dom.minidom.parse(self.grammar_file)
        
        grammar_tag = get_single_element_by_tag_name(self.grammar_dom, "grammar")
        # Get a named formalism, or the default one
        formalism_attr = grammar_tag.attributes.getNamedItem("formalism")
        if formalism_attr is None:
            formalism = get_default_formalism()
        else:
            formalism_name = str(formalism_attr.value)
            try:
                formalism = get_formalism(formalism_name)
            except FormalismLoadError:
                logger.error("The formalism '%s' does not exist. Possible "\
                    "formalisms are: %s" % (formalism_name, ", ".join(FORMALISMS)))
                raise
        self.formalism = formalism
        
        ###############################
        ### Reading in the lexicon
        lex_tag = get_single_element_by_tag_name(self.grammar_dom, "lexicon")
        lexicon_file = os.path.join(filename_base, lex_tag.attributes.getNamedItem("file").value)
        logger.debug("Lexicon: %s" % lexicon_file)
        # Read in the lexicon
        self.lexicon_dom = xml.dom.minidom.parse(lexicon_file)
        
        ###############################
        ### Reading in the words
        morph_tag = get_single_element_by_tag_name(self.grammar_dom, "morphology")
        morph_file = os.path.join(filename_base, morph_tag.attributes.getNamedItem("file").value)
        logger.debug( "Morphology: %s" % morph_file)
        # Read in the lexicon
        self.morph_dom = xml.dom.minidom.parse(morph_file)
        
        ###############################
        ### Reading in the rules
        rules_tag = get_single_element_by_tag_name(self.grammar_dom, "rules")
        rules_file = os.path.join(filename_base, rules_tag.attributes.getNamedItem("file").value)
        logger.debug( "Rules: %s" % rules_file)
        # Read in the lexicon
        self.rules_dom = xml.dom.minidom.parse(rules_file)
        
        ###############################
        ### Reading in the functions list (only used for certain formalisms)
        functions_tag = get_single_element_by_tag_name(self.grammar_dom, "functions", optional=True)
        self.literal_functions = {}
        available_funs = formalism.literal_functions
        if functions_tag is not None:
            functions_file = os.path.join(filename_base, functions_tag.attributes.getNamedItem("file").value)
            logger.debug( "Functions: %s" % functions_file)
            # Read in the functions from the XML
            functions_dom = xml.dom.minidom.parse(functions_file)
            functions_xml = get_single_element_by_tag_name(functions_dom, "functions")
            functions = remove_unwanted_elements(functions_xml.getElementsByTagName("function"))
            # Try adding each of the functions, using the formalism's definitions
            for func_el in functions:
                func_name = func_el.attributes.getNamedItem("name").value
                if func_name in available_funs:
                    lit_fun = available_funs[func_name]
                    self.literal_functions[lit_fun.name] = lit_fun
                else:
                    raise GrammarReadError, "The literal function \"%s\" is not defined in the code for the %s formalism." % formalism.get_name()
        
        ###############################
        ### Reading in the modality hierarchy
        modalities_tag = get_single_element_by_tag_name(self.grammar_dom, "modalities", optional=True)
        if modalities_tag is not None:
            modalities_file = os.path.join(filename_base, modalities_tag.attributes.getNamedItem("file").value)
            logger.debug( "Modalities: %s" % modalities_file)
            # Read in the modalities
            self.modalities_dom = get_single_element_by_tag_name(xml.dom.minidom.parse(modalities_file), "modalities")
        else:
            self.modalities_dom = None
            
        ###############################
        ### Read in grammar-level meta data
        attrs = self.grammar_dom.getElementsByTagName("attr")
        # Initialize values that might not get set
        self.max_categories = None
        # Read in the values from the XML
        for el in attrs:
            name = el.getAttribute("name")
            value = el.getAttribute("value")
            # Check for all the attributes we recognize
            if name == "max_categories":
                self.max_categories = int(value)
        
        ###############################
        ### Prepare the morph word classes
        self.chord_classes = {}
        for entry in self.morph_dom.getElementsByTagName("class"):
            chord_class = ChordClass.from_dom(entry)
            self.chord_classes[chord_class.name] = chord_class
        
        # Maybe handle macros here. Not currently using them.
        
        ###############################
        ### Prepare lexical entries
        # Use a hash table for this too, indexed by pos
        self.families = {}
        self.inactive_families = []
        for family in self.lexicon_dom.getElementsByTagName("family"):
            fam = Family.from_dom(formalism, family)
            # Check whether the family has any entries and don't use it if not
            if len(fam.entries) > 0:
                # Put a new Family in the table for every family entry
                if fam.pos in self.families:
                    # Already an entry for this POS: add to the list
                    self.families[fam.pos].append(fam)
                else:
                    # No occurence of this POS yet: add a new list
                    self.families[fam.pos] = [fam]
            else:
                self.inactive_families.append(fam.pos)
        
        ###############################
        ### Prepare the morph items
        self.morphs = []
        for entry in self.morph_dom.getElementsByTagName("entry"):
            morph = MorphItem.from_dom(formalism,entry,self.chord_classes)
            self.morphs.append(morph)
        
        # Check that all the morphs correspond to a defined POS
        for morph in self.morphs:
            if morph.pos not in self.families:
                raise GrammarReadError, "morph item refers to undefined "\
                    "part-of-speech '%s': %s" % (morph.pos, morph.element.toxml())
                
        ###############################
        ### Prepare modalities hierarchy
        if self.modalities_dom:
            self.modality_tree = ModalityTree.from_dom(self.modalities_dom)
        else:
            # The modalities that existed before they were added to the 
            #  XML spec were just "c" and "."
            self.modality_tree = ModalityTree([
                                    ModalityTreeNode("", 
                                        [ModalityTreeNode("c")]) ])
            
        ###############################
        ### Prepare rules
        self.rules = []
        # Go through each different type of rule and add appropriate Rule subclasses
        rule_block = get_single_element_by_tag_name(self.rules_dom, "rules")
        
        for rule_tag in remove_unwanted_elements(rule_block.childNodes):
            rulename = rule_tag.tagName
            if rulename == "lexrules":
                # We'll deal with these later
                continue
            if rulename not in self.formalism.rules:
                raise GrammarReadError, "unknown rule '%s' (formalism "\
                    "defines: %s)" % (rulename, ", ".join(formalism.rules.keys()))
            ruleclass = self.formalism.rules[rulename]
            # Instantiate the rule, using options from the XML
            self.rules.append(ruleclass(modalities=self.modality_tree, grammar=self, **attrs_to_dict(rule_tag.attributes)))
            
        # Keep rules sorted by arity for ease of access
        self.unary_rules = []
        self.binary_rules = []
        for rule in self.rules:
            if rule.arity == 1:
                self.unary_rules.append(rule)
            elif rule.arity == 2:
                self.binary_rules.append(rule)
                
        # Index rules by internal name for ease of access
        self.rules_by_name = {}
        for rule in self.rules:
            if rule.internal_name in self.rules_by_name:
                # This shouldn't happen: each rule name should only be used once
                raise GrammarReadError, "instantiated two rules with the same "\
                    "internal name: %s. Either the XML has mistakenly "\
                    "instantiated the same thing twice, or the rule class has "\
                    "failed to give different varieties of the rule different "\
                    "names" % rule.internal_name
            self.rules_by_name[rule.internal_name] = rule
                
        # Optionally read in a lexrules element and expand the lexicon 
        #  using its entries
        self.lexical_rules = []
        lexrules_tag = get_single_element_by_tag_name(self.rules_dom, "lexrules", optional=True)
        if lexrules_tag is not None:
            for rule_tag in remove_unwanted_elements(lexrules_tag.childNodes):
                rulename = rule_tag.tagName
                if rulename not in self.formalism.rules:
                    raise GrammarReadError, "unknown lexical expansion "\
                        "rule '%s' (formalism defines: %s)" % \
                        (rulename, ", ".join(formalism.rules.keys()))
                ruleclass = self.formalism.rules[rulename]
                attrs = attrs_to_dict(rule_tag.attributes)
                # Make sure expanded category has a suffix to put on 
                #  POSs. If one isn't given, set a default.
                if "pos_suffix" in attrs:
                    pos_suffix = attrs["pos_suffix"]
                    del attrs["pos_suffix"]
                else:
                    pos_suffix = "_Rep"
                # Instantiate the rule, using any options given
                rule = ruleclass(modalities=self.modality_tree,
                                    grammar=self, 
                                    **attrs)
                rule.pos_suffix = pos_suffix
                # Can only use unary rules - check this one is
                if rule.arity != 1:
                    raise "can only use unary rules as lexical "\
                        "expansions. Tried to use %s, which has arity "\
                        "%d." % (rulename, rule.arity)
                self.lexical_rules.append(rule)
        # Use each lexical rule to expand the lexicon
        for rule in self.lexical_rules:
            for fam in sum(self.families.values(), []):
                for entry in fam.entries:
                    # Try apply the expansion rule to this entry
                    new_signs = rule.apply_rule([entry.sign])
                    if new_signs is not None and len(new_signs) > 0:
                        # Make a new POS for this expanded category
                        new_pos = "%s%s" % (fam.pos, rule.pos_suffix)
                        new_entries = [EntriesItem(self.formalism, "Expanded", new_sign) \
                                    for new_sign in new_signs]
                        new_family = Family(self.formalism, 
                                            new_pos, 
                                            new_pos,
                                            new_entries,
                                            chordfn=fam.chordfn,
                                            expanded=rule.internal_name)
                        self.families.setdefault(new_pos, []).append(new_family)
                        # Also create morph items for each of those 
                        #  that referenced the old unexpanded rules
                        for morph in [m for m in self.morphs if m.pos == fam.pos]:
                            self.morphs.append(
                                    MorphItem(
                                        self.formalism,
                                        copy.deepcopy(morph.words),
                                        new_pos,
                                        optional_minor=morph.optional_minor,
                                        chord_class=morph.chord_class))
        
        ###############
        # Index the morph items by word to make lookup easier
        self.morph_items = {}
        for morph in self.morphs:
            # If the pos is completely inactive in the lexicon, ignore this morph
            if not morph.pos in self.inactive_families:
                # Go through each of this morph's words
                for word in morph.words:
                    # Put a new MorphItem in the table for every entry
                    if word in self.morph_items:
                        # Already a list for this word: add to it
                        self.morph_items[word].append(morph)
                    else:
                        # First occurence of this word: add a new list
                        self.morph_items[word] = [morph]
        
        ###############
        # Read in an equivalence map if one is given for morph entries
        equiv_map_el = get_single_element_by_tag_name(self.morph_dom, "equivmap", optional=True)
        if equiv_map_el is not None:
            self.equiv_map = EquivalenceMap.from_dom(formalism, 
                                                     equiv_map_el, 
                                                     self.chord_classes, 
                                                     self.morphs)
        else:
            self.equiv_map = EquivalenceMap()
        
        ###########
        # Prepare a version of the family list for MIDI input
        self.midi_families = {}
        for pos,fams in self.families.items():
            new_fams = []
            for fam in fams:
                # Exclude any generated by lexical expansions, unless they're 
                #  tonic function
                if fam.expanded is not None and fam.chordfn != "T":
                    continue
                new_fams.append(fam)
            if new_fams:
                # Exclude any that are mapped onto another entry by an equivalence 
                #  mapping that changes the root
                if pos in self.equiv_map:
                    continue
                self.midi_families[pos] = new_fams
        
        ####### Debugging output
        logger.debug( "Read the following information from the grammar:")
        logger.debug( "Morphology:")
        logger.debug("\n".join(["%s: %s" % (word, ", ".join(["%s" % item.pos for item in items])) \
                         for word,items in self.morph_items.items()]))
        logger.debug("Lexicon:")
        logger.debug("\n".join([", ".join(["%s" % initem for initem in item]) \
                         for item in self.families.values()]))
        logger.debug("Rules:")
        logger.debug("\n".join(["  %s" % item for item in self.rules]))
        logger.debug("Lexical expansion rules:")
        logger.debug("\n".join(["  %s" % item for item in self.lexical_rules]))
        logger.debug("Modalities:")
        logger.debug("%s" % self.modality_tree)
        if len(self.literal_functions):
            logger.debug("Literal functions:")
            logger.debug("\n".join(["  %s: %s" % (name,val) for (name,val) in self.literal_functions.items()]))
    
    
    def get_signs_for_word(self, word, tags=None, extra_features=None):
        """
        Given a word string, returns a list of the possible signs
        (as CCGSigns) that the grammar can assign to it.
        word may also be a Chord object.
        For now, this assumes that the input is a single chord in
        roman numeral notation and that spelling issues have already
        been resolved (e.g. that 6s have been removed).
        
        If tags is given it should be a list of strings. Signs will be 
        restricted to those whose entry's tag name/POS is in the list.
        
        If you need to get an instantiated category from a lexical entry, 
        use the methods on L{EntriesItem} directly, or L{get_signs_for_tag}.
        
        """
        if isinstance(word, Chord):
            chord = word.to_db_mirror()
        elif isinstance(word, basestring):
            chord = Chord.from_name(word, permissive=True).to_db_mirror()
        elif isinstance(word, DbChord):
            chord = word
        else:
            raise GrammarLookupError, "Tried to get signs for a word of type "\
                "'%s': %s" % (type(word), word)
        # Get a chord type string to look up in the grammar
        chord_lookup = "X%s" % chord.type
        
        # Check whether we know this word
        if not chord_lookup in self.morph_items:
            # Word not recognised
            raise GrammarLookupError, "The word \"%s\" was not found in the "\
                "lexicon. (Looked up %s in %s)" \
                % (word, chord_lookup, 
                  ",".join(["%s" % item for item in self.morph_items.keys()]))
        # Get the list of interpretations of this word
        morphs = self.morph_items[chord_lookup]
        
        # Limit to tag list if one was given
        if tags is not None:
            morphs = [m for m in morphs if m.pos in tags]
        
        # Build a sign for each morph-family pair
        category_list = []
        for morph in morphs:
            # Look for families corresponding to the POS
            if not morph.pos in self.families:
                raise GrammarLookupError, "There is no family in the lexicon "\
                    "for the POS %s." % morph.pos
            for family in self.families[morph.pos]:
                # Build a CCGCategory for each entry in each family found
                for entry in family.entries:
                    sign = entry.sign.copy()
                    sign.tag = entry.tag_name
                    features = {
                        'root' : chord.root,
                        'morph' : morph
                    }
                    if extra_features is not None:
                        features.update(extra_features)
                    sign.apply_lexical_features(features)
                    category_list.append(sign)
        
        return category_list
        
    def get_sign_for_word_by_tag(self, word, tag, extra_features=None):
        """
        Returns a sign that can be assigned to the given word and that 
        has the given tag. If the word cannot have that tag, returns 
        None.
        """
        possibles = self.get_signs_for_word(word, tags=[tag], extra_features=extra_features)
        if len(possibles) == 0:
            return None
        else:
            return possibles[0]
    
    def get_signs_for_tag(self, tag, features):
        """
        Instantiates all the signs associated with a pos tag, using the given 
        dictionary of lexical features.
        
        """
        # Get all the entries for this tag
        entries = sum([fam.entries for fam in self.families[tag]], [])
        # Instantiate each lexically
        return [entry.get_lexical_sign(features, self) for entry in entries]
        
    def _get_entries_by_tag(self):
        """
        Gets all the tags recognised by the grammar. The tags are 
        returned as indices in a dict to the entry they represent.
        Note that these tags are unique identifiers of lexical items, 
        not pos tags.
        If you want entries indexed by POS tags, just use 
        grammar.families.
        """
        families = self.families
        entries = {}
        # Get all the lexical entries
        for pos in sorted(families.keys()):
            for fam in families[pos]:
                for entry in fam.entries:
                    entries[entry.tag_name] = entry
        return entries
    entries_by_tag = property(_get_entries_by_tag)
    
    def _get_pos_tags(self):
        """
        Convenience function to get the full list of POS tags allowed 
        by the grammar.
        
        """
        return self.families.keys()
    pos_tags = property(_get_pos_tags)
    
    def tag_to_function(self, tag):
        """
        Given a POS tag (roughly denoting a category), returns the 
        function of the chord that is implicit in this interpretation.
        If the tag is not in the grammar or a function is not given 
        for this tag in the lexicon, returns None.
        
        """
        if tag in self.families:
            return self.families[tag][0].chordfn
        else:
            return None
            
    def _get_tags_by_function(self):
        """
        Returns a dictionary mapping chord functions to POS tags (i.e.
        category family names).
        
        """
        return dict([(fam.chordfn,tag) for (tag,fam) in self.families.items()])
    tags_by_function = property(_get_tags_by_function)

##########################
## Class structure      ##
## for grammar from xml ##
##########################
#    Based on OpenCCG    #
class Family(object):
    """
    A lexical family.
    
    """
    def __init__(self, formalism, name, pos, entries, chordfn=None, expanded=None):
        """
        @type expanded: string or None
        @param expanded: if the family is generated by a lexical expansion 
            rule, should contain the name of the rule that generated it. 
            Otherwise None
        
        """
        self.formalism = formalism
        self.name = name
        self.pos = pos
        self.chordfn = chordfn
        self.entries = entries
        for entry in self.entries:
            entry.family = self
        self.expanded = expanded
    
    def __str__(self):
        return "<Family: \"%s\", \"%s\">%s</Family>" % (self.name, self.pos, \
                "".join(["%s" % entry for entry in self.entries]))
                
    @staticmethod
    def from_dom(formalism, element):
        """
        Builds a Family instance from a DOM element read in from the 
        XML grammar definition.
        
        """
        name = element.attributes.getNamedItem("name").value
        pos = element.attributes.getNamedItem("pos").value
        # The chordfn attr is optional, but we hope it's given for everything
        chordfn = element.attributes.getNamedItem("chordfn")
        if chordfn is None:
            # Not given, just use None so it's clear where it came from
            chordfn = None
        else:
            chordfn = chordfn.value
        # No need to read "closed" attr, since all families are closed
        # Same applies to "member" elements.
        
        entries = []
        # Create an Entry instance for every entry child
        for entry in element.getElementsByTagName("entry"):
            entry = EntriesItem.from_dom(formalism,entry)
            # Only use the entry if it's active
            if entry.active:
                entries.append(entry)
        
        return Family(formalism,
                      name,
                      pos,
                      entries,
                      chordfn=chordfn)
        
class MorphItem(object):
    """
    A morphological item - a word. Stores the word and the POS.
    Words are stored as strings, unlike in OpenCCG. We don't need all the 
    extra information about words that OpenCCG holds.
    
    The word field stores a list of strings, defining all the words
    represented by this morph item. In the case of a 
    C{<entry pos="POS" word="WORD"/>} item, this is a single word, 
    but in the case of a C{<entry pos="POS" class="CLASS"/>}
    item, this is all the words contained in the class CLASS.
    
    The argument classes should be a dictionary mapping class names to
    L{ChordClass} objects, for all the classes that have been
    read in for the grammar.
    
    """
    def __init__(self, formalism, words, pos, optional_minor=None, 
                    chord_class=None, mark_class=True):
        self.formalism = formalism
        self.words = words
        self.pos = pos
        self.optional_minor = optional_minor
        self.chord_class = chord_class
        if mark_class:
            # Mark the chord class to indicate that it was used by a morph item
            if chord_class is not None:
                chord_class.used = True
    
    def __str__(self):
        return "<MorphItem: %s>" % self.desc
    
    def __repr__(self):
        return str(self)
        
    def __get_desc(self):
        if self.chord_class is not None:
            return "cls %s := %s" % (self.chord_class, self.pos)
        else:
            return "%s := %s" % \
                (",".join(["%s" % word for word in self.words]), self.pos)
    desc = property(__get_desc)
            
    @staticmethod
    def from_dom(formalism, element, classes, mark_class=True):
        """
        Builds a MorphItem instance from a DOM XML specification.
        
        """
        word_attr = element.attributes.getNamedItem("word")
        if word_attr is not None:
            words = [word_attr.value]
            chord_class = None
        else:
            # Must be a class
            class_attr = element.attributes.getNamedItem("class")
            if class_attr is None:
                raise GrammarReadError, "Morph item has no word or class attribute"
            class_name = class_attr.value
            if not class_name in classes:
                raise GrammarReadError, "Referenced word class has not been defined"
            
            # Get word list from the class dictionary
            chord_class = classes[class_name]
            words = copy.deepcopy(chord_class.words)
            
        pos = element.attributes.getNamedItem("pos").value
        # Optional minors in the category may be forced to be major or minor, 
        #  or left ambiguous
        optmin_element = element.attributes.getNamedItem("optional_minor")
        if optmin_element is None:
            # No constraint is imposed: don't change the categories at all
            optional_minor = None
        else:
            optmin_val = optmin_element.value
            if optmin_val == "minor":
                # Force the optional minors to be minor
                optional_minor = True
            elif optmin_val == "major":
                # Force the optional minors to be major
                optional_minor = False
            else:
                # Not a valid value: don't impose a constraint
                logger.warning("An invalid value was found for the optional_"\
                               "minors attribute: %s. It must be \"major\" or "\
                               "\"minor\"" % optmin_val)
                optional_minor = None
        return MorphItem(formalism, words, pos, optional_minor=optional_minor, \
                            chord_class=chord_class, mark_class=mark_class)
    

class MacroItem(object):
    """
    Not yet implemented. Might be needed
    """
    pass


class EntriesItem(object):
    def __init__(self, formalism, name, sign, active=True, family=None):
        self.formalism = formalism
        self.family = family
        self.name = name
        self.active = active
        self.sign = sign
        
    def copy(self):
        return EntriesItem(self.formalism, 
                           copy.copy(self.name), 
                           self.sign.copy(),
                           active=self.active,
                           family=self.family)
    
    def __str__(self):
        return "<Entry: %s>" % self.category
    
    def __repr__(self):
        return str(self)
        
    def _get_tag_name(self):
        """ The unique tag name used for this lexical entry. """
        if self.family is None:
            return
        elif len(self.family.entries) == 1:
            return "%s" % self.family.name
        else:
            return "%s%s" % (self.family.name, self.name)
    tag_name = property(_get_tag_name)
    
    @property
    def category(self):
        """
        Alias for C{sign} attribute, for backwards compatibility.
        """
        return self.sign
    
    def get_lexical_sign(self, features, grammar):
        """
        The sign stored in the EntriesItem is an abstraction of the lexical 
        signs, or a lexical schema, that may be instantiated. This method 
        produces a specialised lexical sign using the lexical information.
        
        @type features: dict
        @param features: lexical features to be passed directly to the sign's 
            C{apply_lexical_features} method.
        
        """
        # Take a full copy of the prototypical sign
        sign = self.sign.copy()
        sign.tag = self.tag_name
        # Use the sign's own method to specialise it
        sign.apply_lexical_features(features)
        return sign
    
    @staticmethod
    def from_dom(formalism, element):
        name = element.attributes.getNamedItem("name").value
        active_el = element.attributes.getNamedItem("active")
        if active_el is not None:
            active = (active_el.value == "true")
        else:
            active = True
        sign = formalism.lexicon_builder(element)
        
        return EntriesItem(formalism, name, sign, active=active)

class ChordClass(object):
    """
    Representation of a chord class. Primarily, this links morph entries to 
    words.
    
    """
    def __init__(self, name, words, notes=[]):
        self.name = name
        self.words = words
        self.notes = notes
        self.used = False
        
    @staticmethod
    def from_dom(element):
        # Read off the attributes of the chord class
        name = element.attributes.getNamedItem("name").value
        word_string = element.attributes.getNamedItem("words").value
        words = word_string.split()
        # The notes list is technically optional, so default to no notes
        notes_el = element.attributes.getNamedItem("notes")
        if notes_el is None:
            notes = []
        else:
            notes = [int(note) for note in notes_el.value.split()]
        return ChordClass(name, words, notes=notes)
    
    def __str__(self):
        return self.name
        
    def __repr__(self):
        return "<ChordClass %s>" % self.name

class EquivalenceMap(dict):
    """
    A mapping from some of the morph entries to others via a root change.
    
    These define entries that can be considered equivalent to another 
    entry given a change of root. These exist to deal with inversions 
    that show up in chord sequences as different chords.
    
    E.g., a diminished chord may be written as if any of its notes 
    are the root, but this decision is made mainly on the basis of 
    what is easiest to read. Categories must be included to handle 
    each case for the chord grammar, but only one is required for a 
    model that can recognise inversions itself, such as a MIDI model.
    
    Here we tell such models how to construct a smaller set of 
    categories, so that they can understand annotated chord data.
    
    """
    def __init__(self, map={}):
        self.update(map)
        
    @staticmethod
    def from_dom(formalism, element, classes, morphs):
        equiv_map = {}
        # This should contain only <map> elements
        for map_entry in element.getElementsByTagName("map"):
            # There should be a "pos" attribute, giving the pos of the source
            pos = map_entry.attributes.getNamedItem("pos").value
            # This should contain exactly 1 equiv
            equiv = get_single_element_by_tag_name(map_entry, "equiv")
            
            if pos in equiv_map:
                raise GrammarReadError, "two equivalence mappings for the same "\
                    "morph entry: %s" % (source)
            
            # Read the map target element
            target = EquivalenceEntry.from_dom(formalism, equiv, classes, morphs)
            
            # Store this mapping
            equiv_map[pos] = target
        return EquivalenceMap(equiv_map)

class EquivalenceEntry(object):
    """
    Like a L{MorphItem}. Represents the target in a mapping from one morph 
    entry to another. For now this only works with chord class entries, 
    not words.
    
    """
    def __init__(self, target, root):
        self.target = target
        self.root = root
    
    def __str__(self):
        return "<Equiv: %d, %s>" % (self.root, self.target.desc)
    
    def __repr__(self):
        return str(self)
            
    @staticmethod
    def from_dom(formalism, element, classes, morphs):
        # First build a morph item, since this shares all of its attributes
        morph = MorphItem.from_dom(formalism, element, classes, mark_class=False)
        # Get the root specifier
        root = int(element.attributes.getNamedItem("root").value)
        
        # Check that a chord class was given
        if morph.chord_class is None:
            raise GrammarReadError, "equivalence mappings can only currently "\
                "map to morph entries that use chord classes"
        
        # Look for a morph entry that matches this
        for old_morph in morphs:
            if old_morph.chord_class == morph.chord_class and \
                    old_morph.pos == morph.pos:
                target = old_morph
                break
        else:
            # No matching morph entry was found
            raise GrammarReadError, "could not find a morph entry to use as "\
                "equivalence target matching pos=%s and chord_class=%s" % \
                    (morph.pos, morph.chord_class)
        return EquivalenceEntry(target, root)
    
def get_grammar_names():
    """ Returns a list of all valid grammar names. """
    dirs = [d for d in os.listdir(settings.GRAMMAR_DATA_DIR) if not d.startswith(".")]
    grammars = []
    # Work out which of these directories are valid(ish) grammars
    for name in dirs:
        dirname = os.path.abspath(os.path.join(settings.GRAMMAR_DATA_DIR, name))
        if not os.path.exists(dirname):
            continue
        if not os.path.isdir(dirname):
            continue
        if not os.path.exists(os.path.join(dirname, "grammar.xml")):
            continue
        grammars.append(name)
    return grammars

    
_loaded_grammars = {}

def get_grammar(name=None):
    """
    Returns an instance of L{Grammar} for the named grammar.
    
    This is like instantiating L{Grammar} with the grammar with the name 
    as an argument, but caches loaded grammars. If the named grammar has 
    been previously loaded, the same instance will be returned again.
    
    If you want to force a new instance, use C{Grammar(name)}. However, 
    most of the time there's no need, since Grammar is essentially a read-only 
    data structure.
    
    """
    if name is None:
        name = settings.DEFAULT_GRAMMAR
    if name not in _loaded_grammars:
        _loaded_grammars[name] = Grammar(name)
    return _loaded_grammars[name]

class GrammarReadError(Exception):
    """
    Thrown if there's a problem while reading the grammar description
    from the XML file. This will usually be because of missing elements
    or some such thing.
    """
    pass
    
class GrammarLookupError(Exception):
    """
    Raised if there are problems consulting the grammar.
    """
    pass
