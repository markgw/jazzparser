#!/bin/bash
path=$1
shift
for file in $(find $path -name "*.py");
do
	python `dirname $0`/replace_author.py $* $file old_authors.txt Mark Granroth-Wilding \<mark.granroth-wilding\@ed.ac.uk\>
done
