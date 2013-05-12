#!/bin/bash
path=$1
shift
for file in $(find $path -name "*.py");
do
	python `dirname $0`/replace_license.py $file $*;
done
