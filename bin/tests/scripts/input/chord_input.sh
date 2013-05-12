#!/bin/bash
cd `dirname $0`/..
./scripttest "Load input from textual chord input in a file. Doesn't parse, just checks the input's read in." ../../jazzparser --ft chords --file ../etc/test/text_chords -t fail --file-options roman=T
./scripttest "Load input from textual pitch (not numeral) chord input in a file, to check the input's read in." ../../jazzparser --ft chords --file ../etc/test/text_pitch_chords -t fail
