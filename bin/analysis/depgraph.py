#!/usr/bin/env ../jazzshell
"""
Prints out the dependency tree for a parse result.

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

from jazzparser.data.parsing import ParseResults
from jazzparser.formalisms.music_halfspan.harmstruct import semantics_to_dependency_graph
from jazzparser.formalisms.music_halfspan.semantics import EnharmonicCoordinate
from jazzparser.data.dependencies import alignment_to_graph, \
                    optimal_node_alignment, dependency_graph_to_latex

def main():
    usage = "%prog [options] <results-files>"
    description = "Prints a dependency tree for a parse result"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-t", "--times", dest="times", action="store_true", help="show timings of nodes")
    parser.add_option("-l", "--latex", dest="latex", action="store_true", help="output Latex for the graphs using tikz-dependency")
    parser.add_option("--la", "--latex-align", dest="latex_align", action="store_true", help="show node alignments in Latex output")
    parser.add_option("--align-time", dest="align_time", action="store_true", help="show the graph of common dependencies when the two graphs are aligned by node times")
    parser.add_option("--align-max", dest="align_max", action="store_true", help="show the graph of common dependencies when the two graphs are aligned to maximize the dependency recovery")
    options, arguments = parser.parse_args()
        
    if len(arguments) == 0:
        print >>sys.stderr, "Specify a file to read the results from"
        sys.exit(1)
    filename = arguments[0]

    try:
        pres = ParseResults.from_file(filename)
    except ParseResults.LoadError, err:
        print >>sys.stderr, "Error loading file: %s" % (err)
        sys.exit(1)
        
    gold_graph = graph = common_graph = node_alignments = None
    transpose = (0,0)
    
    # This may be None, if a name is unavailable
    name = pres.get_name()
    
    # Try to get a gold standard result
    gold_result = pres.get_gold_semantics()
    if gold_result is None:
        # Can't print this
        print >>sys.stderr, "No gold result"
    else:
        gold_graph,gold_time_map = semantics_to_dependency_graph(gold_result)
        
        if not options.latex:
            print "Gold dependency graph:"
            print gold_graph
            
            if options.times:
                for (node,time) in sorted(gold_time_map.items(), key=lambda x:x[1]):
                    print "%d @ %s" % (node, time)
            print
    
    # Get the top result's semantics
    if len(pres.semantics) == 0:
        print >>sys.stderr, "No results"
    else:
        top_result = pres.semantics[0][1]
        graph,time_map = semantics_to_dependency_graph(top_result)
        
        if not options.latex:
            print "Top result dependency graph:"
            print graph
            
            if options.times:
                for (node,time) in sorted(time_map.items(), key=lambda x:x[1]):
                    print "%d @ %s" % (node, time)
            print
    
    if gold_graph is not None and graph is not None:
        if options.align_time:
            node_pairs = []
            # Always align the root nodes to each other
            node_pairs.append((min(gold_graph.nodes), min(graph.nodes)))
            
            # Align nodes that occur at the same time
            time_nodes1 = dict([(time,node) for (node,time) in gold_time_map.items()])
            for node2,time in sorted(time_map.items(), key=lambda x:x[1]):
                if time in time_nodes1:
                    node_pairs.append((time_nodes1[time], node2))
            node_alignments = [(gold,result,i) for i,(gold,result) in \
                                            enumerate(sorted(node_pairs))][1:]
            
            if not options.latex:
                print "Nodes aligned by time (gold -- result):"
                for i,(node1,node2) in enumerate(node_pairs):
                    print "%d: %d -- %d" % (i, node1,node2)
        
                def _label_compare(label1, label2):
                    if isinstance(label1, EnharmonicCoordinate) and \
                            isinstance(label2, EnharmonicCoordinate):
                        return label1.zero_coord == label2.zero_coord
                    else:
                        return label1 == label2
            
            # Get the graph of shared dependencies that results from aligning 
            #  simultaneous nodes
            common_graph,node_map1,node_map2 = alignment_to_graph(node_pairs, 
                    gold_graph, graph, label_compare=_label_compare)
            if not options.latex:
                print "Common dependencies:"
                print common_graph
                print "Graph size: %d" % len(common_graph)
                print
        
        
        if options.align_max:
            graphs = []
            # Try all possible transpositions and assume the best
            for transx in range(4):
                for transy in range(3):
                    def _label_compare(label1, label2):
                        if isinstance(label1, EnharmonicCoordinate) and \
                                isinstance(label2, EnharmonicCoordinate):
                            coord1 = label1.zero_coord
                            x2,y2 = label2.zero_coord
                            return coord1 == ((x2+transx)%4, (y2+transy)%3)
                        else:
                            return label1 == label2
                    
                    # Find the alignment of the nodes that matches most dependencies
                    alignment = optimal_node_alignment(gold_graph, graph, label_compare=_label_compare)
                    # Get the common dependency graph
                    common_graph, node_map1, node_map2 = alignment_to_graph(alignment, 
                                gold_graph, graph, label_compare=_label_compare)
                    
                    graphs.append((common_graph, node_map1, node_map2, alignment,transx,transy))
            
            # Score on the basis of the shared dependencies
            alignment_score,common_graph,node_map1,node_map2,alignment,transx,transy = \
                max([(len(g),g,nm1,nm2,al,tx,ty) for (g,nm1,nm2,al,tx,ty) in graphs], key=lambda x:x[0])
            transpose = (transx,transy)
                
            # Produce the list of node alignments we used
            # Reverse the mapping from the graphs to the common graph
            node_rmap1 = dict([(common,node) for (node,common) in node_map1.items()])
            node_rmap2 = dict([(common,node) for (node,common) in node_map2.items()])
            node_alignments = [
                (node_rmap1[node], node_rmap2[node], node) for \
                    node in common_graph.nodes if node != 0]
            
            if not options.latex:
                print "Optimal node alignment"
                print "Common dependencies:"
                print common_graph
                print "Graph size: %d" % len(common_graph)
                print
        
    if options.latex:
        # Exit with status 1 if we don't output anything
        exit_status = 1
        
        # Output a full Latex document in one go
        # We shouldn't have output anything so far, just got the graphs
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
%% Commands we'll need for referencing nodes in different graphs
\newcommand{\goldnode}[1]{dependency-gold-1-#1}
\newcommand{\parsenode}[1]{dependency-parse-1-#1}
\newcommand{\intnode}[1]{dependency-int-1-#1}
\centering

""" % \
        { 'title' : title,
          'maketitle' : maketitle }
        
        # Output info about what was missing
        if gold_graph is None or graph is None:
            messages = []
            if gold_graph is None:
                messages.append(r"\textit{No gold standard for this song}")
            if graph is None:
                messages.append(r"\textit{No successful parses}")
            
            print r"\fbox{\raggedright"
            print "\\\\\n".join(messages)
            print "}\\vspace{20pt}\n"
        
        if gold_graph is not None:
            exit_status = 0
            print r"\noindent Gold standard\\[10pt]"
            print dependency_graph_to_latex(gold_graph, 
                                            number_nodes=True, 
                                            fmt_lab=_fmt_label,
                                            graph_id="dependency-gold")
            print "\n\\vspace{15pt}"
        
        if graph is not None:
            exit_status = 0
            if transpose != (0,0):
                trans_txt = ", transposed by $(%d,%d)$" % transpose
            else:
                trans_txt = ""
            print r"\noindent Parse result%s\\[10pt]" % trans_txt
            print dependency_graph_to_latex(graph, 
                                            number_nodes=True, 
                                            fmt_lab=_fmt_label,
                                            graph_id="dependency-parse")
            print "\n\\vspace{15pt}"
        
        if common_graph is not None:
            exit_status = 0
            print r"\noindent Intersection\\[10pt]"
            print dependency_graph_to_latex(common_graph, 
                                            number_nodes=True, 
                                            fmt_lab=_fmt_label,
                                            graph_id="dependency-int")
        
        if common_graph is not None and options.latex_align:
            # Work out what nodes correspond to what matrix positions
            node_to_mat_gold = dict([(node,mat) for (mat,node) in \
                                        enumerate(sorted(gold_graph.nodes))][1:])
            node_to_mat_res = dict([(node,mat) for (mat,node) in \
                                        enumerate(sorted(graph.nodes))][1:])
            node_to_mat_int = dict([(node,mat) for (mat,node) in \
                                        enumerate(sorted(common_graph.nodes))][1:])
            
            # Output lines to show the alignments
            print r"""
\begin{tikzpicture}[overlay, baseline]"""

            for (gold,result,common) in node_alignments:
                # Alignment between the gold and result graphs
                print r"\draw [thick, gray, opacity=.4] (\goldnode{%d}) -- (\parsenode{%d});" \
                        % (node_to_mat_gold[gold], node_to_mat_res[result])
                # Alignment between the result and common graphs
                print r"\draw [thick, gray, opacity=.4] (\parsenode{%d}) -- (\intnode{%d});" \
                        % (node_to_mat_res[result], node_to_mat_int[common])
            
            print r"\end{tikzpicture}"
        
        # Finish off the document
        print r"""
\end{document}
"""
        sys.exit(exit_status)

def _fmt_label(label):
    if isinstance(label, EnharmonicCoordinate):
        return "(%d,%d)" % label.zero_coord
    else:
        return str(label)

if __name__ == "__main__":
    main()
