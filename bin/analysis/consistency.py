#!/usr/bin/env ../jazzshell
"""
Evaluate annotator consistency.

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

from jazzparser.parsers import ParseError
from jazzparser.data.input import DbInput
from jazzparser.grammar import get_grammar
from jazzparser.data.db_mirrors.consistency import ConsistencyData
# Currently specific to music_halfspan formalism: could take an option to 
#  select formalism
from jazzparser.formalisms.music_halfspan import Formalism as formalism
from jazzparser.formalisms.base.semantics.distance import command_line_metric
from jazzparser.evaluation.parsing import parse_sequence_with_annotations

def main():
    usage = "%prog [options] <consistency-data>"
    description = "Evaluates annotator consistency."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-m", "--metric", dest="metric", action="store", 
        help="semantics distance metric to use. Use '-m help' for a list of "\
            "available metrics")
    parser.add_option("--mopt", "--metric-options", dest="mopts", 
        action="append", 
        help="options to pass to the semantics metric. Use with '--mopt help' "\
            "with -m to see available options")
    parser.add_option("-f", "--f-score", dest="f_score", action="store_true", 
        help="outputs recall, precision and f-score for an f-score-based "\
            "metric. Just uses the same metric 3 times with output=recall, "\
            "etc. Will only work with appropriate metrics")
    options, arguments = parser.parse_args()
    
    grammar = get_grammar()
    
    if options.metric is not None:
        use_metric = True
        if options.f_score:
            # Special case: get 3 metrics
            metrics = []
            opts = options.mopts or []
            for opt in [ "output=precision", "output=recall", "output=f" ]:
                metrics.append(command_line_metric(formalism, options.metric, 
                                                                    opts+[opt]))
            print "Evaluating precision, recall and f-score on %s" % metrics[0].name
        else:
            # Get a metric according to the options
            metrics = [command_line_metric(formalism, options.metric, options.mopts)]
            print "Evaluating using metric: %s" % metrics[0].name
    else:
        use_metric = False
    
    
    if len(arguments) < 1:
        print >>sys.stderr, "Specify a consistency data file"
        sys.exit(1)
    filename = arguments[0]
    
    consdata = ConsistencyData.from_file(filename)
    
    # Count up matching annotations
    matches = 0
    chords = 0
    for ann1,ann2 in consdata:
        for chord1,chord2 in zip(ann1,ann2):
            chords += 1
            if chord1.category == chord2.category:
                matches += 1
    # Count matching coordination points
    rean_coords = sum(sum(
                    [1 for crd in seq if crd.treeinfo.coord_unresolved])
                        for seq,gs in consdata) + \
                  sum(sum(
                    [1 for crd in seq if crd.treeinfo.coord_resolved])
                        for seq,gs in consdata)
    gold_coords = sum(sum(
                    [1 for crd in gs if crd.treeinfo.coord_unresolved])
                        for seq,gs in consdata) + \
                  sum(sum(
                    [1 for crd in gs if crd.treeinfo.coord_resolved])
                        for seq,gs in consdata)
    match_coords = sum(sum(
                    [1 for crdr,crdg in zip(seq,gs) if 
                                            crdr.treeinfo.coord_unresolved 
                                            and crdg.treeinfo.coord_unresolved])
                        for seq,gs in consdata) + \
                   sum(sum(
                    [1 for crdr,crdg in zip(seq,gs) if 
                                            crdr.treeinfo.coord_resolved 
                                            and crdg.treeinfo.coord_resolved])
                        for seq,gs in consdata)
    # Compute precision, recall and f-score from this
    precision = 100.0 * (matches + match_coords) / (chords + rean_coords)
    recall = 100.0 * (matches + match_coords) / (chords + gold_coords)
    fscore = 2.0 * precision * recall / (precision+recall)
    print "%d chords" % chords
    print "\nCategory and coordination accuracy:"
    print "Precision: %.2f" % precision
    print "Recall: %.2f" % recall
    print "F-score: %.2f" % fscore
    
    if use_metric:
        print 
        def _parse_seq(seq):
            # Parse the annotations to get a semantics
            try:
                gold_parses = parse_sequence_with_annotations(
                                                    DbInput.from_sequence(seq), 
                                                    grammar=grammar,
                                                    allow_subparses=False)
                # Got a result: return its semantics
                return gold_parses[0].semantics
            except ParseError, err:
                # Could not parse annotated sequence
                print >>sys.stderr, "Could not parse sequence '%s': %s" % \
                                                        (seq.string_name, err)
                return 
        
        # Prepare pairs of gold-standard parse results from the two annotations
        sem_pairs = [
            (_parse_seq(ann1), _parse_seq(ann2)) for (ann1,ann2) in consdata
        ]
        # Compute the distance using the metrics
        for metric in metrics:
            distance = metric.total_distance(sem_pairs)
            print "%s: %s" % (metric.identifier.capitalize(), 
                              metric.format_distance(distance))


if __name__ == "__main__":
    main()
