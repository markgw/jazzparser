#!/usr/bin/env ../jazzshell
import sys
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
    parser.add_option("-m", "--metric", dest="metric", action="store", help="semantics distance metric to use. Use '-m help' for a list of available metrics")
    parser.add_option("--mopt", "--metric-options", dest="mopts", action="append", help="options to pass to the semantics metric. Use with '--mopt help' with -m to see available options")
    parser.add_option("--mc", "--metric-computation", dest="print_computation", action="store_true", help="show the metric's computation trace for each input")
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "Specify at least one file to read the results from"
        sys.exit(1)
    
    deprec_metric = command_line_metric(formalism, "deprec")
    deps_metric = command_line_metric(formalism, "deps")
    
    # Try loading all the input files
    preses = []
    input_pairs = []
    errors = []
    covered = 0
    input_filenames = []
    for filename in arguments:
        try:
            pres = ParseResults.from_file(filename)
        except ParseResults.LoadError, err:
            if options.errors:
                # Print all load errors
                print >>sys.stderr, "Error loading file: %s" % (err)
            errors.append(filename)
            continue
        preses.append(pres)
        
        # Try to get a gold standard result
        gold_result = pres.get_gold_semantics()
        if gold_result is None:
            # Can't evaluate this: ignore it
            if options.unscored:
                print "No gold result for", filename
            continue
        
        # Get the top result's semantics
        if len(pres.semantics) == 0:
            # No results for this
            input_pairs.append((None, gold_result))
            input_filenames.append(filename)
            continue
        top_result = pres.semantics[0][1]
        
        # Got a result and gold result for this
        covered += 1
        input_pairs.append((top_result, gold_result))
        input_filenames.append(filename)
    
    evaluated = len(input_pairs)
    coverage = 100.0 * float(covered) / float(evaluated)
    # Evaluate metric over all results at once
    # This allows things like f-score to sum properly over the set
    print "Read %d files with a gold result for evaluation" % evaluated
    print "Coverage: %.2f%%" % coverage
    for filename,(sem1,sem2) in zip(input_filenames,input_pairs):
        print filename
        distance_deprec = deprec_metric.distance(sem1, sem2)
        distance_deps = deps_metric.distance(sem1, sem2)
        print "Exact recovery (deprec):",distance_deprec
        print "Maximal alignment (deps):",distance_deps
        if distance_deps > distance_deprec:
            print "!!!!!!!!!!!!!!!!! deps > deprec"
        print

if __name__ == "__main__":
    main()
