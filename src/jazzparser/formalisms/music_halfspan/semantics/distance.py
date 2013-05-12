"""Semantic distance metrics.

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
from jazzparser.formalisms.base.semantics.distance import DistanceMetric, \
                            FScoreMetric
from jazzparser.formalisms.music_halfspan.evaluation import tonal_space_f_score, \
                            tonal_space_alignment_score, tonal_space_align, \
                            arrange_alignment, tonal_space_distance, \
                            tonal_space_length

class TonalSpaceEditDistance(FScoreMetric):
    """
    Original tonal space distance metric computed as the edit distance of 
    the step vectors and functions of the path through the tonal space 
    implied by the semantics.
    
    """
    OPTIONS = [
        ModuleOption('output', filter=choose_from_list(
                        ['f','precision','recall','inversef','dist']),
                     usage="output=O, where O is one of 'f', 'precision', "\
                        "'recall', 'inversef', 'dist'",
                     default='dist',
                     help_text="Select what metric to output. Choose recall "\
                        "or precision for asymmetric metrics. F-score ('f') "\
                        "combines these two. This is inverted ('inversef') "\
                        "to get a distance, rather than similarity. "\
                        "Alternatively, use the edit distance of the alignment "\
                        "('dist', default)"),
    ]
    name = "tsed"
    
    def fscore_match(self, sem1, sem2):
        if sem1 is None or sem2 is None:
            alignment_score = 0.0
        else:
            alignment_score = tonal_space_alignment_score(sem1.lf, sem2.lf)
            
        if sem1 is None:
            len1 = 0.0
        else:
            len1 = tonal_space_length(sem1)
        if sem2 is None:
            len2 = 0.0
        else:
            len2 = tonal_space_length(sem2)
        return alignment_score,len1,len2
    
    def _get_identifier(self):
        ident = {
            'f' : 'f-score',
            'precision' : 'precision',
            'recall' : 'recall',
            'inversef' : 'inverse f-score',
            'dist' : 'edit distance',
        }
        return "tsed %s" % ident[self.options['output']]
    identifier = property(_get_identifier)
    
    def distance(self, sem1, sem2):
        # Handle the extra 'dist' case
        if self.options['output'] == 'dist':
            # If one input is empty, we consider all points to have been deleted
            if sem1 is None:
                return tonal_space_length(sem2)
            elif sem2 is None:
                return tonal_space_length(sem1)
            
            # Compute the score using our standard TS distance computation
            # This is based on the alignment score of the optimal alignment 
            #  of the two sequences
            return tonal_space_distance(sem1.lf, sem2.lf)
        else:
            # Otherwise the superclass takes care of everything
            return super(TonalSpaceEditDistance, self).distance(sem1, sem2)
    
    def print_computation(self, sem1, sem2):
        """
        Shows the optimal alignment of the paths that the score comes from.
        
        @see: jazzparser.formalisms.music_halfspan.semantics.distance.DistanceMetric.print_computation
        
        """
        pairs = tonal_space_align(sem1.lf, sem2.lf)
        return "\n".join(["%s %s" % pair for pair in pairs])
    
    def total_distance(self, input_pairs):
        """ Handle the 'dist' output specially (just sum up distances). """
        if self.options['output'] == 'dist':
            # Do the normal (non-f-score) metric thing of summing up all vals
            return DistanceMetric.total_distance(self, input_pairs)
        else:
            return FScoreMetric.total_distance(self, input_pairs)
    
    def format_distance(self, dist):
        if self.options['output'] == 'dist':
            return "%f" % dist
        else:
            return FScoreMetric.format_distance(self, dist)


def _cadence_type(tree):
    # The grammar currently ensures that only one cadence type is used 
    #  throughout a specific cadence. If this changes, we'll want to 
    #  redefine this metric
    if len(tree.root) == 0:
        # Root is a leaf: no cadence
        return "NA"
    else:
        # Pick the first label we come across
        label = tree.root[0].label
        if label == "leftonto":
            return "perfect"
        elif label == "rightonto":
            return "plagal"
        else:
            raise ValueError, "unknown cadence type with node label "\
                "'%s' in the dependency graph" % label
                
class LargestCommonEmbeddedSubtrees(FScoreMetric):
    """
    Tonal space distance metric computed as the size of the largest subtree 
    that can be embedded in the dependency graphs of two logical forms. This 
    is done separately for each alignment of cadences in the two logical 
    forms and the global optimum is used.
    
    """
    OPTIONS = FScoreMetric.OPTIONS + [
        ModuleOption('res_score', filter=int,
                     usage="res_score=R, where R is an integer",
                     default=2,
                     help_text="Score to give to matching resolutions. 1 "\
                        "is the score given to a matching node in the "\
                        "dependency tree. The default (2) gives more "\
                        "weight to matching resolutions that tree nodes. "\
                        "Special value -1 assigns a weight equal to the size "\
                        "of the common dependency tree + 1"),
    ]
    name = "lces"
    
    def _get_identifier(self):
        ident = {
            'f' : 'f-score',
            'precision' : 'precision',
            'recall' : 'recall',
            'inversef' : 'inverse f-score',
        }
        return "dependency tree %s" % ident[self.options['output']]
    identifier = property(_get_identifier)
    
    def fscore_match(self, sem1, sem2):
        """
        The core computation of the distance metric. Takes care of the tree 
        comparison and cadence alignment and return the vital statistics.
        
        """
        from jazzparser.formalisms.music_halfspan.harmstruct import \
                                                semantics_to_dependency_trees
        from jazzparser.misc.tree.lces import lces_size
        from jazzparser.utils.distance import align
        
        res_score = self.options['res_score']
        
        # Get dependency graphs for the two logical forms
        if sem1 is None:
            trees1 = []
        else:
            trees1 = semantics_to_dependency_trees(sem1)
        if sem2 is None:
            trees2 = []
        else:
            trees2 = semantics_to_dependency_trees(sem2)
            
        if sem1 is None or sem2 is None:
            # Empty input: give zero score to everything
            alignment_score = 0.0
            alignment = []
            transpose = None
        else:
            # Try each possible transposition of the second tree to make this 
            #  metric key independent
            distances = []
            for x_trans in range(4):
                for y_trans in range(3):
                    def _align(tree1, tree2):
                        # Transpose the label in the second tree
                        label2 = ((tree2.root.label[0] + x_trans) % 4,
                                  (tree2.root.label[1] + y_trans) % 3)
                        # Check the root to find out whether they have the same resolution
                        same_res = tree1.root.label == label2
                        # Find out what cadence type each is
                        same_cad = _cadence_type(tree1) == _cadence_type(tree2)
                        if same_cad:
                            # Compare the structure of the cadences
                            tree_similarity = lces_size(tree1, tree2)
                        else:
                            tree_similarity = 0
                        
                        # Work out how much score to give a matching resolution
                        if res_score == -1:
                            res_match = tree_similarity + 1
                        else:
                            res_match = res_score
                        return - tree_similarity - (res_match if same_res else 0)
                    
                    aligned,dist = align(trees1, trees2, delins_cost=0, 
                                                        subst_cost=_align,
                                                        dist=True)
                    distances.append((dist,aligned,(x_trans,y_trans)))
            
            alignment_score,alignment,transpose = min(distances, 
                                                            key=lambda x:x[0])
            alignment_score = -float(alignment_score)
        
        def _max_score(trees):
            """
            Get the maximum possible score that could be assigned to a match 
            with this tree set.
            
            """
            score = 0
            for tree in trees:
                # Do the same things as _align (below), but max possible score
                # Maximum similarity is just the size of the tree
                tree_sim = len(tree)
                if res_score == -1:
                    res_match = tree_sim + 1
                else:
                    res_match = res_score
                # Assume the same resolution and cadence type
                score += tree_sim + res_match
            return score
        max_score1 = _max_score(trees1)
        max_score2 = _max_score(trees2)
        
        return alignment_score, max_score1, max_score2, alignment, transpose
        
    def print_computation(self, sem1, sem2):
        from jazzparser.misc.tree.lces import lces
        from cStringIO import StringIO
        
        stats = self.fscore_match(sem1, sem2)
        trans = stats[4]
        buf = StringIO()
        
        print >>buf, "LF1: %s" % sem1
        print >>buf, "LF2: %s" % sem2
        print >>buf, "LF2 transposed by (%d,%d)\n" % trans
        print >>buf, "Maximal cadence alignment:"
        # Go through all the aligned cadences and show the components of the 
        #  scores
        for sem1cad, sem2cad in stats[3]:
            if sem1cad is None:
                print >>buf, "1: deleted"
            else:
                print >>buf, "1: %s" % sem1cad
            if sem2cad is None:
                print >>buf, "2: deleted"
            else:
                print >>buf, "2: %s" % sem2cad
            if sem1cad is not None and sem2cad is not None:
                # Cadences were aligned: explain how
                print >>buf, "Cadence types: %s %s" % (_cadence_type(sem1cad), 
                                                _cadence_type(sem2cad))
                root2 = sem2cad.root.label
                root2 = ((root2[0]+trans[0])%4, (root2[1]+trans[1])%3)
                print >>buf, "Resolutions: %s %s" % (sem1cad.root.label, root2)
                common = lces(sem1cad, sem2cad)
                print >>buf, "Shared structure: %s (size %d)" % (common, len(common)-1)
            print >>buf
        return buf.getvalue()

class OptimizedDependencyRecovery(FScoreMetric):
    """
    Aligns the two dependency graphs in the way that optimizes their 
    dependency recovery and reports that dependency recovery. This gives 
    a metric that can be used when the alignment between the graphs is not 
    known, such as when parsing MIDI.
    
    """
    name = "optdeprec"
    
    def _get_identifier(self):
        ident = {
            'f' : 'f-score',
            'precision' : 'precision',
            'recall' : 'recall',
            'inversef' : 'inverse f-score',
        }
        return "dependency alignment %s" % ident[self.options['output']]
    identifier = property(_get_identifier)
    
    def fscore_match(self, sem1, sem2):
        from jazzparser.formalisms.music_halfspan.harmstruct import \
                                                semantics_to_dependency_graph
        from jazzparser.data.dependencies import optimal_node_alignment, \
                                alignment_to_graph
        from jazzparser.formalisms.music_halfspan.semantics import \
                                EnharmonicCoordinate
        
        if sem1 is None:
            max_score1 = 0.0
        else:
            graph1,timings1 = semantics_to_dependency_graph(sem1)
            max_score1 = float(len(graph1))
        
        if sem2 is None:
            max_score2 = 0.0
        else:
            graph2,timings2 = semantics_to_dependency_graph(sem2)
            max_score2 = float(len(graph2))
        
        if sem1 is None or sem2 is None:
            # Empty input: give zero score to everything
            alignment_score = 0.0
            alignment = []
            transpose = None
        else:
            graph1,timings1 = semantics_to_dependency_graph(sem1)
            graph2,timings2 = semantics_to_dependency_graph(sem2)
            
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
                    alignment = optimal_node_alignment(graph1, graph2, label_compare=_label_compare)
                    # Get the common dependency graph
                    graph, node_map1, node_map2 = alignment_to_graph(alignment, 
                                graph1, graph2, label_compare=_label_compare)
                    
                    graphs.append(graph)
            
            # Score on the basis of the shared dependencies
            alignment_score,graph = max([(len(graph),graph) for graph in graphs], key=lambda x:x[0])
        
        return alignment_score,max_score1,max_score2

class DependencyRecovery(FScoreMetric):
    """
    Exact dependency recovery metric. Only matches two nodes to each other 
    if they have the same time attached to them. This is for use with results 
    where we know the input is the same as that over which the gold standard 
    is defined.
    
    For example, evaluating chord sequence parsing against the 
    corpus we know this. It won't work, however, evaluating midi parsing 
    against the chord corpus.
    
    It is also not pitch-independent, since it's only useful where the input 
    over which the result was produced is the same anyway.
    
    """
    name = "deprec"
    
    def _get_identifier(self):
        ident = {
            'f' : 'f-score',
            'precision' : 'precision',
            'recall' : 'recall',
            'inversef' : 'inverse f-score',
        }
        return "dependency recovery %s" % ident[self.options['output']]
    identifier = property(_get_identifier)
    
    def fscore_match(self, sem1, sem2):
        from jazzparser.formalisms.music_halfspan.harmstruct import \
                                                semantics_to_dependency_graph
        from jazzparser.data.dependencies import optimal_node_alignment, \
                                alignment_to_graph
        from jazzparser.formalisms.music_halfspan.semantics import \
                                EnharmonicCoordinate
        
        if sem1 is None:
            max_score1 = 0.0
        else:
            graph1,timings1 = semantics_to_dependency_graph(sem1)
            max_score1 = float(len(graph1))
        
        if sem2 is None:
            max_score2 = 0.0
        else:
            graph2,timings2 = semantics_to_dependency_graph(sem2)
            max_score2 = float(len(graph2))
        
        if sem1 is None or sem2 is None:
            # Empty input: give zero score to everything
            alignment_score = 0.0
            alignment = []
            transpose = None
        else:
            graph1,timings1 = semantics_to_dependency_graph(sem1)
            graph2,timings2 = semantics_to_dependency_graph(sem2)
            
            node_pairs = []
            # Always align the root nodes to each other
            node_pairs.append((min(graph1.nodes), min(graph2.nodes)))
            
            # Align nodes that occur at the same time
            time_nodes1 = dict([(time,node) for (node,time) in timings1.items()])
            for node2,time in sorted(timings2.items(), key=lambda x:x[1]):
                if time in time_nodes1:
                    node_pairs.append((time_nodes1[time], node2))
    
            def _label_compare(label1, label2):
                if isinstance(label1, EnharmonicCoordinate) and \
                        isinstance(label2, EnharmonicCoordinate):
                    return label1.zero_coord == label2.zero_coord
                else:
                    return label1 == label2
            # Get the graph of shared dependencies that results from aligning 
            #  simultaneous nodes
            graph,node_map1,node_map2 = alignment_to_graph(node_pairs, 
                    graph1, graph2, label_compare=_label_compare)
            
            # Score on the basis of the shared dependencies
            alignment_score = len(graph)
        
        return alignment_score,max_score1,max_score2
    
class RandomDistance(DistanceMetric):
    """
    Returns a distance by picking a random number. This is useful for 
    establishing a random baseline on evaluations.
    Obviously it won't be the same for two calls on the same inputs.
    
    """
    OPTIONS = []
    name = "rand"
    
    def distance(self, sem1, sem2):
        import random
        return random.random()

class DependencyGraphSize(DistanceMetric):
    """
    This is a baseline metric that does nothing clever. It's designed to 
    show how well a system could do just by comparing the lengths of the 
    two analyses in terms of the number of dependencies in them. 
    We'd hope it wouldn't do very well, but it's an important 
    baseline to try.
    
    The distance is the inverse ratio between the lengths, always between 0 
    and 1.
    
    """
    OPTIONS = []
    name = "depsize"
    
    def distance(self, sem1, sem2):
        from jazzparser.formalisms.music_halfspan.harmstruct import \
                                                semantics_to_dependency_trees
        # Get dependency graphs for the two logical forms
        trees1 = semantics_to_dependency_trees(sem1)
        trees2 = semantics_to_dependency_trees(sem2)
        # Count the number of dependencies in each graph
        len1 = sum([len(tree) for tree in trees1])
        len2 = sum([len(tree) for tree in trees2])
        
        # Take the ratio between the sizes
        if len1 > len2:
            return 1.0 - (float(len2) / len1)
        else:
            return 1.0 - (float(len1) / len2)
