"""Output a file with multiple annotation data for evaluating annotator consistency

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

import sys
import logging
from optparse import OptionParser

from django.db.models import Count

from apps.sequences.models import Song
from jazzparser.data.db_mirrors.consistency import ConsistencyData

def main():
    usage = "%prog <out-file>"
    parser = OptionParser(usage=usage)
    parser.add_option("-n", "--no-names", dest="no_names", action="store_true", help="obscure names of the chord sequences")
    options, arguments = parser.parse_args()
    
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify an output file as the first argument"
        sys.exit(1)
    filename = arguments[0]
    
    # Get songs that have multiple annotations
    songs = Song.objects.annotate(seqs=Count('chordsequence')).filter(seqs__gte=2)
    
    # Create db mirrors of all the sequences
    sequences = []
    pairs = []
    for song in songs:
        if song.chordsequence_set.count() > 2:
            print >>sys.stderr, "%s has more than 2 alternative annotations" % \
                song.string_name
        seqs = song.chordsequence_set.all()
        # Add a record of the pairing
        pairs.append((seqs[0].id, seqs[1].id))
        # Add the mirrored version of the sequence
        for seq in seqs:
            sequences.append(seq.mirror)
            
        if options.no_names:
            for seq in sequences:
                # Obscure the sequence's name
                seq.name = "sequence-%d" % seq.id
    
    consdata = ConsistencyData(sequences, pairs)
    consdata.save(filename)
    
    print "Output %d sequences with multiple annotations" % songs.count()
    
if __name__ == "__main__":
    main()

