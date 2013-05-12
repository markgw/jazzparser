#!../../../jazzshell
"""
Some tests for the generic ngram model to see whether it's working correctly.

I've added this to hunt for bugs in the ngram implementation. It tries 
training hidden ngram models on toy data and running them on toy test data. 
The results should show up problems with backoff/smoothing (if they're 
big enough problems!).

"""
import random, itertools, sys
import numpy as np
from sys import stdout
from jazzparser.utils.nltk.ngram import PrecomputedNgramModel
from jazzparser.utils.nltk.probability import witten_bell_estimator
from jazzparser.utils.base import ExecutionTimer

TRAIN_FILE = "train.txt"
TEST_FILE = "test.txt"

SHOW_DECODED_WORDS = False

CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.\"', "
# A distribution over characters with ascii codes surrounding the input 
# by which the input string will be noisified
NOISE_DIST = [
    (-4, 2),
    (-3, 10),
    (-2, 3),
    (-1, 2),
    (0,  20),
    (1,  5),
    (2,  4),
    (3,  3),
    (4,  1),
]
SHIFT_PROFILE = sum(([shift] * repeat for (shift,repeat) in NOISE_DIST), [])

# Use the distribution to mess up some input data char by char
def noisify_gen(string):
    for char in string:
        try:
            chcode = CHARS.index(char)
        except ValueError:
            print "Unknown character: %s" % char
            raise
        shift = random.choice(SHIFT_PROFILE)
        # Shift the character by the randomly selected offset
        yield CHARS[(chcode+shift) % len(CHARS)]

def noisify(string):
    return "".join(list(noisify_gen(string)))


########################################
# Read in the input data for training and testing
with open(TRAIN_FILE, "r") as train_file:
    train_text = train_file.read()
with open(TEST_FILE, "r") as test_file:
    test_text = test_file.read()

# Generate some training data by applying noise to the input data
training_data = []
for line in train_text.split("\n"):
    if len(line):
        training_data.append(zip(list(noisify(line)), list(line)))

# Generate some test data similarly for a different input
test_data = [list(noisify(line)) for line in test_text.split("\n") if len(line)]
test_data_gold = [list(line) for line in test_text.split("\n") if len(line)]

# Function for printing some of a conditional distribution
def show_dist(dist, limit=10):
    for cond in dist.conditions()[:limit]:
        print "%s ->" % str(cond)
        for samp in dist[cond].samples():
            print samp, dist[cond].prob(samp)
        print

############################################
# Train several ngrams on this training data and test them

# Function to score the results of decoding
def correct_letters(output, gold):
    return sum(itertools.imap(str.__eq__, output, gold))
def test_accuracy(output, gold):
    return float(correct_letters(output,gold)) / len(output) * 100.0

# Define the model parameters that we'll try
PARAMS = [
    # Unigram, no backoff, no cutoff
    (1, None, 0),
    # Should be the same as previous
    #(1, None, None),
    # Same, but with cutoff
    (1, None, 2),
    # Bigram, no backoff, no cutoff
    (2, None, 0),
    # Bigram->unigram, no cutoff
    (2, 1,    0),
    # Same, but with cutoff
    # Might plausibly detriment the results
    (2, 1,    2),
    # Trigram, no backoff, no cutoff
    (3, None, 0),
    # Trigram->bigram, no cutoff
    (3, 1,    0),
    # Trigram->bigram->unigram, no cutoff
    (3, 2,    0),
    # Trigram with cutoff
    # This probably ought to improve things (over those below)
    (3, 2,    2),
]

for order,backoff,cutoff in PARAMS:
    print "*******************************"
    print "Order:", order
    print "Backoff:", backoff
    print "Smoothing: witten-bell"
    print "Cutoff:", cutoff
    model = PrecomputedNgramModel.train(order, 
                             training_data, 
                             label_dom=list(CHARS), 
                             emission_dom=list(CHARS),
                             backoff_order=backoff,
                             estimator=witten_bell_estimator,
                             cutoff=cutoff,
                             backoff_kwargs={'cutoff':0})
    
    #~ # Take a look at some of the distributions
    #~ print "Some emission distributions"
    #~ print "%d labels, showing 10\n" % len(model.emission_dist.conditions())
    #~ show_dist(model.emission_dist)
    #~ 
    #~ print "\nSome transition distibrutions"
    #~ print "%d conditions, showing 5\n" % len(model.label_dist.conditions())
    #~ show_dist(model.label_dist, limit=5)
    
    # Try decoding the test data
    correct = 0
    total = 0
    joint_probs = 0.0
    for test_line,gold_line in zip(test_data, test_data_gold):
        # Compute the probability assigned to the data and labels by the model
        joint_logprob = model.labeled_sequence_log_probability(test_line, gold_line)
        joint_probs += joint_logprob
        
        # Decode the noisy string using the model
        result = model.decode_gamma(test_line)
        if SHOW_DECODED_WORDS:
            print
            print "Pre-noise: %s" % "".join(gold_line)
            print "Noise:     %s" % "".join(test_line)
            print "Result:    %s" % "".join(result)
            print "Accuracy: %s" % test_accuracy(result, gold_line)
        else:
            stdout.write(".")
        # Note how many letters it got right
        correct += correct_letters(result, gold_line)
        total += len(result)
        
    print "\nOverall accuracy:"
    print "   %s%%" % (float(correct) / total)
    print "Test sequence entropy:"
    print "   %s" % (-joint_probs / total)
