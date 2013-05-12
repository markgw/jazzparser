"""A more or less null tagger that assigns just a fixed sequence of tags.

This tagger should not be used in practice. It is for use in parsing 
annotated sequences to verify that the annotated derivation structure 
is possible and to produce the chart that that derivation structure 
would produce.

It is instantiated with a sequence of tags and, irrespective of the 
input (which can be None), returns only those tags. If the input is 
not None it should be a list of the same length as the tag list. You may 
want to include input chords so that the tree produced has a record 
of the chords at the leaves.

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

from jazzparser import settings
from jazzparser.utils.input import assign_durations, strip_input
from jazzparser.taggers import Tagger
from jazzparser.data import Fraction
from jazzparser.data.input import DbInput
from jazzparser.utils.options import ModuleOption, file_option

class PretaggedTagger(Tagger):
    """
    The input doesn't matter. Must be instantiated with a complete 
    set of tags. The tag list should contain lists of tags for each 
    word (usually each list will contain just one item). These are 
    what it will return.
    
    """
    COMPATIBLE_FORMALISMS = [
        'music_roman',
        'music_keyspan',
        'music_halfspan',
    ]
    TAGGER_OPTIONS = [
        ModuleOption('tags', filter=file_option, 
            help_text="File to get tag sequence from",
            usage="tags=X, where X a filename"),
    ]
    INPUT_TYPES = ['db', 'chords']
    
    def __init__(self, grammar, input, options={}, tags=None):
        if input is None:
            self.input = ["--"] * len(tags)
        else:
            self.input = input
        
        super(PretaggedTagger, self).__init__(grammar, input, options)
        
        if 'tags' in self.options and tags is None:
            # Load the tag sequence from a file
            self.tags = get_tags_for_input(input, self.options['tags'])
        else:
            if tags is None:
                raise ValueError, "PretaggedTagger must be supplied with a "\
                    "keyword argument 'tags' or a tagger option 'tags' "\
                    "to tell it what tags to return."
            if len(self.input) != len(tags):
                raise ValueError, "the input given to the PretaggedTagger "\
                    "was not the same length as the list of tags."
            self.tags = tags
        
        if len(self.tags) and type(self.tags[0]) == str:
            # These must be schemalabels, rather than signs
            # Resolve each one to a sign
            labels = list(self.tags)
            signs = []
            for label,word in zip(labels,input):
                # Retreive a sign from the grammar for this tag on this word
                sign = grammar.get_sign_for_word_by_tag(word, label)
                if sign is None:
                    raise ValueError, "could not get a sign for the tag '%s' "\
                        "on the word '%s'" % (label,word)
                signs.append([sign])
            self.tags = signs
    
    def get_signs_for_word(self, index, offset=0):
        if offset > 0:
            return []
        else:
            all_signs = self.tags[index]
            return [(sign, sign.tag, Fraction(1, len(all_signs))) for sign in all_signs]
            
    def get_word(self, index):
        return self.input[index]

class TagsFile(object):
    """
    A file format for storing a list of tags, potentially multiple tag lists.
    
    """
    def __init__(self, tags, filename="no-file"):
        self.filename = filename
        self.tags_by_id = (type(tags) == dict)
        self.tags = tags
        
    @staticmethod
    def from_file(filename):
        tags_by_id = None
        
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()
        
        tags = {}
        
        # Get a tag sequence from each line
        for line in lines:
            line = line.strip()
            line = line.rstrip("\n")
            if line:
                if line.startswith("id:"):
                    if tags_by_id == False:
                        # We've had a line without an id
                        raise IOError, "the tags file %s contains sequences with "\
                            "an id and without" % filename
                    line = line.lstrip("id:")
                    linetags = line.split()
                    # The first element is the id and should be an int
                    id = int(linetags.pop(0))
                    tags[id] = linetags
                    tags_by_id = True
                else:
                    if tags_by_id == True:
                        # We've had a line with an id
                        raise IOError, "the tags file %s contains sequences with "\
                            "an id and without" % filename
                    tags = line.split()
                    tags_by_id = False
        return TagsFile(tags, filename=filename)
        
    def to_file(self, filename):
        lines = []
        if self.tags_by_id:
            # Stored as dictionary of sequences by id
            for id,tags in self.tags.items():
                lines.append("id:%d %s" % (id," ".join(tags)))
        else:
            # Stored as a single list of tags
            lines.append(" ".join(self.tags))
        
        f = open(filename, 'w')
        try:
            f.write("\n".join(lines))
        finally:
            f.close()
        
    def get_tags_for_input(self, input):
        if type(input) == DbInput and \
                hasattr(input, "id") and \
                input.id is not None and \
                self.tags_by_id:
            # Use the tags for this sequence id
            if input.id not in self.tags:
                raise ValueError, "tags file %s has no tags for input id %d" \
                    % (self.filename, input.id)
            return self.tags[input.id]
        elif self.tags_by_id:
            # The tags are stored by id in the file, but the input has no id
            raise ValueError, "tags file %s stores tag sequences by id, but "\
                "the input %s has no id associated with it" \
                % (self.filename, input)
        else:
            return self.tags

def get_tags_for_input(input, tag_filename):
    """
    Convenience method that loads up a tags file and pulls out the tag 
    sequence for the DbInput.
    
    """
    tagsfile = TagsFile.from_file(tag_filename)
    return tagsfile.get_tags_for_input(input)
