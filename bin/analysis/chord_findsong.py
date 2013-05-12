#!/usr/bin/env ../jazzshell
"""
Like findsong, but searches by chord label sequence similarity.

============================== License ========================================
 Copyright (C) 2008, 2010-12 University of Edinburgh, Mark Granroth-Wilding
 
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
from optparse import OptionParser

from jazzparser.data.parsing import ParseResults
from jazzparser.parsers.cky.parser import DirectedCkyParser
from jazzparser.utils.options import options_help_text, ModuleOption
from jazzparser.utils.tableprint import pprint_table
from jazzparser.data.input import command_line_input, SegmentedMidiInput
from jazzparser.misc.chordlabel import HPChordLabeler
from jazzparser.data.db_mirrors import Chord
from jazzparser.data.db_mirrors.distance import chord_sequence_match_score, \
                                chord_sequence_alignment

def main():
    usage = "%prog [options] <chord-corpus-file> <chord-labeling-model> <midi-file>"
    description = "Like findsong, but searches by chord label sequence "\
        "similarity. The input is not a results file, but a midi file, or "\
        "a midi bulk input (CSV)."
    parser = OptionParser(usage=usage)
    parser.add_option("--popt", "--parser-options", dest="popts", action="append", help="specify options for the parser that interprets the gold standard annotations. Type '--popt help' to get a list of options (we use a DirectedCkyParser)")
    parser.add_option("-r", "--print-results", dest="print_results", action="store", default=5, type="int", help="number of top search results to print for each query (parse result). Default: 5. Use -1 to print distances from all songs in the corpus")
    parser.add_option("--filetype", "--ft", dest="filetype", action="store", default="bulk-segmidi", help="filetype to read in. Use 'segmidi' to read a single midi file, or 'bulk-segmidi' (default) to read many from a CSV")
    parser.add_option("--file-options", "--fopt", dest="file_options", action="store", help="options for the input file. Type '--fopt help', using '--ft <type>' to select file type, for a list of available options.")
    parser.add_option("--labeler-options", "--lopt", dest="labeler_options", action="store", help="options for the labeler. Type '--lopt help' for a list of available options.")
    parser.add_option("-g", "--gold-only", dest="gold_only", action="store_true", help="skip results that have no gold standard sequence associated with them (we can't tell which is the right answer for these)")
    parser.add_option("--align", "--print-alignment", dest="print_alignment", action="store_true", help="print out the full alignment between the labeling and the top match")
    options, arguments = parser.parse_args()
    
    # Process parser options
    if options.popts is not None:
        poptstr = options.popts
        if "help" in [s.strip().lower() for s in poptstr]:
            # Output this parser's option help
            print options_help_text(DirectedCkyParser.PARSER_OPTIONS, intro="Available options for gold standard interpreter")
            sys.exit(0)
        poptstr = ":".join(poptstr)
    else:
        poptstr = ""
    popts = ModuleOption.process_option_string(poptstr)
    # Check that the options are valid
    try:
        DirectedCkyParser.check_options(popts)
    except ModuleOptionError, err:
        logger.error("Problem with parser options (--popt): %s" % err)
        sys.exit(1)
    
    if len(arguments) < 3:
        print >>sys.stderr, "Specify a song corpus name, a chord labeling "\
            "model name, and a file to read midi data from"
        sys.exit(1)
    
    # First argument is an TonalSpaceAnalysisSet
    corpus_filename = arguments[0]
    # Load the corpus file
    corpus = command_line_input(corpus_filename, 
                                    filetype='bulk-db', 
                                    options="")
    
    # The rest of the args are midi files to analyze
    filename = arguments[2]
    input_data = command_line_input(filename, 
                                    filetype=options.filetype, 
                                    options=options.file_options,
                                    allowed_types=['segmidi', 'bulk-segmidi'])
    if isinstance(input_data, SegmentedMidiInput):
        # Single input
        input_data = [input_data]
    
    
    # Work out how many results to print out
    if options.print_results == -1:
        print_up_to = None
    else:
        print_up_to = options.print_results
        
    
    # Process the labeler options
    lopt_dict = ModuleOption.process_option_string(options.labeler_options)
    # No point in getting more than one label, since we'll only use one
    lopt_dict['viterbi'] = True
    lopt_dict['nokey'] = True
    # Load the chord labeling model
    model_name = arguments[1]
    model = HPChordLabeler.load_model(model_name)
    
    ranks = []
    num_ranked = 0
    for midi_file in input_data:
        # Skip any inputs that don't have a gold sequence associated with them
        # We won't know what the correct answer is
        if options.gold_only and midi_file.gold is None:
            continue
        
        print "######################"
        print "Processing %s" % midi_file.name
        
        # Try to get a correct answer from the PR file
        if midi_file.gold is None:
            print "No correct answer specified in input file"
            correct_song = None
        else:
            # Process the name of the sequence in the same way that 
            #  TonalSpaceAnalysisSet does
            # Ideally, they should make a common function call, but let's be 
            #  bad for once
            correct_song = midi_file.gold.string_name.lower()
            print "Correct answer: %s" % correct_song
        
        
        # Perform labeling on this midi input
        labels = model.label(midi_file, options=lopt_dict)
        
        # Map these chord labels onto the corpus labels and create dbinput 
        #  representations of the chords
        labels = model.map_to_corpus(labels)
        # Get just the single chord for each time
        labels = [timestep[0][0] for timestep in labels]
        # Convert to DbInput-style chord representation
        labels = [Chord(root=chord.root,
                        type=chord.label) for chord in labels]
        
        # Look for repeated chords and remove them, setting durations instead
        current_chord = labels[0]
        current_chord.duration = 1
        single_chords = [ current_chord ]
        for current_chord in labels[1:]:
            # Check if this is the same as the last one
            if single_chords[-1].root == current_chord.root and \
                    single_chords[-1].type == current_chord.type:
                # Don't repeat it: just lengthen the first one
                single_chords[-1].duration += 1
            else:
                # New chord: add it to the sequence
                current_chord.duration = 1
                single_chords.append(current_chord)
        labels = single_chords
        
        # Compare this chord sequence to every one in the corpus
        # Compute the matching score between the two sequences
        distances = []
        for sequence in corpus:
            match_score, transposition = chord_sequence_match_score(labels, \
                                                        list(sequence.chords))
            distances.append(
                (sequence.string_name.lower(), 
                 1.0-match_score,
                 sequence, transposition))
        distances.sort(key=lambda x:x[1])
        
        print
        # Print out the top results, as many as requested
        top_results = distances[:print_up_to]
        table = [["","Song","Distance"]] + [
                        ["*" if res[0] == correct_song else "", 
                         "%s" % res[0], 
                         "%.2f" % res[1]] for res in top_results]
        pprint_table(sys.stdout, table, default_just=True)
        print
        
        if correct_song is not None:
            # Look for the correct answer in the results
            for rank,(name,distance,seq,trans) in enumerate(distances):
                # Match up the song name to the correct one
                if name == correct_song:
                    correct_rank = rank
                    break
            else:
                # The song name was not found in the corpus at all
                correct_rank = None
            
            if correct_rank is None:
                print "Song was not found in corpus"
            else:
                print "Correct answer got rank %d" % correct_rank
                # Record the ranks so we can compute the MRR
                ranks.append(correct_rank+1)
                num_ranked += 1
            print
        
        if options.print_alignment:
            # Just get the top result
            top_name, top_score, top_seq, top_transpose = distances[0]
            # Do the transposition for output
            trans_labels = [Chord(root=(c.root+top_transpose)%12, type=c.type) \
                                                for c in labels]
            # Do the alignment again and this time get the actual 
            #  aligned chords
            alignment = chord_sequence_alignment(trans_labels, list(top_seq.chords))
            print "Input transposed by %d" % top_transpose
            table = [["Input","Ref"]] + \
                [[str(inp), str(ref)] for (inp,ref) in alignment]
            pprint_table(sys.stdout, table)
            print
    
    print "\nGot ranks for %d sequences" % num_ranked
    # Compute the mean reciprocal rank, the reciprocal of the harmonic mean 
    #  of the ranks of the correct answers
    mrr = sum([0.0 if rank is None else 1.0/rank for rank in ranks], 0.0) \
                                                                / len(ranks)
    print "Mean reciprocal rank: %f" % mrr
    hmr = 1.0/mrr
    print "Harmonic mean rank: %f" % hmr

if __name__ == "__main__":
    main()
