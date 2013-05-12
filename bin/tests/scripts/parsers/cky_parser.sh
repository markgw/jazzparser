#!/bin/bash
cd `dirname $0`/..
./scripttest "Use the ngram tagger on a short sequence and parse using the CKY parser" ../../jazzparser --file ../etc/test/text_chords_short --file-options roman=T -t ngram-multi --topt model=bigram -p cky
