"""Edit distance between chord sequences.

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

from jazzparser.utils.distance import levenshtein_distance, align

def chord_sequence_match_score(seq1, seq2):
    """
    Computes the edit distance between two chord sequences to score the 
    extent of the matching between the two sequences between 0 and 1.
    
    Each sequence should be a list of L{jazzparser.data.db_mirrors.Chord}s.
    The metric is key-independent. The distance will be tried for every 
    transposition of one of the sequences and the closest match will be 
    used.
    
    """
    costs = []
    for transpose in range(12):
        # Give a half-point to alignments of roots without labels or vice versa
        def _subst_cost(crd1, crd2):
            cost = 0
            if (crd1.root+transpose) % 12 == crd2.root:
                cost += -1
            if crd1.type == crd2.type:
                cost += -1
            return cost
        
        # Try aligning the two sequences
        align_cost = levenshtein_distance(seq1, seq2, 
                                          delins_cost=0, 
                                          subst_cost_fun=_subst_cost)
        costs.append((transpose,align_cost))
    
    transposition, align_cost = min(costs, key=lambda x:x[1])
    align_score = float(-align_cost) / 2
    
    # Compute f-score of optimal alignment
    precision = align_score / len(seq1)
    recall = align_score / len(seq2)
    f_score = 2.0 * precision * recall / (precision+recall)
    
    return f_score,transposition

def chord_sequence_alignment(seq1, seq2, transposition=0):
    """
    Performs the same alignment as L{chord_sequence_match_score}, but 
    returns the actual alignment of chords.
    
    The alignment assumes that the first sequence is transposed by 
    C{transposition}.
    
    """
    # Give a half-point to alignments of roots without labels or vice versa
    def _subst_cost(crd1, crd2):
        cost = 0
        if (crd1.root+transposition) % 12 == crd2.root:
            cost += -1
        if crd1.type == crd2.type:
            cost += -1
        return cost
    
    # Try aligning the two sequences
    alignment = align(seq1, seq2, delins_cost=0, subst_cost=_subst_cost)
    
    return alignment
