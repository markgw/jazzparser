#!/bin/bash
cd `dirname $0`
# Start up the jazz parser with default options
./scripttest "Parse a very simple sequence using default tagger and parser" ../../jazzparser "C G7 C"
