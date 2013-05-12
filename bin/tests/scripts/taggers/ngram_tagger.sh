#!/bin/bash
cd `dirname $0`/..
./scripttest "Tag a short sequence using the ngram tagger and use a dummy parser to check the tagger's working" ../../jazzparser \
    --file ../etc/test/text_chords_short \
    --file-options roman=T \
    -t ngram-multi --topt model=bigram -p fail
