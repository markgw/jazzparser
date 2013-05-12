#!/usr/bin/env ../jazzshell
"""
Loads a named grammar from XML files and prints out its contents in 
a readable form.

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

import sys, os
from optparse import OptionParser
from jazzparser.grammar import Grammar

def main():
    usage = "%prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-g", "--grammar", dest="grammar", action="store", help="load a grammar by name (defaults to the default grammar from the settings file)")
    parser.add_option("-l", "--lexicon", dest="lexicon", action="store_true", help="show lexicon")
    parser.add_option("-r", "--rules", dest="rules", action="store_true", help="show rules")
    parser.add_option("-m", "--morph", dest="morph", action="store_true", help="show morphological entries")
    parser.add_option("-o", "--modalities", dest="modalities", action="store_true", help="show modality hierarchy")
    parser.add_option("-a", "--attributes", dest="attributes", action="store_true", help="show other grammar attributes")
    options, arguments = parser.parse_args()
    
    if options.grammar:
        grammar = Grammar(options.grammar)
    else:
        grammar = Grammar()
        
    show_lexicon = options.lexicon
    show_rules = options.rules
    show_morph = options.morph
    show_modes = options.modalities
    show_attrs = options.attributes
    # If no section options given, show them all
    show_all = not any([show_rules, show_lexicon, show_morph, show_modes])
        
    if show_lexicon or show_all:
        print "== LEXICON =="
        for family in sorted(sum(grammar.families.values(), [])):
            print ">> Family '%s'" % family.name
            for entry in family.entries:
                print entry.category
        print
        
    if show_rules or show_all:
        print "== RULES =="
        for rule in grammar.rules:
            print rule
        print
    
    if show_morph or show_all:
        print "== MORPH =="
        for morph in sorted(grammar.morphs, key=lambda m:m.pos):
            print "%s => %s" % (", ".join(morph.words), morph.pos)
        print
        
    if show_modes or show_all:
        print "== MODALITIES =="
        print grammar.modality_tree
        print
        
    if show_attrs or show_all:
        print "== ATTRIBUTES =="
        print "Max categories: %s" % grammar.max_categories

if __name__ == "__main__":
    main()
