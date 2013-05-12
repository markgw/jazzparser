#!/usr/bin/env ../../jazzshell
"""
Load up MIDI files that have been downloaded using C{getmidi.py} and 
preferably laboriously filtered using C{checkmidi.py}.

"""
import sys, os
from optparse import OptionParser
from midi import read_midifile
from jazzparser.utils.csv import UnicodeCsvReader
from jazzparser.utils.midi import note_on_similarity
from jazzparser.data.db_mirrors import SequenceIndex

def main():
    usage = "%prog [options] <names-index> <seq-index>"
    description = "Loads the MIDI downloaded files in the names index "\
                    "and the sequence index with the chord sequences in "\
                    "it and performs operations on the MIDI files. "\
                    "By default, counts the files for each sequence."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-z", "--zeroes", dest="zeroes", action="store_true", help="display the names of sequences with no midi files")
    parser.add_option("-f", "--few", dest="few", action="store", type="int", help="display the names of sequences with few midi files, below the given threshold")
    parser.add_option("--names", dest="names", action="store_true", help="only show the names in the output, not the numbers (only applies to --zeroes or --few)")
    parser.add_option("-d", "--diff", dest="diff", action="store_true", help="check every pair of files for each sequence and report the similarity of the midi notes")
    parser.add_option("--min-diff", dest="min_diff", action="store", type="float", help="the minimum similarity the report when diffing files (see --diff). By default, all are reported (i.e. 0)", default=0.0)
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "You must specify a names index file"
        sys.exit(1)
    if len(arguments) == 1:
        print >>sys.stderr, "You must specify a sequence index file"
        sys.exit(1)
    names_filename = os.path.abspath(arguments[0])
    # Use this directory to get midi files from
    midi_base_dir = os.path.dirname(names_filename)
    names_file = open(names_filename, 'r')
    names = UnicodeCsvReader(names_file)
    lines = list(names)
    
    # Load the sequence index file
    seq_filename = arguments[1]
    sequences = SequenceIndex.from_file(seq_filename)
    
    # Index the entries in the names index by the sequence id
    midi_seqs = {}
    for row in lines[1:]:
        # Col 0: filename
        # Col 1: name from web page
        midi_seqs.setdefault(int(row[2]), []).append((row[0],row[1]))
    # Filter out the ones that don't exist
    def _exists(filename):
        return os.path.exists(os.path.join(midi_base_dir, filename))
    existing_seqs = dict([
                    (seq_id,
                        list(set([(filename,name) for (filename,name) in files if _exists(filename)])))
                    for (seq_id,files) in midi_seqs.items()])
                    
    def _load_midi(filename):
        return read_midifile(open(os.path.join(midi_base_dir, filename), 'r'))
    
    if options.zeroes or options.few is not None:
        # Look for sequences with few (or no) midi files
        if options.zeroes:
            threshold = 1
        else:
            threshold = options.few
        seq_counts = [(seq, 0 if seq.id not in existing_seqs else len(existing_seqs[seq.id])) for seq in sequences]
        few_seqs = [(seq,count) for (seq,count) in seq_counts if count < threshold]
        if options.names:
            print "\n".join([seq.string_name for (seq,count) in few_seqs])
        else:
            print "\n".join(["%s (%d)" % (seq.string_name,count) for (seq,count) in few_seqs])
    elif options.diff:
        # Measure the similarity between each pair of files
        for seq_id,files in existing_seqs.items():
            seq = sequences.sequence_by_id(seq_id)
            print "%s (%d)" % (seq.string_name,len(files))
            # Compare every pair
            for i,(filename0,__) in enumerate(files):
                mid0 = _load_midi(filename0)
                for (filename1,__) in files[:i]:
                    mid1 = _load_midi(filename1)
                    similarity0,similarity1 = note_on_similarity(mid0, mid1)
                    if similarity0 >= options.min_diff:
                        print "  %s, %s: %f" % (filename0, filename1, similarity0)
                    if similarity1 >= options.min_diff:
                        print "  %s, %s: %f" % (filename1, filename0, similarity1)
    else:
        # By default, count the midi files found for each sequence
        for seq in sequences:
            files = existing_seqs.get(seq.id, [])
            print "%s\t%d" % (seq.string_name,len(files))

if __name__ == "__main__":
    main()
