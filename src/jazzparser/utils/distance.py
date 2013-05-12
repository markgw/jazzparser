"""Algorithms for commonly-used distance metrics.

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

def levenshtein_distance(seq1, seq2, delins_cost=1, subst_cost_fun=None):
    """
    Compute the Levenshtein distance between two sequences.
    By default, will compare the elements using the == operator, but 
    any binary function can be given as the equality argument.
    
    delins_cost is the cost applied for deletions and insertions.
    
    subst_cost_fun is a binary function that gives the cost to substitute 
    the first argument with the second. If not given, a cost of delins 
    is used for any substitution.
    
    """
    if subst_cost_fun is None:
        subst_cost_fun = lambda x,y: 0 if x==y else delins_cost
        
    # Simple cases: empty sequences
    if len(seq1) == 0:
        return len(seq2) * delins_cost
    elif len(seq2) == 0:
        return len(seq1) * delins_cost
    
    # Create a table with m+1 rows and n+1 columns
    dist = []
    for i in range(len(seq1)+1):
        dist.append([None] * (len(seq2)+1))
    
    for i in range(len(seq1)+1):
        dist[i][0] = i*delins_cost      # deletion
    for j in range(len(seq2)+1):
        dist[0][j] = j*delins_cost      # insertion
    
    for j in range(1, len(seq2)+1):
        for i in range(1, len(seq1)+1):
            dist[i][j] = min(
                            dist[i-1][j] + delins_cost,  # deletion
                            dist[i][j-1] + delins_cost,  # insertion
                            dist[i-1][j-1] + subst_cost_fun(seq1[i-1], seq2[j-1])    # substitution
                            )
    
    return dist[-1][-1]

def levenshtein_distance_with_pointers(seq1, seq2, delins_cost=1, subst_cost_fun=None):
    """
    Compute the Levenshtein distance between two sequences.
    This does the same thing as levenshtein_distance, but stores 
    pointers to indicate what alignments gave the costs and returns
    the full cost matrix, plus the pointer matrix.
    
    C{seq2} is aligned with C{seq1}: that is, a deletion indicates that 
    C{seq1} moves on a cell without a corresponding cell in C{seq2}.
    
    """
    if subst_cost_fun is None:
        subst_cost_fun = lambda x,y: 0 if x==y else delins_cost
        
    # Simple cases: empty sequences
    if len(seq1) == 0:
        return len(seq2) * delins_cost
    elif len(seq2) == 0:
        return len(seq1) * delins_cost
    
    # Create a table with m+1 rows and n+1 columns
    pointers = []
    dist = []
    for i in range(len(seq1)+1):
        dist.append([None] * (len(seq2)+1))
        pointers.append([None] * (len(seq2)+1))
    
    for i in range(len(seq1)+1):
        dist[i][0] = i*delins_cost      # deletion
        pointers[i][0] = 'D'
    for j in range(len(seq2)+1):
        dist[0][j] = j*delins_cost      # insertion
        pointers[0][j] = 'I'
    
    for j in range(1, len(seq2)+1):
        for i in range(1, len(seq1)+1):
            dist[i][j],pointers[i][j] = min(
                            (dist[i-1][j] + delins_cost, 'D'),  # deletion
                            (dist[i][j-1] + delins_cost, 'I'),  # insertion
                            (dist[i-1][j-1] + subst_cost_fun(seq1[i-1], seq2[j-1]), 'S'),    # substitution
                            key=lambda x:x[0])
    
    return dist, pointers

def align(seq1, seq2, delins_cost=1, subst_cost=None, dist=False):
    """
    Finds the optimal alignment of the two sequences using Levenshtein 
    distance and traces back the pointers to find the alignment. Returns 
    a list of pairs, containing the points from the two lists. 
    
    In the case of a substitution, it will contain the two points that were 
    aligned. In the case of an insertion, the first value will be C{None}
    and the second the inserted value. In the case of a deletion, the 
    second value will be C{None} and the first the deleted value.
    
    Note that the pair of values in the case of a substitution may be 
    equal - an alignment - or not - a substitution - depending on the 
    substitution cost function.
    
    @type dist: bool
    @param dist: return a tuple of the alignment and the dist
    
    """
    dists,pointers = levenshtein_distance_with_pointers(
                                seq1, 
                                seq2,
                                delins_cost=delins_cost,
                                subst_cost_fun=subst_cost)
    # We now have the matrix of costs and the pointers that generated 
    #  those costs.
    # Trace back to find out what costs were incurred in the optimal 
    #  alignment
    operations = []
    # Start at the top right corner
    i,j = (len(dists)-1), (len(dists[0])-1)
    while not i == j == 0:
        if pointers[i][j] == "I":
            operations.append((None,seq2[j-1]))
            j -= 1
        elif pointers[i][j] == "D":
            operations.append((seq1[i-1],None))
            i -= 1
        else:
            operations.append((seq1[i-1],seq2[j-1]))
            j -= 1
            i -= 1
    
    operations.reverse()
    
    if dist:
        return operations,dists[-1][-1]
    else:
        return operations

def local_levenshtein_distance(seq1, seq2, delins_cost=1, subst_cost_fun=None):
    """
    Compute a local alignment variant of the Levenshtein distance between two 
    sequences. Options are the same as L{levenshtein_distance_with_pointers}.
    
    Finds the optimal alignment of seq2 within seq1.
    
    In addition to the operations I, D and S used in 
    L{levenshtein_distance_with_pointers}, we use here '.' to indicate a 
    deletion at zero-cost at the beginning or end.
    
    """
    if subst_cost_fun is None:
        subst_cost_fun = lambda x,y: 0 if x==y else delins_cost
        
    # Simple cases: empty sequences
    if len(seq1) == 0:
        return len(seq2) * delins_cost
    elif len(seq2) == 0:
        return len(seq1) * delins_cost
    
    # Create a table with m+1 rows and n+1 columns
    dist = []
    pointers = []
    for i in range(len(seq1)+1):
        dist.append([None] * (len(seq2)+1))
        pointers.append([None] * (len(seq2)+1))
    
    for i in range(len(seq1)+1):
        # Initial deletions cost us nothing because the alignment's local
        dist[i][0] = 0
        pointers[i][0] = '.'
    for j in range(len(seq2)+1):
        dist[0][j] = j*delins_cost      # insertion
        pointers[0][j] = 'I'
    
    for j in range(1, len(seq2)+1):
        for i in range(1, len(seq1)+1):
            dist[i][j],pointers[i][j] = min(
                (dist[i-1][j] + delins_cost, 'D'),  # deletion
                (dist[i][j-1] + delins_cost, 'I'),  # insertion
                (dist[i-1][j-1] + subst_cost_fun(seq1[i-1], seq2[j-1]), 'S'),    # substitution
                    key=lambda x:x[0])
    
    # Allow free deletions at the end of seq2
    for i in range(1, len(seq1)+1):
        # Let us move along seq1 at 0-cost when seq1 is over if it helps
        dist[i][-1],pointers[i][-1] = min(
            (dist[i][-1], pointers[i][-1]), # Keep the same
            (dist[i-1][-1], '.'),           # Use free move
                key=lambda x:x[0])
    
    return dist, pointers
