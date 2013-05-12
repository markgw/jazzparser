#!/bin/bash
# Edit the description of a model
# Read out the old description
./description.py $1 >description.tmp
# Edit it using nano
nano description.tmp
# Store this as the new description
cat description.tmp |./description.py $1 -s
rm description.tmp
