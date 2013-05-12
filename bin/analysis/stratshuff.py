#!/usr/bin/env ../jazzshell
"""
Runs stratified shuffling (due to Dan Bikel) using a particular metric to 
judge whether the difference between the evaluation of two sets of results 
is statistically significant.

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

import sys, numpy, os, random
from glob import glob
from optparse import OptionParser
from progressbar import ProgressBar, widgets

from jazzparser.data.parsing import ParseResults
# Currently specific to music_halfspan formalism: could take an option to 
#  select formalism
from jazzparser.formalisms.music_halfspan import Formalism as formalism
from jazzparser.formalisms.base.semantics.distance import command_line_metric, \
                    FScoreMetric

def main():
    usage = "%prog [options] <results-dir1> <results-dir2>"
    description = "Measures statistical significance of two sets of results "\
        "using stratified shuffling. Only works with f-score metrics."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-m", "--metric", dest="metric", action="store", help="semantics distance metric to use. Use '-m help' for a list of available metrics")
    parser.add_option("--mopt", "--metric-options", dest="mopts", action="append", help="options to pass to the semantics metric. Use with '--mopt help' with -m to see available options")
    parser.add_option("--mc", "--metric-computation", dest="print_computation", action="store_true", help="show the metric's computation trace for each input")
    parser.add_option("-q", "--quiet", dest="quiet", action="store_true", help="just output the p-value, nothing else")
    parser.add_option("-i", "--iterations", dest="iterations", action="store", type="int", help="number of shuffles to do. Default: 100,000", default=100000)
    parser.add_option("-p", "--pattern", dest="pattern", action="store", help="filename glob pattern to look for in the directories. Default: *.res", default="*.res")
    parser.add_option("-e", "--exhaustive", dest="exhaustive", action="store_true", help="perform all possible shuffles exhaustively. You probably never want to do this. If not set, shuffles randomly for a fixed number of iterations")
    options, arguments = parser.parse_args()
    
    metric = command_line_metric(formalism, options.metric, options.mopts or [])
    if not isinstance(metric, FScoreMetric):
        print >>sys.stderr, "%s is not an f-score metric. The script is only for f-scores"
        sys.exit(1)
    
    if len(arguments) < 2:
        print >>sys.stderr, "Specify two directories to read results from"
        sys.exit(1)
    res_dir1 = arguments[0]
    res_dir2 = arguments[1]
    
    # Look for .res files in the two directories
    filenames1 = glob(os.path.join(res_dir1, options.pattern))
    filenames2 = glob(os.path.join(res_dir2, options.pattern))
    
    # We must be able to pair the filenames
    basenames1 = [os.path.basename(fn) for fn in filenames1]
    basenames2 = [os.path.basename(fn) for fn in filenames2]
    for basename2 in basenames2:
        if basename2 not in basenames1:
            print "No result in set 1 for %s" % basename2
    for basename1 in basenames1:
        if basename1 not in basenames2:
            print "No result in set 2 for %s" % basename1
    # Only use filenames that are in both directories
    basenames = list(set(basenames1) & set(basenames2))
    
    def _load_res(filename):
        try:
            return ParseResults.from_file(filename)
        except ParseResults.LoadError, err:
            if not options.quiet:
                print >>sys.stderr, "Error loading file %s: %s" % (filename, err)
    
    def _metric_stats(pres, name):
        """ Compute the metric stats for a particular result """
        # Try to get a gold standard result
        gold_result = pres.get_gold_semantics()
        if gold_result is None:
            # Can't evaluate this: ignore it
            if not options.quiet:
                print "No gold result for", name
            return
        # Get the top result's semantics
        if len(pres.semantics) == 0:
            # No results for this
            return metric.fscore_match(None, gold_result)
        else:
            top_result = pres.semantics[0][1]
            return metric.fscore_match(top_result, gold_result)
    
    ######
    # Try loading all the input files and pairing up the results
    paired_results = []
    for basename in basenames:
        # Load the set 1 file
        res1 = _load_res(os.path.join(res_dir1, basename))
        stats1 = _metric_stats(res1, basename)
        if stats1 is None:
            continue
        # Load the set 2 file
        res2 = _load_res(os.path.join(res_dir2, basename))
        stats2 = _metric_stats(res2, basename)
        if stats2 is None:
            continue
        # Pair these results
        paired_results.append((stats1, stats2))
    
    ######
    num_tests = options.iterations if not options.exhaustive else \
                    2**len(paired_results)
    
    def _fscore(alignments, max_scores1, max_scores2):
        # Compute recall, precision and fscore from alignment stats
        recall = 100.0 * sum(alignments) / sum(max_scores2)
        precision = 100.0 * sum(alignments) / sum(max_scores1)
        fscore = 2.0 * recall * precision / (recall+precision)
        return recall, precision, fscore
    
    # Get the actual fscores for the two models
    model1_stats, model2_stats = zip(*paired_results)
    model1_recall, model1_precision, model1_fscore = _fscore(*zip(*model1_stats))
    model2_recall, model2_precision, model2_fscore = _fscore(*zip(*model2_stats))
    # The lower score is (presumably) the baseline
    baseline_fscore = min(model1_fscore, model2_fscore)
    result_fscore = max(model1_fscore, model2_fscore)
    baseline_recall = min(model1_recall, model2_recall)
    result_recall = max(model1_recall, model2_recall)
    baseline_precision = min(model1_precision, model2_precision)
    result_precision = max(model1_precision, model2_precision)
    # Which model is the baseline?
    if model1_fscore < model2_fscore:
        baseline_fscore_model = 1
        result_fscore_model = 2
    else:
        baseline_fscore_model = 2
        result_fscore_model = 1
    if model1_recall < model2_recall:
        baseline_recall_model = 1
        result_recall_model = 2
    else:
        baseline_recall_model = 2
        result_recall_model = 1
    if model1_precision < model2_precision:
        baseline_precision_model = 1
        result_precision_model = 2
    else:
        baseline_precision_model = 2
        result_precision_model = 1
        
    if not options.quiet:
        print "Baseline f-score:    %.2f (model %d)" % (baseline_fscore, baseline_fscore_model)
        print " Baseline recall:    %.2f (model %d)" % (baseline_recall, baseline_recall_model)
        print " Baseline precision: %.2f (model %d)" % (baseline_precision, baseline_precision_model)
        print "Result f-score:      %.2f (model %d)" % (result_fscore, result_fscore_model)
        print " Result recall:      %.2f (model %d)" % (result_recall, result_recall_model)
        print " Result precision:   %.2f (model %d)" % (result_precision, result_precision_model)
    
    if not options.quiet:
        print "Preparing %d shuffles..." % num_tests
    # Prepare the shuffles
    if options.exhaustive:
        # Perform all possible shuffles
        def _shuffle(inlist):
            if len(inlist):
                return sum([
                        [
                            # Unswitched version
                            [inlist[0]]+sublist,
                            # Switched version
                            [(inlist[0][1], inlist[0][0])]+sublist
                        ] for sublist in _shuffle(inlist[1:])], [])
            else:
                # Base: no more items to shuffle
                return [[]]
        shuffles = _shuffle(paired_results)
    else:
        shuffles = []
        indices = list(range(len(paired_results)))
        for iteration in range(num_tests):
            # Select randomly half of the results to shuffle
            to_shuffle = random.sample(indices, len(paired_results)/2)
            shuffled = [stats2 if i in to_shuffle else stats1
                            for i,(stats1,stats2) in enumerate(paired_results)]
            shuffles.append(shuffled)
        
    # Show a progress bar
    if not options.quiet:
        pbar = ProgressBar(widgets=["Shuffling: ", 
                                    widgets.Percentage(),
                                    " ", widgets.Bar(),
                                    ' ', widgets.ETA()], 
                                maxval=num_tests).start()
        # Don't update to often
        pb_update = max(1000, num_tests/100)
    
    # Do the shuffling
    f_matches = 0
    r_matches = 0
    p_matches = 0
    for iteration,shuffled in enumerate(shuffles):
        if not options.quiet and (iteration % pb_update) == 0:
            pbar.update(iteration)
        
        # Use the shuffled stats to compute an f-score for the pretend model
        recall, precision, fscore = _fscore(*zip(*shuffled))
        
        # See whether this did as well as the result
        if fscore >= result_fscore:
            f_matches += 1
        if precision >= result_precision:
            p_matches += 1
        if recall >= result_recall:
            r_matches += 1
    
    if not options.quiet:
        pbar.finish()
    # Calculate the p-values
    fp = float(f_matches+1) / (num_tests+1)
    fp_sig = "*" if fp <= 0.05 else " "
    rp = float(r_matches+1) / (num_tests+1)
    rp_sig = "*" if rp <= 0.05 else " "
    pp = float(p_matches+1) / (num_tests+1)
    pp_sig = "*" if pp <= 0.05 else " "
    
    if not options.quiet:
        print "F-score:   p = %.4e %s  (%d/%d)" % (fp, fp_sig, f_matches, num_tests)
        print "Precision: p = %.4e %s  (%d/%d)" % (pp, pp_sig, p_matches, num_tests)
        print "Recall:    p = %.4e %s  (%d/%d)" % (rp, rp_sig, r_matches, num_tests)
    else:
        print "%.4e" % fp
        print "%.4e" % pp
        print "%.4e" % rp

if __name__ == "__main__":
    main()
