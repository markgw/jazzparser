#!/usr/bin/env ../../jazzshell
"""
Nasty script to speed up the process of checking midi files.

"""
import sys, os, csv, subprocess
from optparse import OptionParser

def main():
    usage = "%prog [options] <names-index>"
    description = "Plays each midi file in a names index and asks "\
                    "whether to delete it"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-s", "--start", dest="start", action="store", type="int", help="start for the given line of the names file")
    parser.add_option("-q", "--quiet", dest="quiet", action="store_true", help="quiet mode - just ignores missing files without complaining")
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify a names index file"
        sys.exit(1)
    names_filename = os.path.abspath(arguments[0])
    base_dir = os.path.dirname(names_filename)
    names_file = open(names_filename, 'r')
    names = csv.reader(names_file)
    lines = list(names)
    
    if options.start is not None:
        # Use the specified start line (0 not allowed)
        first_line = max(options.start, 1)
    else:
        first_line = 1
    
    for i,row in enumerate(lines[first_line:]):
        linenum = first_line+i
        filename = os.path.join(base_dir, row[0])
        name = row[1]
        if options.quiet:
            if os.path.exists(filename):
                print "\n\n<<<<<<<<<< Line %d >>>>>>>>>>" % linenum
                print "File: %s" % row[0]
                print "Reported name: %s" % name
            else:
                continue
        else:
            print "\n\n<<<<<<<<<< Line %d >>>>>>>>>>" % linenum
            print "File: %s" % row[0]
            print "Reported name: %s" % name
            if not os.path.exists(filename):
                if not options.quiet:
                    print "Could not find file: %s" % filename
                continue
        
        while True:
            print "\nPlaying (interrupt to stop)..."
            # Try playing the file with timidity
            try:
                subprocess.call(["timidity", filename])
            except KeyboardInterrupt:
                print
            # Clear the stdin so we don't get anything that was pressed during playback
            sys.stdin.flush()
            
            try:
                # Let the user choose what to do with this file
                response = None
                while response not in ['d','','p']:
                    response = raw_input("Delete (d), play again (p), or leave (blank) ").lower()
                if response == 'd':
                    print "Deleting %s" % filename
                    os.remove(filename)
                    break
                elif response == 'p':
                    continue
                elif response == '':
                    # Don't do anything - continue to the next file
                    break
            except KeyboardInterrupt:
                print "\nExiting"
                sys.exit(0)

if __name__ == "__main__":
    main()
