#!/usr/bin/env ../jazzshell
"""
Compares the f-score given by the alignment of dependency graph nodes that 
optimizes dependency recovery and that given by the correct alignment of 
dependency graph nodes (according to timings, when the results were produced 
on the same inputs as the gold standard).

"""
import sys, os
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
    parser.add_option("--tabbed", dest="tabbed", action="store_true", help="output a tabbed table of values")
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "Specify at least one file to read the results from"
        sys.exit(1)
    
    deprec_metric = command_line_metric(formalism, "deprec", options="output=f")
    deps_metric = command_line_metric(formalism, "deps", options="output=f")
    
    # Try loading all the input files
    input_pairs = []
    errors = []
    covered = 0
    input_filenames = []
    for filename in arguments:
        try:
            pres = ParseResults.from_file(filename)
        except ParseResults.LoadError, err:
            errors.append(filename)
            continue
        
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
    print >>sys.stderr,"Read %d files with a gold result for evaluation" % evaluated
    print >>sys.stderr,"Coverage: %.2f%%" % coverage
    if options.tabbed:
        print "Filename\tDeprec\tDeps\tPercent over"
    for filename,(sem1,sem2) in zip(input_filenames,input_pairs):
        #distance_deprec = deprec_metric.distance(sem1, sem2)
        #distance_deps = deps_metric.distance(sem1, sem2)
        # Get the number of deps aligned by each metric
        deps_recovery,__,__ = deps_metric.fscore_match(sem1, sem2)
        deprec_recovery,__,__ = deprec_metric.fscore_match(sem1, sem2)
        if deprec_recovery > 0:
            percent_over = "%.2f" % \
                (float(deps_recovery-deprec_recovery) / deprec_recovery * 100.0)
        else:
            percent_over = ""
        
        if options.tabbed:
            filename_s = os.path.basename(filename)
            print "%s\t%f\t%f\t%s" % (filename_s, deprec_recovery, 
                                deps_recovery, percent_over)
        else:
            print filename
            print "Exact recovery (deprec): %d" % deprec_recovery
            print "Maximal alignment (deps): %d" % deps_recovery
            print "Maximizing overestimated DR by: %s%%" % percent_over
            print

if __name__ == "__main__":
    main()
