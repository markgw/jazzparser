#!/bin/bash
cd `dirname $0`/..
./scripttest "Analyse a short sequence using the ngram backoff model" ../../jazzparser --file ../etc/test/text_chords_short \
    --file-options roman=T \
    -t fail \
    --backoff ngram \
    --backoff-options model=bigram0

