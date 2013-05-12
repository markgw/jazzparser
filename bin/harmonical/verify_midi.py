#!/usr/bin/env ../jazzshell
"""
Check a midi file for problems.

"""
import sys, os
from optparse import OptionParser
from midi import read_midifile, write_midifile, check_midi

def main():
    usage = "%prog [options] <input>"
    description = "Loads a midi file and checks it for problems."
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify an input midi file"
        sys.exit(1)
        
    try:
        mid = read_midifile(arguments[0])
    except MidiReadError, err:
        print "Could not load midi data: %s" % err
        sys.exit(1)
    
    problems = check_midi(mid)
    for prob,desc,events in problems:
        print "%s [%s]" % (desc, ", ".join([str(ev) for ev in events]))
    
    if len(problems):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
