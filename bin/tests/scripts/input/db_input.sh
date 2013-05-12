#!/bin/bash
cd `dirname $0`/..
./scripttest "Load input from database mirror format input in a file. Doesn't parse, just checks the input's read in." ../../jazzparser --ft db --file ../etc/test/dbsequences --fopt index=0 -t fail
