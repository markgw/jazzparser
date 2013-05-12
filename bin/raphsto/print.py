#!/usr/bin/env ../jazzshell
"""
Outputs information about a trained model.

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
    description = "Outputs information about a trained Raphsto model"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-m', '--model-type', dest="model_type", action="store", help="select a model type: one of %s (default: standard)" % ", ".join(mt for mt in MODEL_TYPES.keys()), default="standard")
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
    
    print "Raphael & Stoddard trained model, %s: %s" % (options.model_type, model_name)
    print "as on %s" % datetime.now().strftime("%a %d %b %Y")
    
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
    
    if show_em:
        print
        print "Emission distribution"
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
            print " Beat category: %s (%s)" % (cond, BCMEANING.get(cond, '?'))
            for samp in model.emission_dist[cond].samples():
                print "   %s(%s)" % (("D = %s: %.5f" % (samp, 
                                                                  model.emission_dist[cond].prob(samp))
                                                                ).ljust(15),
                                               DMEANING.get(samp, '?'))
    
    if show_ktrans:
        print "\n\nTransition distributions"
        print "Key transition distribution"
        for cond in model.key_transition_dist.conditions():
            print " Previous mode: %s" % constants.MODE_NAMES[cond]
            samp_probs = [(model.key_transition_dist[cond].prob(samp),samp) for samp in model.key_transition_dist[cond].samples()]
            for (prob,samp) in reversed(sorted(samp_probs)):
                print "%smode = %s: %.5f" % (("   key = %s (%s)," % (constants.RELATIVE_TONIC_NAMES.get(samp[0], '?'), 
                                                                samp[0])).ljust(20), 
                                         constants.MODE_NAMES[samp[1]], prob)
    
    if show_ctrans:
        print "\nChord transition distribution"
        for cond in model.chord_transition_dist.conditions():
            print " Previous chord: %s" % constants.CHORD_NAMES[cond]
            samp_probs = [(model.chord_transition_dist[cond].prob(samp),samp) for samp in model.chord_transition_dist[cond].samples()]
            for (prob,samp) in reversed(sorted(samp_probs)):
                print "   %s%.5f" % (("%s:" % constants.CHORD_NAMES[samp]).ljust(5), 
                                     prob)
    
    if show_chord:
        print "\nKey change chord dist"
        samp_probs = [(model.chord_dist.prob(samp),samp) for samp in model.chord_dist.samples()]
        for (prob,samp) in reversed(sorted(samp_probs)):
            print " %s%.5f" % (("%s:" % constants.CHORD_NAMES[samp]).ljust(5), 
                               prob)
    
    print "\n======================="
    print "Model training history:"
    print model.history
    print "\n============="
    print "Description:"
    print model.description
    
if __name__ == "__main__":
    main()
