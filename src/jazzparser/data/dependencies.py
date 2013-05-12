"""Data structures for dependency graphs.

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

class DependencyGraph(object):
    """
    Data structure to represent dependency graphs. Each dependency arc is 
    represented as a pair of indices, with a label.
    
    Node index 0 has a special meaning: it is the root node.
    
    """
    def __init__(self, arcs=[], words=[]):
        self.arcs = []
        self.nodes = []
        self.words = words
        # For efficient lookup, index arcs by start and end edges
        self._arcs_by_source = {}
        self._arcs_by_target = {}
        
        # Add each arc one by one to get all the indexing right
        for (source,target,label) in arcs:
            self.add_arc(source, target, label)
    
    def __str__(self):
        if self.words:
            words = "%s\n" % " ".join(self.words)
        else:
            words = ""
        def _node(i):
            if i == 0:
                return "ROOT"
            else:
                if i-1 < len(self.words):
                    return "%d:%s" % (i, self.words[i-1])
                else:
                    return str(i)
        return "%s[%s]" % (words, "\n ".join("%s -> %s (%s)" % (_node(source),
                                                      _node(target),
                                                      label) \
                                for (source,target,label) in sorted(self.arcs)))
    
    def __len__(self):
        return len(self.arcs)
            
    def add_arc(self, source, target, label):
        if (source, target, label) not in self:
            self.arcs.append((source, target, label))
            if source not in self.nodes:
                self.nodes.append(source)
            if target not in self.nodes:
                self.nodes.append(target)
            
            self._arcs_by_source.setdefault(source, []).append((source, target, label))
            self._arcs_by_target.setdefault(target, []).append((source, target, label))
        
    def remove_arc(self, source, target, label):
        if (source, target, label) in self:
            self.arcs.remove((source, target, label))
            del self._arcs_by_source[source]
            del self._arcs_by_target[target]
    
    def arcs_from(self, source):
        return self._arcs_by_source.get(source, [])
        
    def arcs_to(self, target):
        return self._arcs_by_target.get(target, [])
    
    def arcs_spanning(self, source, target):
        return [arc for arc in self.arcs_from(source) if arc[1] == target]
    
    def root_arcs(self):
        """
        Returns all the arcs coming directly from the root node.
        
        """
        return self.arcs_from(0)
    
    def __contains__(self, arc):
        return arc in self.arcs


########################### Input/output ###################
def malt_tab_to_dependency_graphs(data):
    """
    Reads in data in the Malt-TAB format, as used by the Malt Parser, 
    and returns a list of dependency graphs.
    
    A error will be raised if the input is in two-column format, because 
    you can't build a dependency graph from that.
    
    @type data: string
    @param data: file content
    
    @see: http://w3.msi.vxu.se/~nivre/research/MaltXML.html
    
    """
    lines = data.splitlines()
    graph_arcs = []
    
    current_arcs = []
    for line in lines:
        if len(line.strip()) == 0:
            # Empty line: start a new graph
            if len(current_arcs):
                graph_arcs.append(current_arcs)
                current_arcs = []
            continue
        
        # Interpret the line by splitting on tabs
        parts = line.split("\t")
        # The line may have two parts (form and pos tag) or four
        if len(parts) == 2:
            raise MaltTabReadError, "can't construct a dependency graph "\
                "out of a two-column malt-tab file"
        elif len(parts) != 4:
            raise MaltTabReadError, "each line may have 2 or 4 columns, "\
                "found %d in \"%s\"" % (len(parts), line)
        else:
            word = parts[0]
            pos = parts[1]
            if parts[2]:
                head = int(parts[2])
            else:
                head = None
            label = parts[3]
            current_arcs.append((word,pos,head,label))
    
    # Finish the last graph
    if len(current_arcs):
        graph_arcs.append(current_arcs)
    
    # Read all the lines successfully
    # Produce a representation of each graph
    graphs = []
    for arcset in graph_arcs:
        words = [arc[0] for arc in arcset]
        arcs = [(i+1,arc[2],arc[3]) for (i,arc) in enumerate(arcset)]
        graphs.append(DependencyGraph(arcs, words))
    
    return graphs

class MaltTabReadError(Exception):
    pass

def dependency_graph_to_latex(graph, words=[], number_nodes=False, 
        fmt_lab=str, graph_id=None, extra_rows=[]):
    """
    Output a latex representation of the dependency graph to typeset it 
    using tikz-dependency.
    
    """
    if number_nodes:
        words = [str(i) for i in range(len(graph.nodes)-1)]
    else:
        if len(words):
            words = list(words)
        else:
            words = graph.words
        if len(words) < len(graph.nodes)+1:
            words.extend([""]*(len(graph.nodes)-len(words)-1))
    if len(extra_rows):
        # Add blanks to the extra rows as well
        extra_rows = [
            row + [""]*(len(graph.nodes)-len(row)-1) for row in extra_rows]
    
    nmap = dict([(old,new) for (new,old) in enumerate(sorted(graph.nodes))])
    
    deptext = " \\& ".join(words) + "\\\\\n"
    if len(extra_rows):
        deptext += "\\\\\n".join("\\& ".join(row) for row in extra_rows)
    
    edges = "\n".join([
        "    \\deproot{%d}{%s}" % (nmap[start],fmt_lab(label)) if end == 0 else \
        "    \\depedge{%d}{%d}{%s}" % (nmap[end],nmap[start],fmt_lab(label)) for (start,end,label) \
            in sorted(graph.arcs)])
    
    options = []
    if graph_id is not None:
        # Set a custom id for the graph, so we can refer to it elsewhere
        options.append(", dep id=%s" % graph_id)
    
    string = """\
