#!/bin/bash
cd `dirname $0`/..
./scripttest "Load input from a MIDI file. Doesn't parse, just checks the input's read in." ../../jazzparser --ft segmidi --file ../etc/test/afine.mid -t fail
