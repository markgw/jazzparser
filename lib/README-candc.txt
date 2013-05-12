To use the candc parser, put all the code (with models, etc) in a directory 
called "candc", here in the lib directory. This directory will be svn:ignored.
Compile the code in this directory.
Models are checked in in the "candc_data" directory here.

Using precompiled binaries
==========================
It's worth trying the precompiled binaries first. Put them in lib/candc/bin.
You don't need anything else in the candc directory then.

Building
========
Unpack the source code and move the top-level directory to lib/candc.
Build using make. See notes on 
  http://svn.ask.it.usyd.edu.au/trac/candc/wiki/Installation
regarding errors you might get and the fix.
The binaries will then be in lib/candc/bin.