\\begin{dependency}[theme = simple%(opts)s]
  \\begin{deptext}[column sep=0.6em]
    %(words)s \\\\
  \\end{deptext}
%(edges)s
\\end{dependency}""" % {
        'words' : deptext,
        'edges' : edges,
        'opts' : "".join(options) }
    return string


########################### Alignment-related utilities ##################

def optimal_node_alignment(graph1, graph2, label_compare=(lambda x,y:x==y)):
    """
    Produces the alignment between the nodes of the two dependency graphs that 
    maximizes the shared dependencies.
    
    Returns a list of aligned pairs of node indices, using C{None} to 
    represent deletions/insertions.
    
    """
    N = len(graph1.nodes)
    M = len(graph2.nodes)
    indices1 = list(enumerate(sorted(graph1.nodes)))
    indices2 = list(enumerate(sorted(graph2.nodes)))
    root1 = min(graph1.nodes)
    root2 = min(graph2.nodes)
    
    # Initialize a score matrix
    S = []
    P = []
    for x in range(N):
        row = []
        prow = []
        for y in range(M):
            row.append([])
            prow.append([])
        S.append(row)
        P.append(prow)
    
    # Utility functions
    def _append(lst, val):
        if val not in lst:
            lst.append(val)
    def addS(x, y, val, pointer):
        # If a value (same score, same dependencies) is already there, don't 
        #  add it again
        if val not in S[x][y]:
            S[x][y].append(val)
            # Also add a pointer so we can trace the alignment back
            P[x][y].append(pointer)
    def removeS(x, y, index):
        # Remove the value from S and pointers P
        del S[x][y][index]
        del P[x][y][index]
    
    # First nodes should always be aligned: these are the root nodes
    # Find dependencies to or from root
    root_deps = []
    for (source1,target1,label1) in graph1.arcs_from(root1):
        for (source2,target2,label2) in graph2.arcs_from(root2):
            if label_compare(label1, label2):
                # If we align the nodes at the other end of this 
                #  arc, we match a dependency
                _append(root_deps, (target1,target2))
    for (source1,target1,label1) in graph1.arcs_to(root1):
        for (source2,target2,label2) in graph2.arcs_to(root2):
            if label_compare(label1, label2):
                # If we align the nodes at the other end of this 
                #  arc, we match a dependency
                _append(root_deps, (source1,source2))
    # We don't propogate these potential alignments through the table, since 
    #  they're the same everywhere
    
    # Initialize (0,0) to empty
    # This will get propogated along the first row and column
    addS(0, 0, (0, []), ('UL',0))
    
    for x,node1 in indices1:
        for y,node2 in indices2:
            if x > 0:
                # Insertion in graph1
                for i,(score,deps) in enumerate(S[x-1][y]):
                    # Remove dependencies that can't possibly be match now
                    deps = [(goal1, goal2) for (goal1, goal2) in deps if \
                                goal1 != node1]
                    # Don't add anything to the score for this
                    addS(x, y, (score,deps), ('U',i))
            
            if y > 0:
                # Insertion in graph2
                for i,(score,deps) in enumerate(S[x][y-1]):
                    # Remove dependencies that can't possibly be match now
                    deps = [(goal1, goal2) for (goal1, goal2) in deps if \
                                goal2 != node2]
                    # Don't add anything to the score for this
                    addS(x, y, (score,deps), ('L',i))
            
            if x > 0 and y > 0:
                # Alignment
                for i,(score,deps) in enumerate(S[x-1][y-1]):
                    # Count how many dependencies were satisfied by this alignment
                    matched = 0
                    new_deps = []
                    for (goal1, goal2) in deps:
                        if goal1 == node1 and goal2 == node2:
                            # A required match to match a dependency arc
                            matched += 1
                        elif goal1 > node1 and goal2 > node2:
                            # Keep looking for this
                            new_deps.append((goal1, goal2))
                    # Check if we've matched any root arcs by this alignment
                    matched += root_deps.count((node1,node2))
                            
                    # Find dependencies that might later be matched thanks to 
                    #  this alignment
                    for (source1,target1,label1) in graph1.arcs_from(node1):
                        for (source2,target2,label2) in graph2.arcs_from(node2):
                            if label_compare(label1, label2) and target1 > node1 and target2 > node2:
                                # If we align the nodes at the other end of this 
                                #  arc, we match a dependency
                                new_deps.append((target1,target2))
                                
                    # Do the same for dependencies pointing backwards to here
                    for (source1,target1,label1) in graph1.arcs_to(node1):
                        for (source2,target2,label2) in graph2.arcs_to(node2):
                            if label_compare(label1, label2) and source1 > node1 and source2 > node2:
                                # If we align the nodes at the other end of this 
                                #  arc, we match a dependency
                                new_deps.append((source1,source2))
                    
                    addS(x, y, (score+matched, new_deps), ('UL',i))
            
            # Remove from S[x][y] any (score,deps) where the maximum 
            #  possible score, score+len(deps), <= some other option's 
            #  minimum score
            # Find the option with the highest minimum score
            max_min_score,top_scorer = max((score,i) for i,(score,deps) in enumerate(S[x][y]))
            # Get indices to remove
            # Make sure not to remove the one that had the max min score
            remove = [i for i,(score,deps) in enumerate(S[x][y]) if \
                                            score+len(deps) <= max_min_score \
                                            and i != top_scorer]
            shifter = 0
            for i in remove:
                removeS(x, y, i-shifter)
                shifter += 1
    
    # Trace back through the pointers to find operations that make the alignment
    index,(score,deps) = max(enumerate(S[-1][-1]), key=lambda x:x[1][0])
    x = N-1
    y = M-1
    ops = []
    while not (x == 0 and y == 0):
        direction,index = P[x][y][index]
        if direction == 'U':
            x -= 1
            ops.append('I1')
        elif direction == 'L':
            y -= 1
            ops.append('I2')
        else:
            y -= 1
            x -= 1
            ops.append('A')
    # Always align the root nodes with each other
    ops.append('A')
    ops.reverse()
    
    # Pair up the node indices according to these operations
    nodes1it = iter(sorted(graph1.nodes))
    nodes2it = iter(sorted(graph2.nodes))
    pairs = []
    for op in ops:
        if op == "A":
            # Take one from both graphs
            pairs.append((nodes1it.next(), nodes2it.next()))
        elif op == "I1":
            # Insertion in graph1
            pairs.append((nodes1it.next(), None))
        else:
            # Insertion in graph2
            pairs.append((None, nodes2it.next()))
    
    return pairs

def alignment_to_graph(node_pairs, graph1, graph2, label_compare=(lambda x,y:x==y)):
    """
    Given a list of pairs of aligned nodes, as returned by 
    L{optimal_node_alignment}, produces the dependency graph that contains 
    only the shared dependencies. The node indices do not, of course, 
    correspond to those in the input graphs, so we also return a mapping 
    from the node indices in the common graph to those in each of the 
    other graphs.
    
    """
    arcs = []
    # Filter out pairs that don't align the two graphs
    node_pairs = [(n1,n2) for (n1,n2) in node_pairs if n1 is not None and n2 is not None]
    g1_to_g2 = dict(node_pairs)
    new_nodes = dict([(node1,i) for i,(node1,node2) in enumerate(node_pairs)])
    new_nodes2 = dict([(node2,i) for i,(node1,node2) in enumerate(node_pairs)])
    
    for source1,target1,label1 in graph1.arcs:
        # Check whether the other graph has a corresponding arc
        if source1 in g1_to_g2:
            source2 = g1_to_g2[source1]
        else:
            continue
        
        if target1 in g1_to_g2:
            target2 = g1_to_g2[target1]
        else:
            continue
        
        matching = graph2.arcs_spanning(source2, target2)
        for (__,__,label2) in matching:
            if label_compare(label1, label2):
                # This arc matches between the two
                # Add an arc to the common graph
                arcs.append((new_nodes[source1], new_nodes[target1], label1))
    
    return DependencyGraph(arcs), new_nodes, new_nodes2
