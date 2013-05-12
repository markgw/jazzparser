#!/usr/bin/env ../jazzshell
"""
Prints out the dependency tree for a gold standard annotation.

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

from jazzparser.grammar import get_grammar
from jazzparser.data.input import DbInput, command_line_input
from jazzparser.evaluation.parsing import parse_sequence_with_annotations
from jazzparser.formalisms.music_halfspan.harmstruct import semantics_to_dependency_graph
from jazzparser.formalisms.music_halfspan.semantics import EnharmonicCoordinate
from jazzparser.data.dependencies import dependency_graph_to_latex
from jazzparser.utils.latex import filter_latex

def main():
    usage = "%prog [options] <results-files> <index>"
    description = "Prints a dependency tree for a parse result"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-l", "--latex", dest="latex", action="store_true", help="output Latex for the graphs using tikz-dependency")
    parser.add_option("--file-options", "--fopt", dest="file_options", action="store", help="options for the input file (--file). Type '--fopt help' for a list of available options.")
    options, arguments = parser.parse_args()
        
    if len(arguments) < 1:
        print >>sys.stderr, "Specify a file to read the results from"
        sys.exit(1)
    filename = arguments[0]
    if len(arguments) < 2:
        print >>sys.stderr, "Specify an of the sequence to load"
        sys.exit(1)
    index = int(arguments[1])
    
    grammar = get_grammar()
    
    # We always need an index, so this is given as an argument
    # Put it in the options list for loading the file
    fopts = options.file_options
    if fopts and len(fopts):
        fopts += ":index=%d" % index
    else:
        fopts = "index=%d" % index
    # Load the sequence index file
    dbinput = command_line_input(filename=filename, filetype="db", options=fopts)
    
    name = dbinput.name
    
    anal = parse_sequence_with_annotations(dbinput, grammar)[0]
    graph, time_map = semantics_to_dependency_graph(anal.semantics)
    
    # Join together chords that are on the same dependency node
    times = iter(sorted(time_map.values()))
    dep_time = times.next()
    current_chord = []
    joined_chords = []
    finished = False
    for chord_time,chord in sorted(dbinput.sequence.time_map.items()):
        if chord_time >= dep_time and not finished:
            if len(current_chord):
                joined_chords.append(current_chord)
            current_chord = [chord]
            try:
                dep_time = times.next()
            except StopIteration:
                finished = True
        else:
            current_chord.append(chord)
    joined_chords.append(current_chord)
    
    chords = [" ".join(filter_latex(str(crd)) for crd in item) 
                                                for item in joined_chords]
    annotations = [" ".join(filter_latex(crd.category) for crd in item) 
                                                for item in joined_chords]
    graph.words = annotations
    
    if options.latex:
        # Exit with status 1 if we don't output anything
        exit_status = 1
        
        # Output a full Latex document in one go
        if name is not None:
            title = r"""\title{%s}
\author{}
\date{}""" % name.capitalize()
            maketitle = r"\maketitle\thispagestyle{empty}\vspace{-20pt}"
        else:
            title = ""
            maketitle = ""
        
        # Print the header
        print r"""\documentclass[a4paper]{article}
\usepackage{tikz-dependency}
%% You may need to set paperheight (for width) and paperwidth (for height) to get things to fit
\usepackage[landscape,margin=1cm,paperheight=50cm]{geometry}
\pagestyle{empty}

%(title)s

\begin{document}
%(maketitle)s

\tikzstyle{every picture}+=[remember picture]
\centering

""" % \
        { 'title' : title,
          'maketitle' : maketitle }
        
        if graph is not None:
            exit_status = 0
            print dependency_graph_to_latex(graph, 
                                            fmt_lab=_fmt_label,
                                            extra_rows=[chords])
            print "\n\\vspace{15pt}"
        
        # Finish off the document
        print r"""
\end{document}
"""
        sys.exit(exit_status)
    else:
        # Not outputing Latex
        print graph
    

def _fmt_label(label):
    if isinstance(label, EnharmonicCoordinate):
        return "(%d,%d)" % label.zero_coord
    else:
        return str(label)

if __name__ == "__main__":
    main()
