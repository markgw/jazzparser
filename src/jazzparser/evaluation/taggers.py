"""Tagger evaluation routines.

@note: This was originally C{jazzparser.utils.stats}, but only ended up having 
tagger evaluation stuff in it.

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

from math import log
import logging

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

def tagger_entropy(input, grammar, tagger_class, correct_tags, options={}):
    """
    Given some input, a tagger and a list of correct tags, 
    computes the entropy of the tagger over the input, returning a tuple 
    of the total entropy and the number of chords that were involved 
    in the computation.
    
    The option dictionary options will be passed to the tagger.
    """
    # Do the tagging of the sequence
    tagger = tagger_class(grammar, input, options=options)
    def _get_word(i):
        if i >= len(correct_tags):
            return None
        else:
            return tagger.get_word(i)
    def _get_context(i):
        if i == 0:
            return "START *%s* %s" % (_get_word(0), _get_word(1))
        elif i == 1:
            return "START %s *%s* %s" % (_get_word(0), _get_word(1), _get_word(2))
        else:
            return "%s %s *%s* %s" % (_get_word(i-2), _get_word(i-1), _get_word(i), _get_word(i+1))
    # Compute the entropy for every chord
    total_entropy = 0.0
    total_chords = 0
    for i in range(tagger.input_length):
        # Don't include chords that aren't annotated - we could never get them right
        if correct_tags[i] not in ["", "?"]:
            # The tag is actually the root and the schema, but the list of 
            #  correct tags only includes the schema
            correct = (_get_word(i).root, correct_tags[i])
            probability = tagger.get_tag_probability(i, correct)
            if probability == 0.0:
                # Should be -inf
                # What to do?
                # Just give it a very small probability to fudge the calculations
                # This is effectively giving the model a very naive smoothing
                logger.error("The correct tag (%s) was given 0 probability by the tagger. Context: %s. Assigning a very small probability instead." % (correct_tags[i], _get_context(i)))
                probability = float('1e-50')
            entropy = log(probability, 2)
            total_entropy += entropy
            total_chords += 1
    total_entropy = -1 * total_entropy
    return (total_entropy, total_chords)

def tagger_agreement(input, grammar, tagger_class, correct_tags, options={}, confusion_matrix=None, topn=1):
    """
    Like tagger_entropy, but instead of computing the entropy computes 
    the proportion of top tags assigned that agree with the gold 
    standard.
    
    The option dictionary options will be passed to the tagger.
    
    Optionally puts a confusion matrix in the dictionary given in 
    confusion_matrix. This is a dictionary keyed by correct tags whose 
    values are dictionaries keyed by the incorrect tags that were 
    confused for them, whose values are a count of the confusions.
    
    Returns a tuple (number_agreeing, number_compared).
    
    """
    # Do the tagging of the sequence
    tagger = tagger_class(grammar, input, options=options)
    # Compute the entropy for every chord
    total_agreeing = 0
    total_chords = 0
    
    # Get all the spans the tagger can give us
    spans = tagger.get_signs(offset=0)
    added = len(spans)
    offset = 1
    while added > 0:
        new_spans = tagger.get_signs(offset=offset)
        added = len(new_spans)
        spans.extend(new_spans)
        offset += 1
    # Look for all the length 1 spans: single-word categories
    word_signs = {}
    for (start,end,sign) in spans:
        if end == start + 1:
            word_signs.setdefault(start, []).append(sign)
    
    for i in range(tagger.input_length):
        # Don't include chords that aren't annotated - we could never get them right
        if correct_tags[i] not in ["", "?"]:
            tags = word_signs.get(i, [])
            if len(tags) == 0:
                # Nothing returned by the tagger - must be wrong
                assigned_tag = None
            else:
                tags = [schema for __,(root,schema),__ in tags]
                assigned_tag = tags[0]
            # Count as correct if the correct tag is in the top n returned
            tags = tags[:topn]
            if correct_tags[i] in tags:
                # Got the correct one!
                total_agreeing += 1
                
            # Keep a record of what tags were confused if the top tag wasn't right
            if confusion_matrix is not None and correct_tags[i] != assigned_tag:
                conf = confusion_matrix.setdefault(correct_tags[i], {})
                conf.setdefault(assigned_tag, 0)
                # Increment the count of this particular confusion by one
                conf[assigned_tag] += 1
            total_chords += 1
    return (total_agreeing, total_chords)
