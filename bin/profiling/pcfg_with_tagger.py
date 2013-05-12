#!/bin/bash

cd `dirname $0`/..
./parserprofile --parser pcfg --popt model=test0 --tagger ngram --topt model=bigram-c2-uni0 -f ../input/fullseqs:1 --progress
