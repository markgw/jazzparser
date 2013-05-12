#!/usr/bin/env ../jazzshell
"""
Outputs a Latex summary of the model's parameters

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

import sys, os
from optparse import OptionParser
from datetime import datetime

from jazzparser.utils.config import parse_args_with_config
from jazzparser.misc.raphsto import format_state_as_chord, \
            format_state, constants, MODEL_TYPES

def main():
    usage = "%prog [options] <model-name>"
    description = "Outputs a Latex summary of a raphsto model's parameters"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-m', '--model-type', dest="model_type", action="store", help="select a model type: one of %s (default: standard)" % ", ".join(mt for mt in MODEL_TYPES.keys()), default="standard")
    parser.add_option('--head', dest="head", action="store", help="Latex command to use for headings", default="\\subsection")
    parser.add_option('--subhead', dest="subhead", action="store", help="Latex command to use for subheadings", default="\\subsubsection*")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print >>sys.stderr, "You must specify a model name as the first argument"
        sys.exit(1)
    model_name = arguments[0]
    
    if options.model_type not in MODEL_TYPES:
        print >>sys.stderr, "Model type must be one of: %s" % ", ".join(mt for mt in MODEL_TYPES)
        sys.exit(1)
    model_cls = MODEL_TYPES[options.model_type]
    
    # Load the model
    model = model_cls.load_model(model_name)
    
    if options.model_type == "unigram":
        show_em = True
        show_ktrans = False
        show_ctrans = False
        show_chord = False
    else:
        show_em = True
        show_ktrans = True
        show_ctrans = True
        show_chord = True
    
    def _heading(title):
        return "%s{%s}" % (options.head, title)
    def _subheading(title):
        return "\n%s{%s}\n" % (options.subhead, title)
    
    if show_em:
        print _heading("Emission Distribution")
        DMEANING = {
            0 : 'chord root',
            1 : 'chord 3rd',
            2 : 'chord 5th',
            3 : 'other scale note',
            4 : 'non-scale note',
        }
        BCMEANING = {
            0 : '1st beat',
            1 : '3rd beat',
            2 : '2nd or 4th beat',
            3 : 'off beat',
        }
        for cond in model.emission_dist.conditions():
            print _subheading("Beat category: %s (%s)" % (cond, BCMEANING.get(cond, '?')))
            print
            print "\\begin{tabular}{l l l}"
            for samp in model.emission_dist[cond].samples():
                print "D = %s & %.5f & (%s)\\\\" % (samp, 
                                              model.emission_dist[cond].prob(samp),
                                              DMEANING.get(samp, '?'))
            print "\\end{tabular}"
            print
    
    if show_ktrans:
        print
        print _heading("Key Transition Distribution")
        for cond in model.key_transition_dist.conditions():
            print _subheading("Previous mode: %s" % constants.MODE_NAMES[cond])
            print "\\begin{tabular}{l l l}"
            print "\\textbf{Key} & \\textbf{Mode} \\\\"
            samp_probs = [(model.key_transition_dist[cond].prob(samp),samp) for samp in model.key_transition_dist[cond].samples()]
            for (prob,samp) in reversed(sorted(samp_probs)):
                print "%s & %s & %.5f \\\\" % (
                            constants.RELATIVE_TONIC_NAMES.get(samp[0], '?'), 
                            constants.MODE_NAMES[samp[1]], 
                            prob)
            print "\\end{tabular}"
    
    if show_ctrans:
        print
        print _heading("Chord Transition Distribution")
        for cond in model.chord_transition_dist.conditions():
            print
            print _subheading("Previous chord: %s" % constants.CHORD_NAMES[cond])
            print
            print "\\begin{tabular}{l l}"
            samp_probs = [(model.chord_transition_dist[cond].prob(samp),samp) for samp in model.chord_transition_dist[cond].samples()]
            for (prob,samp) in reversed(sorted(samp_probs)):
                print "%s & %.5f \\\\" % (constants.CHORD_NAMES[samp], prob)
            print "\\end{tabular}"
    
    if show_chord:
        print
        print _heading("Key Change Chord Distribution")
        samp_probs = [(model.chord_dist.prob(samp),samp) for samp in model.chord_dist.samples()]
        print "\\begin{tabular}{l l}"
        for (prob,samp) in reversed(sorted(samp_probs)):
            print "%s & %.5f \\\\" % (constants.CHORD_NAMES[samp], prob)
        print "\\end{tabular}"
    
if __name__ == "__main__":
    main()
