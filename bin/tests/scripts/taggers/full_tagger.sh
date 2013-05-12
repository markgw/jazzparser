#!/bin/bash
cd `dirname $0`/..
./scripttest "Tag a short sequence using the full tagger and use a dummy parser to check the tagger's working" ../../jazzparser --file ../etc/test/text_chords_short --file-options roman=T -t full -p fail
