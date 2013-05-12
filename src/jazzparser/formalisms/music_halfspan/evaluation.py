"""Tonal space path evaluation functions.

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

from jazzparser.utils.base import group_pairs

def _subst_type(point1, point2):
    root = point1[0] != point2[0]
    function = point1[1] != point2[1]
    if root and function:
        return "both"
    elif root:
        return "root"
    elif function:
        return "fun"
    else:
        return "match"

def _subst_cost(point1, point2):
    return {
        "both" : 2,
        "root" : 1,
        "fun"  : 1,
        "match": 0
    }[_subst_type(point1, point2)]
    
def _subst_cost_float(point1, point2):
    """
    Substitution cost, same as _subst_cost, but returns a value between 0 
    and 1.
    
    """
    return float(_subst_cost(point1,point2))/2

def _steps_list(seq):
    """
    Given a list of (coordinate,function) pairs, produces a similar list 
    that represents the steps between each point in the path and its previous 
    point, maintaining the original functions.
    
    The first point yields the step 
    from the origin, ignoring its enharmonic block (in other words, the 
    step from (0,0) within its enharmonic block).
    
    This means that effectively we don't care what enharmonic block the 
    path lies in, only the relative points along the path.
    
    """
    def _minus(c0, c1):
        return (c0[0]-c1[0], c0[1]-c1[1])
    
    # Get the functions out for later
    coords,funs = zip(*seq)
    steps = [coords[0]] + [(_minus(c1,c0)) for c0,c1 in group_pairs(coords)]
    # Put the functions back in for the result
    return zip(steps, funs)

def _lf_to_coord_funs(sem):
    """
    Gets a list of (coordinate,function) pairs from a logical form.
    
    """
    from jazzparser.formalisms.music_halfspan.semantics import \
                            list_lf_to_coordinates, list_lf_to_functions
    # Convert the LF to a list of coordinates
    coords,__ = zip(*list_lf_to_coordinates(sem))
    # And to a list of functions
    funs,__ = zip(*list_lf_to_functions(sem))
    # Put them together into (coord,fun) pairs
    return zip(coords,funs)

def tonal_space_distance(sem1, sem2):
    """
    Computes the edit distance between the tonal space paths of two logical 
    forms, using a suitable scoring. This uses a cost of 2 for deletions and 
    insertions and scores 1 for a substitution that gets either 
    the step or function right, but not both. The result is then 
    divided by 2 (meaning that effectively all costs are 1 and a 0.5 
    cost is given to half-right substitutions).
    
    The alignment is not between the tonal space points themselves, but 
    between the vectors between each pair of points (that is the points 
    relative to the previous point). This means that a path won't be 
    penalised if part of it is translated by a constant vector, except at 
    the point where it goes wrong.
    
    """
    from jazzparser.utils.distance import levenshtein_distance
    # Get a list of (coord,fun) pairs for the logical forms
    seq1 = _lf_to_coord_funs(sem1)
    seq2 = _lf_to_coord_funs(sem2)
    # Produce a version of the paths made up of steps and functions, 
    #  rather than points and functions
    steps1 = _steps_list(seq1)
    steps2 = _steps_list(seq2)
    
    edit_dist = levenshtein_distance(
                                steps1, 
                                steps2,
                                delins_cost=2,
                                subst_cost_fun=_subst_cost)
    return float(edit_dist) / 2.0

def tonal_space_alignment_costs(sem1, sem2):
    """
    Performs the same algorithm as tonal_space_distance, but instead 
    of returning the score returns the counts of deletions, 
    insertions, root (only) substitutions, function (only) 
    substitutions, full substitutions and alignments.
    
    """
    from jazzparser.utils.distance import levenshtein_distance_with_pointers
    # Get a list of (coord,fun) pairs for the logical forms
    seq1 = _lf_to_coord_funs(sem1)
    seq2 = _lf_to_coord_funs(sem2)
    # Produce a version of the paths made up of steps and functions, 
    #  rather than points and functions
    steps1 = _steps_list(seq1)
    steps2 = _steps_list(seq2)
    
    dists,pointers = levenshtein_distance_with_pointers(
                                steps1, 
                                steps2,
                                delins_cost=2,
                                subst_cost_fun=_subst_cost)
    # We now have the matrix of costs and the pointers that generated 
    #  those costs.
    # Trace back to find out what costs were incurred in the optimal 
    #  alignment
    insertions = 0
    deletions = 0
    function_subs = 0
    root_subs = 0
    full_subs = 0
    alignments = 0
    # Start at the top right corner
    i,j = (len(dists)-1), (len(dists[0])-1)
    while not i == j == 0:
        if pointers[i][j] == "I":
            insertions += 1
            j -= 1
        elif pointers[i][j] == "D":
            deletions += 1
            i -= 1
        else:
            # Substitution: find out what kind
            step1 = steps1[i-1]
            step2 = steps2[j-1]
            subst_type = _subst_type(step1, step2)
            if subst_type == "both":
                full_subs += 1
            elif subst_type == "fun":
                function_subs += 1
            elif subst_type == "root":
                root_subs += 1
            else:
                alignments += 1
            j -= 1
            i -= 1
    
    return {
        'deletions' : deletions, 
        'insertions' : insertions, 
        'root_subs' : root_subs, 
        'function_subs' : function_subs, 
        'full_subs' : full_subs, 
        'substitutions' : root_subs+function_subs+full_subs,
        'alignments' : alignments,
        'steps1' : steps1,
        'steps2' : steps2,
    }
    
def tonal_space_alignment(sem1, sem2, distance=False):
    """
    Performs the same algorithm as L{tonal_space_distance} and 
    L{tonal_space_alignment_costs}, but returns a list of the operations 
    that produce the optimal alignment: "I" - insertion; "D" - deletion; 
    "A" - alignment; "S" - full substitution; or anything else beginning with 
    "S" to indicate a partial substitution.
    
    Returns the operation list and the two sequences that were compared.
    If distance=True, also includes the distance metric. Not included by 
    default for backward compatibility.
    
    """
    from jazzparser.utils.distance import levenshtein_distance_with_pointers
    # Get a list of (coord,fun) pairs for the logical forms
    seq1 = _lf_to_coord_funs(sem1)
    seq2 = _lf_to_coord_funs(sem2)
    # Produce a version of the paths made up of steps and functions, 
    #  rather than points and functions
    steps1 = _steps_list(seq1)
    steps2 = _steps_list(seq2)
    
    dists,pointers = levenshtein_distance_with_pointers(
                                steps1, 
                                steps2,
                                delins_cost=2,
                                subst_cost_fun=_subst_cost)
    
    # We now have the matrix of costs and the pointers that generated 
    #  those costs.
    # Trace back to find out what produces the optimal alignment
    # Start at the top right corner
    i,j = (len(dists)-1), (len(dists[0])-1)
    oplist = []
    while not i == j == 0:
        if pointers[i][j] == "I":
            oplist.append("I")
            j -= 1
        elif pointers[i][j] == "D":
            oplist.append("D")
            i -= 1
        else:
            # Substitution: find out what kind
            step1 = steps1[i-1]
            step2 = steps2[j-1]
            subst_type = _subst_type(step1, step2)
            if subst_type == "both":
                oplist.append("S")
            elif subst_type == "fun":
                oplist.append("Sf")
            elif subst_type == "root":
                oplist.append("Sr")
            else:
                oplist.append("A")
            j -= 1
            i -= 1
    oplist = list(reversed(oplist))
    
    if distance:
        dist = float(dists[-1][-1]) / 2.0
        return oplist,steps1,steps2,dist
    else:
        return oplist,steps1,steps2

def tonal_space_align(sem1, sem2):
    """
    Like the other alignment functions, but returns the list of aligned 
    pairs.
    
    """
    from jazzparser.utils.distance import align
    # Get a list of (coord,fun) pairs for the logical forms
    seq1 = _lf_to_coord_funs(sem1)
    seq2 = _lf_to_coord_funs(sem2)
    # Produce a version of the paths made up of steps and functions, 
    #  rather than points and functions
    steps1 = _steps_list(seq1)
    steps2 = _steps_list(seq2)
    
    pairs = align(steps1, steps2, delins_cost=2, subst_cost=_subst_cost)
    return pairs
    
def tonal_space_precision_recall(sem, gold_sem):
    """
    Calculates the precision and recall and f-score of the optimal alignment 
    between the sequence and the gold standard sequence.
    
    """
    costs = tonal_space_alignment_costs(sem, gold_sem)
    num_steps = len(costs['steps1'])
    num_gold_steps = len(costs['steps2'])
    
    # Work out the positive score for the alignment
    align_score = float(costs["alignments"]) + \
                  float(costs["root_subs"]+costs["function_subs"]) / 2.0
    
    # Compute precision and recall to get f-score
    precision = align_score / num_steps
    recall = align_score / num_gold_steps
    f_score = 2*precision*recall / (precision+recall)
    return precision,recall,f_score
    
def tonal_space_f_score(sem, gold_sem):
    """
    Calculates an f-score for the optimal alignment between the sequence and 
    the gold standard sequence.
    
    """
    return tonal_space_precision_recall(sem, gold_sem)[2]

def tonal_space_alignment_score(seq1, seq2):
    """
    Assigns a score to the optimal alignment between the two logical forms.
    
    Think of this as essentially a count of alignments in the optimal 
    alignment. In fact, a pair of points may be partly aligned, in which 
    case they contribute something to this score between 0 and 1.
    
    """
    costs = tonal_space_alignment_costs(seq1, seq2)
    return float(costs["alignments"]) + float(costs["root_subs"]+costs["function_subs"])/2

def tonal_space_length(sem):
    """
    Length of the tonal space path represented by the given logical form.
    
    This could be more efficient, but at the moment only gets used in places 
    where it doesn't matter much, so I might as well keep it simple.
    
    """
    from jazzparser.formalisms.music_halfspan.semantics import Semantics
    if isinstance(sem, Semantics):
        sem = sem.lf
    # Use our standard function to get a tonal space path for the sems
    seq = _lf_to_coord_funs(sem)
    return len(seq)


def tonal_space_local_distance(sem1, sem2):
    """
    Like L{tonal_space_distance}, but uses local alignment of seq2 within 
    seq1.
    
    """
    from jazzparser.utils.distance import local_levenshtein_distance
    # Get a list of (coord,fun) pairs for the logical forms
    seq1 = _lf_to_coord_funs(sem1)
    seq2 = _lf_to_coord_funs(sem2)
    # Produce a version of the paths made up of steps and functions, 
    #  rather than points and functions
    steps1 = _steps_list(seq1)
    steps2 = _steps_list(seq2)
    
    dists,pointers = local_levenshtein_distance(
                                steps1, 
                                steps2,
                                delins_cost=2,
                                subst_cost_fun=_subst_cost)
    return float(dists[-1][-1]) / 2.0

def tonal_space_local_alignment(sem1, sem2):
    """
    Like L{tonal_space_alignment}, but uses local alignment of seq2 within seq1.
    
    Also returns the distance metric (like L{tonal_space_local_distance}.
    
    """
    from jazzparser.utils.distance import local_levenshtein_distance
    # Get a list of (coord,fun) pairs for the logical forms
    seq1 = _lf_to_coord_funs(sem1)
    seq2 = _lf_to_coord_funs(sem2)
    # Produce a version of the paths made up of steps and functions, 
    #  rather than points and functions
    steps1 = _steps_list(seq1)
    steps2 = _steps_list(seq2)
    
    dists,pointers = local_levenshtein_distance(
                                steps1, 
                                steps2,
                                delins_cost=2,
                                subst_cost_fun=_subst_cost)
    
    # We now have the matrix of costs and the pointers that generated 
    #  those costs.
    # Trace back to find out what produces the optimal alignment
    # Start at the top right corner
    i,j = (len(dists)-1), (len(dists[0])-1)
    oplist = []
    while not i == j == 0:
        if pointers[i][j] == "I":
            oplist.append("I")
            j -= 1
        elif pointers[i][j] == "D":
            oplist.append("D")
            i -= 1
        elif pointers[i][j] == ".":
            oplist.append(".")
            i -= 1
        else:
            # Substitution: find out what kind
            step1 = steps1[i-1]
            step2 = steps2[j-1]
            subst_type = _subst_type(step1, step2)
            if subst_type == "both":
                oplist.append("S")
            elif subst_type == "fun":
                oplist.append("Sf")
            elif subst_type == "root":
                oplist.append("Sr")
            else:
                oplist.append("A")
            j -= 1
            i -= 1
    
    oplist = list(reversed(oplist))
    distance = float(dists[-1][-1]) / 2.0
    return oplist, steps1, steps2, distance

def arrange_alignment(steps1, steps2, ops):
    """
    Arrange the steps of an alignment for printing in aligned rows.
    
    """
    steps1 = iter(steps1)
    steps2 = iter(steps2)
    alignments = []
    
    for op in ops:
        if op == "I":
            left = ""
            right = str(steps2.next())
        elif op in ["D", "."]:
            left = steps1.next()
            right = ""
        elif op == "A" or op.startswith("S"):
            left = steps1.next()
            right = steps2.next()
        cells = [str(left),str(right),str(op)]
        width = max(len(txt) for txt in cells)
        cells = [cell.ljust(width) for cell in cells]
        alignments.append(cells)
    
    return alignments
