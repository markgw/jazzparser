#!/usr/bin/env ../jazzshell
"""
Evaluates parse results stored in files by comparing them to the gold 
standard results stored along with them, using any distance metric 
available.

This is basically a generalization of result_alignment, which only computes 
alignment scores over tonal space paths.

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

import sys, datetime, numpy
from optparse import OptionParser

from jazzparser.data.parsing import ParseResults
# Currently specific to music_halfspan formalism: could take an option to 
#  select formalism
from jazzparser.formalisms.music_halfspan import Formalism as formalism
from jazzparser.formalisms.base.semantics.distance import command_line_metric

def main():
    usage = "%prog [options] <results-files>"
    description = "Evaluates parse results stored in files by comparing "\
        "them to the gold standard results stored with them, using any "\
        "a variety of metrics."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("--errors", dest="errors", action="store_true", help="display errors reading in the files.")
    parser.add_option("--unscored", dest="unscored", action="store_true", help="output a list of files containing no results (i.e. no successful full parses) and exit")
    parser.add_option("--timeout", dest="timeout", action="store_true", help="output a list of parses that timed out")
    parser.add_option("-m", "--metric", dest="metric", action="store", help="semantics distance metric to use. Use '-m help' for a list of available metrics")
    parser.add_option("--mopt", "--metric-options", dest="mopts", action="append", help="options to pass to the semantics metric. Use with '--mopt help' with -m to see available options")
    parser.add_option("--mc", "--metric-computation", dest="print_computation", action="store_true", help="show the metric's computation trace for each input")
    parser.add_option("-f", "--f-score", dest="f_score", action="store_true", help="outputs recall, precision and f-score for an f-score-based metric. Just uses the same metric 3 times with output=recall, etc. Will only work with appropriate metrics")
    parser.add_option("-q", "--quiet", dest="quiet", action="store_true", help="just output the numbers, nothing else")
    parser.add_option("-t", "--time", dest="time", action="store_true", help="output average parse time. This is output by default, but hidden in quiet mode unless this switch is used")
    options, arguments = parser.parse_args()
        
    if options.f_score:
        # Special case: get 3 metrics
        metrics = []
        opts = options.mopts or []
        for opt in [ "output=precision", "output=recall" ]:
            metrics.append(command_line_metric(formalism, options.metric, 
                                                                opts+[opt]))
        if not options.quiet:
            print "Evaluating precision, recall and f-score on %s" % metrics[0].name
    else:
        # Get a metric according to the options
        metrics = [command_line_metric(formalism, options.metric, options.mopts)]
        if not options.quiet:
            print "Evaluating using metric: %s" % metrics[0].name
    
    if len(arguments) == 0:
        print >>sys.stderr, "Specify at least one file to read the results from"
        sys.exit(1)
    
    # Try loading all the input files
    input_pairs = []
    errors = []
    covered = 0
    input_filenames = []
    times = []
    timed_out = 0
    for filename in arguments:
        # We read in the whole file (it's pickled, so we have to), but don't 
        #  keep the pres object after the loop iteration, because it can 
        #  be very big
        try:
            pres = ParseResults.from_file(filename)
        except ParseResults.LoadError, err:
            if options.errors:
                # Print all load errors
                print >>sys.stderr, "Error loading file: %s" % (err)
            errors.append(filename)
            continue
        
        if options.timeout and pres.timed_out:
            print "Timed out: %s" % filename
        if pres.timed_out:
            timed_out += 1
        
        # Try to get a gold standard result
        gold_result = pres.get_gold_semantics()
        if gold_result is None:
            # Can't evaluate this: ignore it
            if not options.quiet:
                print "No gold result for", filename
            continue
        
        # Get the top result's semantics
        if len(pres.semantics) == 0:
            # No results for this
            input_pairs.append((None, gold_result))
            input_filenames.append(filename)
            if options.unscored:
                print "No results: %s" % filename
            continue
        top_result = pres.semantics[0][1]
        
        # Got a result and gold result for this
        covered += 1
        input_pairs.append((top_result, gold_result))
        input_filenames.append(filename)
        # Check this for compat with old stored results
        if hasattr(pres, 'cpu_time'):
            times.append(pres.cpu_time)
    
    if options.unscored or options.timeout:
        # We've output the resultless files: no more to do
        return
        
    evaluated = len(input_pairs)
    if evaluated:
        coverage = 100.0 * float(covered) / float(evaluated)
    else:
        coverage = 0.0
    # Evaluate metric over all results at once
    # This allows things like f-score to sum properly over the set
    if not options.quiet:
        print "Read %d files with a gold result for evaluation" % evaluated
        print "Coverage: %.2f%%" % coverage
    
    distances = []
    for metric in metrics:
        distance = metric.total_distance(input_pairs)
        if options.quiet:
            print metric.format_distance(distance)
        else:
            print "%s: %s" % (metric.identifier.capitalize(), 
                              metric.format_distance(distance))
        distances.append(distance)
        
        if options.print_computation:
            print "\nMetric computations"
            for (top_result,gold_result),filename in zip(input_pairs,input_filenames):
                print "\n%s" % filename
                print metric.print_computation(top_result, gold_result)
    
    if options.f_score:
        # We'll have shown the recall and precision
        # Now compute the f-score from them
        f_score = 2.0 * distances[0] * distances[1] / (distances[0]+distances[1])
        if options.quiet:
            print "%f%%" % (f_score*100.0)
        else:
            print "F-score: %f%%" % (f_score*100.0)
    
    if not options.quiet or options.time:
        # Output average parse time
        set_times = [t for t in times if t is not None]
        if any(t is None for t in times) and not options.quiet:
            print "Timings for %d/%d results" % (len(set_times), len(times))
        if len(set_times):
            ave_time = sum(set_times, 0.0) / len(set_times)
            ave_time = datetime.timedelta(seconds=ave_time)
            # Calculate the std dev
            std_time = numpy.std(set_times)
            std_time = datetime.timedelta(seconds=std_time)
            if options.quiet:
                print "%s,%s" % (ave_time,std_time)
            else:
                print "Average parse time: %s (%s)" % (ave_time, std_time)
        
    if not options.quiet:
        # Output how many parses timed out
        print "Parses timed out: %d/%d" % (timed_out, len(input_pairs))

if __name__ == "__main__":
    main()
