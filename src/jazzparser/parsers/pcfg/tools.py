"""Interactive shell tools for the PCFG parser.

This provides tools for the debugging shell that are specific to the 
PCFG parser. This parser also uses tools from the CKY parser (since it 
is merely a subclass of it).

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
from jazzparser.shell.tools import Tool
from jazzparser.utils.strings import fmt_prob
from jazzparser.utils.tableprint import pprint_table

class ProbabilisticResultListTool(Tool):
    """
    Prints out a particular range of results, or the whole list.
    """
    name = "Result Slice with Probabilities"
    commands = ['pres']
    usage = ("pres [<start> <end>]", "show the results list again, with probabilities, optionally giving a range.")
    help = """
Prints out the current result list, with result numbers and 
probabilities.
Optionally, you may specify a valid range of result numbers to display.

This functions in the same way as the 'res' command, but shows 
probabilities with the results.

The columns in the list are:
 * result number
 * probability
 * ratio of probability to highest probability
 * sign

See also:
  res, the basic result printing command.
"""
    def run(self, args, state):
        if len(args) == 1:
            raise ShellError, "You must specify a start and an end of a range"
        elif len(args):
            start,end = int(args[0]), int(args[1])
            print "Showing results in range [%s:%s]" % (start,end)
            result_list = state.results[start:end]
        else:
            result_list = state.results
        # Display results again
        list_results(result_list, state.options.silent)


class ProbabilityTool(Tool):
    """
    Outputs the probability of a sign.
    """
    name = "Show Probability"
    commands = ['prob']
    usage = ("prob <sign>", "show the probability of the given sign.")
    help = """
Simply outputs the probability of a sign in the chart.
"""
    
    def run(self, args, state):
        from jazzparser.shell.shell import ShellError
        if len(args) == 0:
            raise ShellError, "You must specify a sign from the chart. Specify a sign in the form 'arc_start/arc_end/index'."
        # Get arcs from the chart
        parts = args[0].split("/")
        if len(parts) != 3:
            raise ShellError, "%s is not a valid chart arc. Specify a sign in the form 'arc_start/arc_end/index'." % args[0]
        parts = [int(p) for p in parts]
        # Get the sign
        sign = state.parser.chart.get_signs(parts[0], parts[1])[parts[2]]
        print "%s, %s" % (sign, fmt_prob(sign.probability))
    

class ProbabilisticChartTool(Tool):
    """
    Outputs an arc from the chart, ranked by probability
    """
    name = "Probabilistic Chart Arc"
    commands = ['pchart']
    usage = ("pchart <start> <end>", "show the signs on a given arc in the chart ranked by probability.")
    help = """
Show the signs of an arc in the chart ranked by probabilities.
Specify an arc by its start and end nodes (as with the chart tool).

See also:
  chart, for displaying the whole chart or parts of it.
"""
    
    def run(self, args, state):
        from jazzparser.shell.shell import ShellError
        if len(args) != 2:
            raise ShellError, "You must give a start and end node for the arc."
        # Get arcs from the chart
        start,end = int(args[0]), int(args[1])
        signs = state.parser.chart.get_signs(start, end)
        signs = list(reversed(sorted(signs, key=lambda s: s.probability)))
        print "\n".join(["%s  %s" % (fmt_prob(sign.probability), sign) for sign in signs])


class ProbabilisticDerivationTraceTool(Tool):
    """
    Outputs an arc from the chart, ranked by probability
    """
    name = "Probabilistic Derivation Trace"
    commands = ['pderiv']
    usage = ('pderiv <res>', 'show derivation of numbered result, including '\
                'probabilities of each sign')
    help = """
Just like deriv, but displays probabilities on signs.

See also:
  deriv, the standard derivation trace tool.
"""
    
    def run(self, args, state):
        results = state.results
        # We must have an argument
        from jazzparser.shell.shell import ShellError
        if len(args) == 0:
            raise ShellError, "You must specify the number of a result"
        # Display the trace for this result
        result_num = int(args[0])
        # Use custom formatting of the categories
        def _signfmt(sign):
            return "%s, P=%s" % (sign, sign.probability)
        if result_num < len(results):
            if results[result_num].derivation_trace is None:
                raise ShellError, "Derivation traces have not been stored. Run parser with -d flag to create them"
            else:
                print "Probabilistic derivation trace for result %d: %s" % (result_num,results[result_num])
                print "\n%s" % \
                    results[result_num].derivation_trace.str_indent(\
                        signfmt=_signfmt)
        else:
            raise ShellError, "There are only %d results" % len(results)


def list_results(results, silent):
    """
    Like jazzparser.parser.list_results, but shows probabilities.
    
    Note this doesn't obey the Latex option because I couldn't be 
    bothered.
    
    """
    import math
    def _fmt_index(i):
        return format(i, " >3d")
        
    if len(results) == 0:
        if not silent:
            print "No results"    
    elif silent:
        # Only print the results themselves if we're in silent mode
        for i in range(len(results)):
            print "%s, %s" % (results[i], fmt_prob(results[i].probability))
    else:
        previous_prob = None
        # Get the highest scoring probability to compute the ratio of the others
        if len(results):
            log_highest_prob = results[0].probability
            print "Log highest prob: %s" % log_highest_prob
        table = [["", "", "Prob", "Ratio", "Sign"]]
        for i in range(len(results)):
            # Mark where probabilities are identical
            if previous_prob == results[i].probability:
                same_marker = "*"
            else:
                same_marker = " "
            # Compute the ratio to the highest probability
            prob_ratio = math.exp(results[i].probability - log_highest_prob)
            table.append(["%s>" % _fmt_index(i), same_marker, fmt_prob(math.exp(results[i].probability)), "%.4f" % prob_ratio, str(results[i])])
            previous_prob = results[i].probability
        pprint_table(sys.stdout, table, justs=[True,True,True,True,True])
