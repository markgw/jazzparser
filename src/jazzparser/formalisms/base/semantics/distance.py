"""Base distance metric representation.

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

from jazzparser.utils.options import ModuleOption, choose_from_list

class DistanceMetric(object):
    """
    Base class for semantic distance metrics. Formalism-specific distance 
    metrics should be provided as subclasses of this.
    
    """
    OPTIONS = []
    name = "base"
    
    def __init__(self, options={}):
        self.options = ModuleOption.process_option_dict(options, self.OPTIONS)
    
    def _get_identifier(self):
        """
        A human-readable identifier for the metric represented by this instance.
        """
        return self.name
    identifier = property(_get_identifier)
    
    def distance(self, sem1, sem2):
        """
        Compares the two semantics instances and returns a float distance 
        between them.
        
        """
        raise NotImplementedError, "called distance() on base DistanceMetric"
    
    def print_computation(self, sem1, sem2):
        """
        Produces a string showing a derivation of the distance metric that 
        would be returned for the given inputs. This is useful for debugging 
        the metric.
        
        Subclasses are not required to provide this, and there may not always 
        be something sensible to show.
        
        """
        return "Metric '%s' does not provide any computation trace information"\
                % self.name
    
    def total_distance(self, input_pairs):
        """
        Returns the distances summed over the given pairs of inputs. By 
        default, this will just be the sum of the individual distances, 
        but in some cases it may be necessary to do something else, as with 
        f-score.
        
        The input pairs may continue C{None} values. For example, if evaluating 
        the distance of parse results from the gold standard, there may be 
        inputs for which no parse result is obtained. It doesn't make sense, 
        however, for both of the pair to be C{None}.
        
        """
        return sum([self.distance(*pair) for pair in input_pairs], 0.0)
    
    def format_distance(self, dist):
        """
        Format a distance value (as returned from L{distance} or 
        L{total_distance}) as a string suitable for human-readable output.
        
        """
        return "%s" % dist

class FScoreMetric(DistanceMetric):
    """
    Metrics that compute their distance by f-score share a lot of processing. 
    There's no need to put in every one the code for computing f-score from 
    matching stats. Instead, subclasses of this only need to provide the 
    C{fscore_match} method.
    
    """
    OPTIONS = [
        # Subclasses may add more values to the output option, but should at 
        #  least include these ones
        ModuleOption('output', filter=choose_from_list(
                        ['f','precision','recall','inversef']),
                     usage="output=O, where O is one of 'f', 'precision', "\
                        "'recall', 'inversef'",
                     default='inversef',
                     help_text="Select what metric to output. Choose recall "\
                        "or precision for asymmetric metrics. F-score ('f') "\
                        "combines these two. This is inverted ('inversef') "\
                        "to get a distance, rather than similarity"),
    ]
    
    def fscore_match(self, sem1, sem2):
        """
        Subclasses must provide this. It should return a tuple. The first three 
        values must be floats: score given to the matching between the two 
        inputs; max score that could be given to the first; max score for the 
        second. There may be more values in the tuple.
        
        """
        raise NotImplementedError, "f-score metric %s does not provide the "\
            "fscore_match method" % self.name
    
    def distance(self, sem1, sem2):
        scores = self.fscore_match(sem1, sem2)
        alignment = scores[0]
        max_score1 = scores[1]
        max_score2 = scores[2]
        
        # Compute recall and precision
        if alignment == 0:
            recall = 0.0
        else:
            recall = alignment / max_score2
        if self.options['output'] == 'recall':
            return recall
            
        if alignment == 0:
            precision = 0.0
        else:
            precision = alignment / max_score1
        if self.options['output'] == 'precision':
            return precision
        
        # Harmonic mean: f-score
        if alignment == 0:
            f_score = 0.0
        else:
            f_score = 2 * recall * precision / (recall+precision)
        
        if self.options['output'] == 'f':
            return f_score
        else:
            # Assume it must be 'inversef' output
            return 1.0-f_score
    
    def total_distance(self, input_pairs):
        """
        We don't just sum up f-scores to get another f-score.
        
        """
        max_score1 = 0.0
        max_score2 = 0.0
        alignment = 0.0
        
        for (input1,input2) in input_pairs:
            scores = self.fscore_match(input1, input2)
            alignment += scores[0]
            max_score1 += scores[1]
            max_score2 += scores[2]
        
        # Now compute the appropriate metric over the whole set
        if alignment == 0:
            recall = 0
        else:
            recall = alignment / max_score2
        if self.options['output'] == 'recall':
            return recall
            
        if alignment == 0:
            precision = 0
        else:
            precision = alignment / max_score1
        if self.options['output'] == 'precision':
            return precision
        
        # Harmonic mean: f-score
        if alignment == 0:
            f_score = 0
        else:
            f_score = 2 * recall * precision / (recall+precision)
        
        if self.options['output'] == 'f':
            return f_score
        else:
            # Assume it must be 'inversef' output
            return 1.0-f_score
    
    def format_distance(self, dist):
        return "%f%%" % (dist * 100.0)
    

def command_line_metric(formalism, metric_name=None, options=""):
    """
    Utility function to make it easy to load a metric, with user-specified 
    options, from the command line. Takes care of printing help output.
    
    Typical options::
      parser.add_option("-m", "--metric", dest="metric", action="store", 
          help="semantics distance metric to use. Use '-m help' for a list of available metrics")
      parser.add_option("--mopt", "--metric-options", dest="mopts", action="append", 
          help="options to pass to the semantics metric. Use with '--mopt help' with -m to see available options")
    
    You could then call this as::
      metric = command_line_metric(formalism, options.metric, options.mopts)
    
    @return: the metric instantiated with given options
    
    """
    import sys
    from jazzparser.utils.options import ModuleOption, options_help_text
    
    # Get a distance metric
    # Just check this, as it'll cause problems
    if len(formalism.semantics_distance_metrics) == 0:
        print "ERROR: the formalism defines no distance metrics, so this "\
            "script won't work"
        sys.exit(1)
    
    # First get the metric
    if metric_name == "help":
        # Print out a list of metrics available
        print "Available distance metrics:"
        print ", ".join([metric.name for metric in \
                                        formalism.semantics_distance_metrics])
        sys.exit(0)
    
    if metric_name is None:
        # Use the first in the list as default
        metric_cls = formalism.semantics_distance_metrics[0]
    else:
        # Look for the named metric
        for m in formalism.semantics_distance_metrics:
            if m.name == metric_name:
                metric_cls = m
                break
        else:
            # No metric found matching this name
            print "No metric '%s'" % metric_name
            sys.exit(1)
    
    # Options might be given as a list, if the option action was "append"
    if isinstance(options, str):
        options = [options]
    # Now process the metric options
    if options is not None:
        moptstr = options
        if "help" in [s.strip().lower() for s in options]:
            # Output this parser's option help
            print options_help_text(metric_cls.OPTIONS, 
                intro="Available options for metric '%s'" % metric_cls.name)
            sys.exit(0)
        moptstr = ":".join(moptstr)
    else:
        moptstr = ""
    mopts = ModuleOption.process_option_string(moptstr)
    # Instantiate the metric with these options
    metric = metric_cls(options=mopts)
    
    return metric
