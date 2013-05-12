#!/usr/bin/env ../../jazzshell
"""
Goes through a load of sequences and tries to find MIDI files for 
each one (looking up by name on the web). Writes them all to files 
on disk.

"""
import sys, os, string
from optparse import OptionParser

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.utils.web import find_midi_files, SOURCES
from jazzparser.utils.csv import UnicodeCsvWriter

DEFAULT_PARTITIONS = 10

def main():
    usage = "%prog [options] <in-file>"
    description = "Reads in a sequence index file and tries to find "\
        "midi files of each song by looking up the name online. Writes "\
        "them all to the given directory."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-i", "--index", dest="index", action="store", type="int", help="select a single sequence by index from the file and just get files for that sequence")
    parser.add_option("-n", "--name", dest="name", action="store_true", help="interpret the arguments as a song name to look up directly instead of fetching the name of a sequence from a file")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", help="verbose output")
    parser.add_option("-s", "--source", dest="sources", action="append", help="sources to get midi files from (use option multiple times for multiple sources). Possible values: %s. Default: all sources." % ", ".join(SOURCES))
    parser.add_option("-r", "--resume", dest="resume", action="store", type="int", help="resume lookup at the given sequence index. Sequences before this index will be skipped at the names entries will be appended to an existing file.")
    parser.add_option("-d", "--dir", dest="dir", action="store", help="directory to output files to. By default, outputs to the current directory")
    options, arguments = parser.parse_args()
        
    if options.dir is not None:
        outdir = os.path.abspath(options.dir)
    else:
        outdir = os.path.abspath(os.getcwd())
        
    if not os.path.isdir(outdir):
        print >>sys.stderr, "%s is not a directory" % outdir
    
    if options.name is not None:
        sequences = [(" ".join(arguments),None)]
    else:
        if len(arguments) == 0:
            print >>sys.stderr, "You must specify an input sequence index file"
            sys.exit(1)
        filename = os.path.abspath(arguments[0])
        
        # Read in the data file
        seqs = SequenceIndex.from_file(filename)
        if options.index is not None:
            seq = seqs.sequence_by_index(options.index)
            sequences = [(seq.name,seq.id)]
        elif options.resume is not None:
            sequences = [(seq.name,seq.id) for seq in seqs.sequences[options.resume:]]
        else:
            sequences = [(s.name,s.id) for s in seqs.sequences]
    
    if options.verbose:
        verbose_out = sys.stderr
        out_prefix = ">>> "
    else:
        verbose_out = None
        out_prefix = ""
    
    # Output a name list
    if options.resume is None:
        namefile = open(os.path.join(outdir, "NAMES"), 'w')
    else:
        # Append data to the old file
        namefile = open(os.path.join(outdir, "NAMES"), 'a')
    try:
        names = UnicodeCsvWriter(namefile)
        if options.resume is None:
            # Add a header if we're not appending to an old file
            names.writerow(['Filename','Reported song name','Database id'])
        
        for seq_name,seq_id in sequences:
            print "%sLooking up %s" % (out_prefix, seq_name)
            files = find_midi_files(seq_name, sources=options.sources, verbose_out=verbose_out)
            print "%s  Found %d files" % (out_prefix, len(files))
            # Create a suitable base filename
            base_filename = "_".join(\
                seq_name.encode('ascii', 'ignore').translate(string.maketrans("",""), string.punctuation).lower().split())
            for i,(data,name) in enumerate(files):
                filename = u"%s-%d.mid" % (base_filename,i)
                full_filename = os.path.join(outdir, filename)
                # Write each midi file out individually
                f = open(full_filename, 'w')
                f.write(data)
                f.close()
                # Keep a list of the name reported for each file
                names.writerow([filename,name,seq_id])
            namefile.flush()
    finally:
        namefile.close()

if __name__ == "__main__":
    main()
