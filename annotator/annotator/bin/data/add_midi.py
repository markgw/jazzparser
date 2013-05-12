"""Add midi files to the database.

Associates a midi file with a chord sequence in the database.

"""
"""
============================== License ========================================
 Copyright (C) 2008, 2010 University of Edinburgh, Mark Granroth-Wilding
 
 This file is part of The Jazz Parser.
 
 The Jazz Parser is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 The Jazz Parser is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 
 You should have received a copy of the GNU General Public License
 along with The Jazz Parser.  If not, see <http://www.gnu.org/licenses/>.
 
============================ End license ======================================

"""
__author__ = "Mark Granroth-Wilding <mark.granroth-wilding@ed.ac.uk>" 

import sys, os
import logging
from StringIO import StringIO
from optparse import OptionParser
from midi import read_midifile

from apps.sequences.models import MidiData, ChordSequence
from django.core.files.base import ContentFile
from jazzparser.utils.csv import UnicodeCsvReader

def main():
    usage = "%prog <seq-id> <midi-file> [<midi-file> ...]"
    parser = OptionParser(usage=usage)
    parser.add_option("--names", dest="names", action="store", help="read in a NAMES file from the midi auto-collection, intead of reading midi files from the command line")
    options, arguments = parser.parse_args()
    
    if options.names is not None:
        print "Reading names from %s" % options.names
        csv = UnicodeCsvReader(open(options.names))
        filenames = []
        dirname = os.path.dirname(options.names)
        
        csv.next()
        for row in csv:
            filename = os.path.join(dirname,row[0])
            if not os.path.exists(filename):
                continue
            seq = ChordSequence.objects.get(id=int(row[2]))
            filenames.append((seq,filename))
    else:
        if len(arguments) < 2:
            print >>sys.stderr, "Specify a sequence id and one or more midi files"
            sys.exit(1)
        
        seq_id = int(arguments[0])
        seq = ChordSequence.objects.get(id=seq_id)
        filenames = [(seq,fn) for fn in arguments[1:]]
        
    if len(filename) == 0:
        print sys.stderr, "No input files"
        sys.exit()
    
    files = []
    for seq,filename in filenames:
        print "Reading %s" % filename
        f = open(filename, 'r')
        data = f.read()
        # Try reading in the midi data to check it's ok
        read_midifile(StringIO(data))
        files.append((seq, os.path.basename(filename), ContentFile(data)))
    
    for seq, filename,f in files:
        print "Storing %s" % filename
        # Create a new midi data record in the database
        midi = MidiData()
        midi.sequence = seq
        midi.save()
        # Use the original filename
        midi.midi_file.save(filename, f)
        midi.save()
    
if __name__ == "__main__":
    main()

