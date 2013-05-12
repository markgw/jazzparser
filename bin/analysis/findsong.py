#!/usr/bin/env ../jazzshell
"""
Perform song identification by loading up a corpus of harmonic analyses 
and comparing parse results to all of them, according to some distance metric.

"""
"""
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
from jazzparser.data.tonalspace import TonalSpaceAnalysisSet
from jazzparser.formalisms.music_halfspan import Formalism
from jazzparser.utils.tableprint import pprint_table

def main():
    usage = "%prog [options] <song-set> <results-file0> [<results-file1> ...]"
    parser = OptionParser(usage=usage)
    parser.add_option("--popt", "--parser-options", dest="popts", action="append", help="specify options for the parser that interprets the gold standard annotations. Type '--popt help' to get a list of options (we use a DirectedCkyParser)")
    parser.add_option("-m", "--metric", dest="metric", action="store", help="semantics distance metric to use. Use '-m help' for a list of available metrics")
    parser.add_option("--mopt", "--metric-options", dest="mopts", action="append", help="options to pass to the semantics metric. Use with '--mopt help' with -m to see available options")
    parser.add_option("-r", "--print-results", dest="print_results", action="store", default=5, type="int", help="number of top search results to print for each query (parse result). Default: 5. Use -1 to print distances from all songs in the corpus")
    parser.add_option("-g", "--gold-only", dest="gold_only", action="store_true", help="skip results that have no gold standard sequence associated with them (we can't tell which is the right answer for these)")
    parser.add_option("--mc", "--metric-computation", dest="metric_computation", action="store_true", help="output the computation information for the metric between the parse result and each top search result")
    options, arguments = parser.parse_args()
    
    # For now, we always use the music_halfspan formalism with this script
    # If we wanted to make it generic, we'd just load the formalism according 
    #  to a command-line option
    formalism = Formalism
    
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
    
    # Get a distance metric
    # Just check this, as it'll cause problems
    if len(formalism.semantics_distance_metrics) == 0:
        print "ERROR: the formalism defines no distance metrics, so this "\
            "script won't work"
        sys.exit(1)
    # First get the metric
    if options.metric == "help":
        # Print out a list of metrics available
        print "Available distance metrics:"
        print ", ".join([metric.name for metric in \
                                        formalism.semantics_distance_metrics])
        sys.exit(0)
    if options.metric is None:
        # Use the first in the list as default
        metric_cls = formalism.semantics_distance_metrics[0]
    else:
        for m in formalism.semantics_distance_metrics:
            if m.name == options.metric:
                metric_cls = m
                break
        else:
            # No metric found matching this name
            print "No metric '%s'" % options.metric
            sys.exit(1)
    print >>sys.stderr, "Using distance metric: %s" % metric_cls.name
    # Now process the metric options
    if options.mopts is not None:
        moptstr = options.mopts
        if "help" in [s.strip().lower() for s in moptstr]:
            # Output this parser's option help
            print options_help_text(metric_cls.OPTIONS, intro="Available options for metric '%s'" % metric_cls.name)
            sys.exit(0)
        moptstr = ":".join(moptstr)
    else:
        moptstr = ""
    mopts = ModuleOption.process_option_string(moptstr)
    # Instantiate the metric with these options
    metric = metric_cls(options=mopts)
    
        
    if len(arguments) < 2:
        print >>sys.stderr, "Specify a song corpus name and one or more files to read results from"
        sys.exit(1)
    
    # First argument is an TonalSpaceAnalysisSet
    corpus_name = arguments[0]
    # Load the corpus file
    corpus = TonalSpaceAnalysisSet.load(corpus_name)
    
    # The rest of the args are result files to analyze
    res_files = arguments[1:]

    # Work out how many results to print out
    if options.print_results == -1:
        print_up_to = None
    else:
        print_up_to = options.print_results
    
    ranks = []
    num_ranked = 0
    for filename in res_files:
        # Load the parse results
        pres = ParseResults.from_file(filename)
        if options.gold_only and pres.gold_sequence is None:
            # Skip this sequence altogether if requested
            continue
        print "######################"
        print "Read %s" % filename
        
        # Try to get a correct answer from the PR file
        if pres.gold_sequence is None:
            print "No correct answer specified in input file"
            correct_song = None
        else:
            # Process the name of the sequence in the same way that 
            #  TonalSpaceAnalysisSet does
            # Ideally, they should make a common function call, but let's be 
            #  bad for once
            correct_song = pres.gold_sequence.string_name.lower()
            print "Correct answer: %s" % correct_song
        
        # Could have an empty result list: skip if it does
        if len(pres.semantics) == 0:
            print "No results"
            # Failed to get any result: if this is one of the sequences that 
            #  is in the corpus, count it as a 0 result. Otherwise, skip: 
            #  we wouldn't have counted it anyway
            num_ranked += 1
            ranks.append(None)
            continue
        result = pres.semantics[0][1]
        
        # Compare to each of the songs
        distances = []
        for name,songsem in corpus:
            # Get the distance from this song
            dist = metric.distance(result, songsem)
            distances.append((name,dist,songsem))
        # Sort them to get the closest first
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
            for rank,(name,distance,__) in enumerate(distances):
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
        
        if options.metric_computation:
            print "Explanation of top result:"
            print metric.print_computation(result, distances[0][2])
            print
    
    if num_ranked:
        print "\nGot ranks for %d sequences" % num_ranked
        # Compute the mean reciprocal rank, the reciprocal of the harmonic mean 
        #  of the ranks of the correct answers
        mrr = sum([0.0 if rank is None else 1.0/rank for rank in ranks], 0.0) \
                                                                    / len(ranks)
        print "Mean reciprocal rank: %f" % mrr
        if mrr > 0.0:
            hmr = 1.0/mrr
            print "Harmonic mean rank: %f" % hmr
        
        succ_ranks = [rank for rank in ranks if rank is not None]
        print "\nIncluding only successful parses (%d):" % len(succ_ranks)
        mrr_succ = sum([1.0/rank for rank in succ_ranks], 0.0) / len(succ_ranks)
        print "Mean reciprocal rank: %f" % mrr_succ
        if mrr_succ > 0.0:
            hmr_succ = 1.0/mrr_succ
            print "Harmonic mean rank: %f" % hmr_succ
    else:
        print "\nNo results to analyze"

if __name__ == "__main__":
    main()
