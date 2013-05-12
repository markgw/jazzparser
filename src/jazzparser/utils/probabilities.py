"""Utilities for processing probability distributions.

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

def batch_sizes(probabilities, batch_ratio, max_batch=0):
    """
    Given a list of probabilities, returns a list of integers that 
    represents the ordered sizes of batches (from high to low 
    probability) required so that the ratio between the highest and 
    lowest probabilities in the batch is at most batch_ratio.
    
    If C{max_batch} is non-zero, a maximum of C{max_batch} items are included 
    in each batch.
    
    """
    # Make sure we go through the probabilities in order, high to low
    probs = reversed(sorted(probabilities))
    sizes = []
    batch_top = None
    batch_length = 1
    for prob in probs:
        if batch_top is None:
            batch_top = prob
        else:
            # Check the probability ratio and whether we've filled the max size
            if prob >= batch_ratio * batch_top and \
                    (not max_batch or batch_length < max_batch):
                # This is a high enough probability to go in this batch
                batch_length += 1
            else:
                # Start a new batch
                sizes.append(batch_length)
                # This is now the top one in the batch
                batch_length = 1
                batch_top = prob
    sizes.append(batch_length)
    return sizes
    
def beamed_batch_sizes(probabilities, batch_ratio, max_batch=0):
    """
    An alternative to L{batch_sizes} which processes many lists of 
    probabilities at once (i.e. one per word).
    
    The lists returned contain the number 
    of values that should be returned in each batch to represent a 
    progressively widening probability beam, which is the same across 
    all the words. The main difference between this and applying 
    L{batch_sizes} to each word independently is that this may result 
    in some words having some batches empty, if the beam is not wide 
    enough to catch the next highest probability.
    
    The one exception to this is the first batch, which will always 
    contain at least one value, even if this means effectively lowering 
    the beam for that one word.
    
    Every batch will include at least one value on at least one word.
    
    It is assumed that every word has at least one value.
    
    If C{max_batch} is non-zero, a maximum of C{max_batch} items are included 
    in each batch for each word.
    
    @type probabilities: list of lists of floats
    @param probabilities: a list for each word of the probabilities 
        to batch up.
    @type batch_ratio: float
    @param batch_ratio: maximum ratio between the highest probability in a 
        particular batch and the lowest (over all words).
    @rtype: list of lists of ints
    @return: the list of sizes of each batch for each word.
    
    """
    words = len(probabilities)
    # Copy the input to use as a queue
    queues = [list(reversed(sorted(probs))) for probs in probabilities]
    # Build up a list of batch sizes
    batch_lists = [[] for i in range(words)]
    
    first_batch = True
    
    # Keep making more batches until the queues are all empty
    while sum([len(q) for q in queues]) > 0:
        # Get the highest probability still waiting to be taken
        beam_top = max([q[0] for q in queues if len(q) > 0])
        beam_bottom = batch_ratio * beam_top
        # For each word, add all values that lie within the beam and 
        #  remove them from the queue
        for word in range(words):
            vals_in_batch = len([prob for prob in queues[word] if prob >= beam_bottom])
            # Don't take more than max_batch at once (if given)
            if max_batch:
                vals_in_batch = min(vals_in_batch, max_batch)
            queues[word] = queues[word][vals_in_batch:]
            batch_lists[word].append(vals_in_batch)
            
        # If this is the first batch, check every word got at least one
        if first_batch:
            first_batch = False
            for word in range(words):
                if batch_lists[word][0] == 0:
                    # Nothing was assigned to this word - give it many 
                    #  values as have the highest probability (probably 
                    #  just one)
                    vals_in_batch = len([prob for prob in queues[word] if prob == queues[word][0]])
                    queues[word] = queues[word][vals_in_batch:]
                    batch_lists[word][0] = vals_in_batch
    return batch_lists

def random_selection(obj_probs, normalize=False):
    """
    Given a distribution in the form of (object,prob) pairs, picks an 
    object randomly with probabilities according to the distribution.
    
    The probabilities should obviously sum to 1.0. If they don't, an 
    error might be raised, but it might go unnoticed. Make sure your 
    distributions are healthy.
    Alternatively, set normalize=True and the probabilities will be 
    scaled into a real probability distribution.
    
    The objects may be of any type.
    
    """
    import random
    if normalize:
        total_prob = sum(pair[1] for pair in obj_probs)
        # Rescale probs so they sum to 1.0
        obj_probs = [(obj,prob/total_prob) for (obj,prob) in obj_probs]
    # Pick a number between 0 and 1
    rand_num = random.random()
    # Step through the cumulative probability dist until we get to this number
    cum_prob = 0.0
    for obj,prob in obj_probs:
        cum_prob += prob
        if cum_prob >= rand_num:
            return obj
    raise ProbabilityError, "probability distribution should reach 1.0, but didn't get as far as %f" % rand_num

class ProbabilityError(Exception):
    pass
