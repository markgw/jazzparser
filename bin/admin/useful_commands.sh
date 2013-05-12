#!/bin/bash
# This is not a script for running.
# Don't let it be run!
exit 0

##### The following are useful commands that I might want to remember

# Run the conversion script cat_conversion_2.0.rep on the entire database
./django-admin.py run annotator/bin/reannotate.py -r -f annotator/bin/input/cat_conversion_2.0.rep |tee conversion.out

# Restore the database from a backup
./django-admin.py dbshell <fullbackup.sql

