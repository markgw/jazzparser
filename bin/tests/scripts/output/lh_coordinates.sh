#!/bin/bash
cd `dirname $0`/..
./scripttest "Parse a short sequence with the ngram tagger and CKY parser and convert it to tonal space coordinates" ../../jazzparser \
    --file ../etc/test/text_chords_short \
    --file-options roman=T \
    -t ngram-multi \
    --topt model=bigram -p cky --lh-coordinates
