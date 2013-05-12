"""Utilities relating to data handling and processing.

This module does not define datatypes itself. See L{jazzparser.data} 
for that.

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

def hold_out(full, start, end):
    if start is None or start == 0:
        return full[end:]
    elif end is None:
        return full[:start]
    else:
        return full[:start] + full[end:]

def holdout_partition(input, partitions):
    """
    Partitions the iterable input into the given number of partitions 
    and returns a list of subsets of the input with each of the 
    partitions excluded. Useful for doing heldout data evaluations.
    """
    partition_size = len(input) / partitions
    heldout_sets = []
    for partition in range(partitions-1):
        heldout_sets.append(hold_out(input, partition_size*partition, partition_size*(partition+1)))
    # Last partition: throw in everything that's left
    heldout_sets.append(hold_out(input, partition_size*(partitions-1), None))
    return heldout_sets

def partition(input, partitions):
    """
    The complement of holdout_partition. Simply splits the input 
    n ways.
    """
    partition_size = len(input) / partitions
    parts = []
    for partition in range(partitions-1):
        parts.append(input[partition_size*partition: partition_size*(partition+1)])
    # Last partition: throw what's left in
    parts.append(input[partition_size*(partitions-1):])
    return parts
