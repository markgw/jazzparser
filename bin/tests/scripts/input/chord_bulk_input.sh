#!/bin/bash
cd `dirname $0`/..
./scripttest "Load many input sequences from textual chord input in a file. Doesn't parse, just checks the input's read in." ../../jazzparser --ft bulk-chords --file ../etc/test/text_chord_list --file-options roman=T -t fail --no-progress 
