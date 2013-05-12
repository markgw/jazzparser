"""Largest Common Embeddable Subtree.

Implementation of the algorithm from I{On the Maximum Common Embedded Subtree 
Problem for Ordered Trees} by Loxano and Valiente. This is for unlabeled, 
ordered trees.

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

from .datastructs import Node, MutableTree
from .balancedseq import BalancedSequence

def lces_size(tree1, tree2):
	"""
	Computes the size of the largest common embedded subtree for two 
	unlabeled trees. It is quicker to compute the size than to compute 
	the common tree itself, so this function doesn't actually compute what 
	the tree is.
	
	"""
	# Get a balanced sequence to represent each tree
	bs1 = BalancedSequence.from_tree(tree1)
	bs2 = BalancedSequence.from_tree(tree2)
	
	# To make sure we never recompute an lcs value for a pair of subsequences 
	#  twice, we store those we've computed in a dictionary
	lcs_cache = {}
	
	def _lcs(seq1, seq2):
		# Base cases: common subtree of empty tree and anything is size 0
		if len(seq1) == 0:
			return 0
		if len(seq2) == 0:
			return 0
			
		# Check whether we've computed this before
		if (seq1,seq2) in lcs_cache:
			return lcs_cache[(seq1,seq2)]
		# Also the other way round: the result would be the same
		if (seq2,seq1) in lcs_cache:
			return lcs_cache[(seq2,seq1)]
		
		# Break the seqs into heads and tails
		head1,tail1 = seq1.head_tail()
		head2,tail2 = seq2.head_tail()
		
		# Try the three possible matchings and take the max size
		# First try matching the heads to each other
		head_match = _lcs(head1, head2) + _lcs(tail1, tail2) + 1
		# Next try skipping a level of embedding on the head of tree1
		# Note that head1+tail1 != tree1
		head_skip1 = _lcs(head1+tail1, seq2)
		# Finally, try skipping a level on tree2 as well
		head_skip2 = _lcs(seq1, head2+tail2)
		
		max_size = max([head_match, head_skip1, head_skip2])
		
		# Remember this in case we get asked the same thing again
		lcs_cache[(seq1,seq2)] = max_size
		return max_size
	
	# Run recursive lcs computation on the two sequences
	size = _lcs(bs1, bs2)
	return size


def lces(tree1, tree2):
	"""
	Computes the largest common embedded subtree for two 
	unlabeled trees. Even you only need to know the size, use L{lces_size}, 
	since it's a slightly simpler problem.
	
	"""
	cat = BalancedSequence.cat
	
	# Get a balanced sequence to represent each tree
	bs1 = BalancedSequence.from_tree(tree1)
	bs2 = BalancedSequence.from_tree(tree2)
	
	# To make sure we never recompute an lcs value for a pair of subsequences 
	#  twice, we store those we've computed in a dictionary
	lcs_cache = {}
	
	def _lcs(seq1, seq2):
		# Base cases: common subtree of empty tree and anything is the empty tree
		if len(seq1) == 0:
			return BalancedSequence([]), 0
		if len(seq2) == 0:
			return BalancedSequence([]), 0
			
		# Check whether we've computed this before
		if (seq1,seq2) in lcs_cache:
			return lcs_cache[(seq1,seq2)]
		# Also the other way round: the result would be the same
		if (seq2,seq1) in lcs_cache:
			return lcs_cache[(seq2,seq1)]
		
		# Break the seqs into heads and tails
		head1,tail1 = seq1.head_tail()
		head2,tail2 = seq2.head_tail()
		
		# Try the three possible matchings and take the max size
		# First try matching the heads to each other
		head_match_h, head_match_h_size = _lcs(head1, head2)
		head_match_t, head_match_t_size = _lcs(tail1, tail2)
		# Next try skipping a level of embedding on the head of tree1
		# Note that head1+tail1 != tree1
		head_skip1, head_skip1_size = _lcs(head1+tail1, seq2)
		# Finally, try skipping a level on tree2 as well
		head_skip2, head_skip2_size = _lcs(seq1, head2+tail2)
		
		# Choose whichever of these options gives us the biggest sequence
		sizes = [
			('h', head_match_h_size + head_match_t_size + 1),
			('s1', head_skip1_size),
			('s2', head_skip2_size),
		]
		(max_op,max_size) = max(sizes, key=lambda x:x[1])
		
		if max_op == 'h':
			# Matched the heads
			# Put together the tree that does this
			seq = cat(head_match_h, head_match_t)
		elif max_op == 's1':
			# Skipped the head of the first sequence
			seq = head_skip1
		else:
			seq = head_skip2
		
		# Remember this in case we get asked the same thing again
		lcs_cache[(seq1,seq2)] = (seq,max_size)
		return (seq,max_size)
	
	# Run recursive lcs computation on the two sequences
	max_seq, max_size = _lcs(bs1, bs2)
	return max_seq.to_tree()
