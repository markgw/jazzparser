#!/bin/bash
cd `dirname $0`/..
./scripttest "Load many input sequences from MIDI files. Doesn't parse, just checks the input's read in." ../../jazzparser --ft bulk-segmidi --file ../etc/test/segmidi.csv -t fail --no-progress
