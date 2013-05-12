#!/usr/bin/python
# Simple script to count the average number of chords produced by the 
# chord labeller
# First run jazzparser with config:
#  input/config/chordlabel/label/heads.conf
# then this script

with open("../../etc/tmp/chordlabels", 'r') as labelfile:
    chordcounts = [ len(line.split(" ")) for line in labelfile ]

print "Ave chords per timestep: %f" % (float(sum(chordcounts)) / len(chordcounts))
