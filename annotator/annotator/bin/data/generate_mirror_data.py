"""generate_mirror_data.py -- output sequence data to a file.

Creates mirror instances of all the sequences in the database 
(see jazzparser.data.db_mirrors) and stores it all to a single output 
file.

"""
"""
============================== License ========================================
 Copyright (C) 2008, 2010 University of Edinburgh, Mark Wilding
 
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
__author__ = "Mark Wilding <mark.wilding@ed.ac.uk>" 

import sys
import logging
from optparse import OptionParser

from django.db.models import Q

from jazzparser.utils.loggers import init_logging
init_logging(logging.INFO)
# Get the logger from the logging system
logger = logging.getLogger("main_logger")

from apps.sequences.datautils import save_pickled_data

def main():
    usage = "%prog <out-file>"
    parser = OptionParser(usage=usage)
    parser.add_option("-r", "--reannotated", dest="reannotated", action="store_true", help="include sequences that are reannotations of others")
    parser.add_option("-p", "--partial", dest="partial", action="store_true", help="include sequences that are only partly annotated")
    parser.add_option("-n", "--no-names", dest="no_names", action="store_true", help="obscure names of the chord sequences")
    options, arguments = parser.parse_args()
    
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify an output file as the first argument"
        sys.exit(1)
    filename = arguments[0]
    
    print "Storing all sequences except those marked as unanalysed"
    q = Q(analysis_omitted=False)
    if not options.reannotated:
        q = q & Q(alternative=False)
        
    if not options.partial:
        f = lambda s: s.fully_annotated
    else:
        f = None
        
    save_pickled_data(filename, query=q, filter=f, no_names=options.no_names)
    
    sys.exit(0)
    
if __name__ == "__main__":
    main()

