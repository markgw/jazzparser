#!/usr/bin/env ../jazzshell
"""
Read in a ParseResults file, just like result_alignment.py. Examines the 
errors that were made and outputs them in context.

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

from jazzparser.evaluation.results import results_alignment, get_top_result
from jazzparser.data.parsing import ParseResults
from jazzparser.utils.tableprint import pprint_table
from jazzparser.grammar import get_grammar

def main():
    usage = "%prog [options] <results-files>"
    description = """\
Read in a ParseResults file, just like result_alignment.py. Examines the \
errors that were made and outputs them in context.
"""
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("--window", "-w", dest="window", action="store", type="int", help="size of context window to show before and after each error. Default: 2", default=2)
    parser.add_option("--distance", "--dist", dest="distance", action="store_true", help="show the total distance travelled in the tonal space by the result and the gold standard")
    parser.add_option("--output-opts", "--oopts", dest="output_opts", action="store", help="options that affect the output formatting. Use '--output-opts help' for a list of options.")
    parser.add_option("--summary-threshold", dest="summary_threshold", action="store", type="int", help="how many times a substitution/insertion/deletion needs to have happened to be including in the summary (default: 4)", default=4)
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "Specify at least one file to read the results from"
        sys.exit(1)
        
    grammar = get_grammar()
    grammar.formalism.cl_output_options(options.output_opts)
        
    # Size of window of context to show
    win = options.window
    
    errors = []
    unscored_files = []
    scored = 0
    unscored = 0
    result_lengths = []
    gold_lengths = []
    insertions = {}
    deletions = {}
    substitutions = {}
    error_types = {}
    for filename in arguments:
        try:
            top_result, gold_result = get_top_result(filename)
        except ParseResults.LoadError, err:
            print >>sys.stderr, "Error loading file: %s" % (err)
            errors.append(filename)
            continue
        else:
            print "============================="
            print "File: %s" % filename
            if top_result is None:
                # No alignment was found
                unscored +=1
                print "No result"
            else:
                # Wrap these up as a semantics, since some functions need that as input
                Sems = grammar.formalism.Semantics.Semantics
                top_sems, gold_sems = Sems(top_result), Sems(gold_result)
                
                # Do the alignment of the top result and gold result
                alignment,gold_seq,result_seq = results_alignment(top_result, gold_result)
                scored += 1
                # Get the actual list of coordinates
                coords = zip(*grammar.formalism.semantics_to_coordinates(gold_sems))[0]
                funs = zip(*grammar.formalism.semantics_to_functions(gold_sems))[0]
                gold_coords = zip(coords, funs)
                
                coords = zip(*grammar.formalism.semantics_to_coordinates(top_sems))[0]
                funs = zip(*grammar.formalism.semantics_to_functions(top_sems))[0]
                result_coords = zip(coords, funs)
                
                print "Result length: %d, gold length: %d" % \
                        (len(result_coords), len(gold_coords))
                result_lengths.append(len(result_coords))
                gold_lengths.append(len(gold_coords))
                
                if options.distance:
                    # Work out the total distance travelled
                    start, end = gold_coords[-1][0], gold_coords[0][0]
                    gold_vect = end[0] - start[0], end[1] - start[1]
                    # And for the actual result
                    start, end = result_coords[-1][0], result_coords[0][0]
                    result_vect = end[0] - start[0], end[1] - start[1]
                    print "Distance travelled:"
                    print "  Gold result:", gold_vect
                    print "  Top result: ", result_vect
                    print
                
                # Put together a table of error windows
                table = [
                    # Header row
                    ["", "Step", "", "Result", "Gold"]
                ]
                
                gold = iter(zip(gold_seq,gold_coords))
                result = iter(zip(result_seq,result_coords))
                context = []
                post_context = 0
                unseen = 0
                for op in alignment:
                    # Keep a record of how many of each error occur
                    if op not in error_types:
                        error_types[op] = 1
                    else:
                        error_types[op] += 1
                    
                    if op == "A":
                        # Aligned pair
                        # Move both sequences on
                        gold_step,gold_point = gold.next()
                        result_step,result_point = result.next()
                        if post_context > 0:
                            # Show this as part of the post-context of an error
                            table.append(["A", str(gold_step), "", str(result_point), str(gold_point)])
                            context = []
                            post_context -= 1
                        else:
                            # Add this to the rolling window of pre-context
                            if len(context) >= win:
                                # We've not shown something here
                                unseen += 1
                            if win > 0:
                                context.append((gold_step, gold_point, result_step, result_point))
                                context = context[-win:]
                    else:
                        # Mark if there was something we didn't show
                        if unseen:
                            table.append(["", "   ...%d..." % unseen, "", "", ""])
                            unseen = 0
                        if context:
                            # Show the error's pre-context
                            for (pre_gold_step,pre_gold_point,__,pre_result_point) in context:
                                table.append(["A", str(pre_gold_step), "", str(pre_result_point), str(pre_gold_point)])
                            context = []
                        
                        if op == "I":
                            # Inserted in the result
                            result_step,result_point = result.next()
                            table.append(["I", str(result_step), "", str(result_point), ""])
                            if str(result_step) not in insertions:
                                insertions[str(result_step)] = 1
                            else:
                                insertions[str(result_step)] += 1
                        elif op == "D":
                            # Deleted in the result
                            gold_step,gold_point = gold.next()
                            table.append(["D", str(gold_step), "", "", str(gold_point)])
                            if str(gold_step) not in deletions:
                                deletions[str(gold_step)] = 1
                            else:
                                deletions[str(gold_step)] += 1
                        else:
                            # Substituted
                            result_step, result_point = result.next()
                            gold_step, gold_point = gold.next()
                            table.append([str(op), str(result_step), "for %s" % str(gold_step), str(result_point), str(gold_point)])
                            subst_key = "%s > %s" % (gold_step, result_step)
                            if subst_key not in substitutions:
                                substitutions[subst_key] = 1
                            else:
                                substitutions[subst_key] += 1
                        # After anything other than an alignment, cancel the 
                        #  context window
                        context = []
                        # Show up to <win> in the post-context of alignments
                        post_context = win
                # Mark if there was something at the end we didn't show
                if unseen:
                    table.append(["", "   ...%d..." % unseen, "", "", ""])
                # Print out the table
                pprint_table(sys.stdout, table, justs=[True,True,True,True,True])
        
        print "\n"
    print "Processed %d result sets" % (scored+unscored)
    print "Errors processing %d result sets" % len(errors)
    print "Average result length: %.2f (%d)" % (
                    float(sum(result_lengths)) / len(result_lengths),
                    sum(result_lengths))
    print "Average gold length:   %.2f (%d)" % (
                    float(sum(gold_lengths)) / len(gold_lengths),
                    sum(gold_lengths))
    # A table of error types
    print 
    print "Error types:"
    error_table = []
    for error, count in error_types.items():
        if error != "A":
            error_table.append([error, "%d" % count])
    pprint_table(sys.stdout, error_table, justs=[True, False])
    # Show common mistakes
    # Substitutions
    print 
    print "Common substitutions:"
    subst_table = []
    for subst,count in reversed(sorted(substitutions.items(), key=lambda x:x[1])):
        if count >= options.summary_threshold:
            subst_table.append(["%s" % subst, "%d" % count])
    pprint_table(sys.stdout, subst_table, justs=[True, False])
    
    # Deletions
    print
    print "Common deletions:"
    del_table = []
    for deln,count in reversed(sorted(deletions.items(), key=lambda x:x[1])):
        if count >= options.summary_threshold:
            del_table.append(["%s" % deln, "%d" % count])
    pprint_table(sys.stdout, del_table, justs=[True, False])
    
    # Insertions
    print 
    print "Common insertions:"
    ins_table = []
    for ins,count in reversed(sorted(insertions.items(), key=lambda x:x[1])):
        if count >= options.summary_threshold:
            ins_table.append(["%s" % ins, "%d" % count])
    pprint_table(sys.stdout, ins_table, justs=[True, False])

if __name__ == "__main__":
    main()
