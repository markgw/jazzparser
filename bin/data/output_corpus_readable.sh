#!/bin/bash
# Output the full annotated corpus in a human-readable format
echo "# Granroth-Wilding/Steedman annotated jazz chord progression corpus
# 
# Each chord sequence specifies a key, and bar length in beats.
# Chords are shown transposed to the key of C. The line below the 
# chords gives the duration of each chord, vertically aligned with the 
# chord. The next line gives the name of a lexical category schema. 
# The next line showns brackets indicating the start and end of 
# non-initial coordination consituents. (The brackets should be placed 
# in front of the chord on which they are annotated.)
#
" >chord_corpus.txt
./printseqs.py -a ../../input/fullseqs >>chord_corpus.txt
