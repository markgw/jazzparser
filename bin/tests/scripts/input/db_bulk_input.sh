#!/bin/bash
cd `dirname $0`/..
./scripttest "Load many input sequences from database mirror format input in a file. Doesn't parse, just checks the input's read in." ../../jazzparser --ft bulk-db --file ../etc/test/dbsequences -t fail --no-progress
