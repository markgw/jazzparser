"""Interactive shell tools for the Halfspan formalism.

These tools concern song recognition and allow utilities for recognising 
songs to be called from the shell.

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

from jazzparser.shell.tools import Tool
from jazzparser.shell import ShellError
from jazzparser.utils.options import ModuleOption, options_help_text
from jazzparser.utils.strings import str_to_bool

class LoadCorpusTool(Tool):
    """
    Tool to load a corpus of tonal space analyses of songs. These may then 
    be used for song recognition. This must be called before other song 
    recognition tools will work.
    
    A corpus may be created from the chord corpus using the bin/data/parsegs.py 
    to parse the chord corpus and store the analyses in a file.
    
    """
    
    name = "Load analysis set"
    commands = ['loadsongs']
    usage = ('loadsongs <name>', "load the named tonal space analysis corpus")
    help = """\
Loads a tonal space analysis corpus by name. This corpus may then be used by 
other tools which require a song corpus.

These corpora are built using the script bin/data/parsegs.py.
"""
    
    def run(self, args, state):
        from jazzparser.data.tonalspace import TonalSpaceAnalysisSet
        if len(args) != 1:
            raise ShellError, "Please give the name of a tonal space analysis "\
                "set. Available sets are: %s" % \
                    ", ".join(TonalSpaceAnalysisSet.list())
        
        try:
            # Try loading the named set
            songset = TonalSpaceAnalysisSet.load(args[0])
        except Exception, err:
            raise ShellError, "Error loading tonal space analysis set: %s" % \
                err
        print "Loaded tonal space analysis set '%s'" % args[0]
        # Store this in the state so other tools can use it
        state.data['songset'] = songset

class ListSongsTool(Tool):
    name = "List songs"
    commands = ['songs']
    usage = ('songs', "list songs in loaded songset")
    help = """\
List all the song names in the loaded tonal space analysis songset.
"""
    
    def run(self, args, state):
        # Try getting song data
        songset = state.get_data("songset", 
                        help_msg="Use command 'loadsongs' to load a songset")
        print "\n".join(["%d. %s" % (num,name) for (num,name) in \
                                                    enumerate(songset.songs)])

class PrintAnalysisTool(Tool):
    name = "Print analysis"
    commands = ['songanal']
    usage = ('songanal <songnum>', "display the tonal space analysis for song "\
        "number <songnum> in the loaded songset")
    help = """\
Prints the tonal space path that is the analysis of a song from a loaded 
songset.
"""

    def run(self, args, state):
        from jazzparser.formalisms.music_halfspan.semantics import semantics_to_coordinates
        
        if len(args) == 0:
            raise ShellError, "Give a song number"
        # Get the song from the dataset
        song = get_song(int(args[0]), state)
        print "Analysis of '%s'" % song[0]
        print "\nSemantics"
        # Display the semantics
        print song[1]
        print "\nTonal space path"
        # Also display the TS coordinates
        print semantics_to_coordinates(song[1])

class ResultSongTSEditDistanceTool(Tool):
    name = "Compare result"
    commands = ['songcomparets', 'songcompts']
    usage = ('songcomparets <result-num> <song-num>', "compare a parse result "\
        "to a song in the database using the tonal space edit distance metric")
    help = """\
Compares a parse result to a specific song in the database  using the tonal 
space edit distance metric and outputs the alignment distance.

See also:
    songcomparedep: to compare a result to a song in terms of dependency 
        recovery.
"""
    tool_options = Tool.tool_options + [
        ModuleOption('local', filter=str_to_bool,
                     usage="local=B, where B is true or false",
                     default=False,
                     help_text="Use local alignment to score the similarity "\
                        "of the tonal space paths instead of global"),
        ModuleOption('song', filter=str_to_bool,
                     usage="tosong=B, where B is true or false",
                     default=False,
                     help_text="Compare the numbered song in the corpus to the "\
                        "second song, instead of comparing the numbered result "\
                        "to the song"),
        ModuleOption('alignment', filter=str_to_bool,
                     usage="alignment=B, where B is true or false",
                     default=False,
                     help_text="Output the full alignment, with the two step "\
                        "lists above one another"),
    ]
    
    def run(self, args, state):
        from jazzparser.formalisms.music_halfspan.evaluation import \
                            tonal_space_local_alignment, tonal_space_alignment, \
                            arrange_alignment
        
        if len(args) < 2:
            raise ShellError, "Give a result number and a song number"
        
        resnum = int(args[0])
        songnum = int(args[1])
        
        song = get_song(songnum, state)
        songsem = song[1]
        
        if self.options['song']:
            # Compare a song instead of a result
            compsong = get_song(resnum, state)
            resultsem = compsong[1]
            print "Comparing '%s' to '%s'" % (compsong[0], song[0])
        else:
            # Normal behaviour: compare a result to a song
            if resnum >= len(state.results):
                raise ShellError, "No result number %d" % resnum
            result = state.results[resnum]
            resultsem = result.semantics
            print "Comparing result %d to '%s'" % (resnum, song[0])
        
        # Do the comparison
        if self.options['local']:
            ops, song_steps, result_steps, distance = \
                    tonal_space_local_alignment(songsem.lf, resultsem.lf)
        else:
            ops, song_steps, result_steps, distance = \
                    tonal_space_alignment(songsem.lf, resultsem.lf, distance=True)
        print "Steps in '%s':" % song[0]
        print song_steps
        if self.options['song']:
            print "Steps in '%s'" % compsong[0]
        else:
            print "Steps in result path:"
        print result_steps
        print "Alignment operations:"
        print ops
        
        if self.options['alignment']:
            print "Full alignment:"
            # Print the alignment in three rows
            WRAP_TO = 70
            wrapped_rows = []
            current_row = []
            current_width = 0
            # Wrap the rows
            for cells in arrange_alignment(song_steps, result_steps, ops):
                if len(cells[0]) + current_width > WRAP_TO:
                    # Start a new row
                    wrapped_rows.append(current_row)
                    current_row = []
                    current_width = 0
                current_row.append(cells)
                current_width += len(cells[0])
            # Add the incomplete last row
            wrapped_rows.append(current_row)
            for row in wrapped_rows:
                lefts, rights, opses = zip(*row)
                print " ".join(lefts)
                print " ".join(rights)
                print " ".join(opses)
                print
        print "Distance: %s" % distance

class ResultSongDependencyRecoveryTool(Tool):
    name = "Compare result"
    commands = ['songcomparedep', 'songdep']
    usage = ('songcomparedep <result-num> <song-num>', "compare a parse result "\
        "to a song in the database using the tonal space edit distance metric")
    help = """\
Compares a parse result to a specific song in the database in terms of 
dependency recovery and outputs the recall, precision and f-score.

See also:
    songcomparets: to compare a result to a song in terms of tonal space path 
        edit distance.
"""
    tool_options = Tool.tool_options + [
        ModuleOption('song', filter=str_to_bool,
                     usage="tosong=B, where B is true or false",
                     default=False,
                     help_text="Compare the numbered song in the corpus to the "\
                        "second song, instead of comparing the numbered result "\
                        "to the song"),
    ]
    
    def run(self, args, state):
        from jazzparser.formalisms.music_halfspan.semantics.distance import \
                            MaximalDependencyAlignment
        
        if len(args) < 2:
            raise ShellError, "Give a result number and a song number"
        
        resnum = int(args[0])
        songnum = int(args[1])
        
        song = get_song(songnum, state)
        songsem = song[1]
        
        if self.options['song']:
            # Compare a song instead of a result
            compsong = get_song(resnum, state)
            resultsem = compsong[1]
            print "Comparing '%s' to '%s'" % (compsong[0], song[0])
        else:
            # Normal behaviour: compare a result to a song
            if resnum >= len(state.results):
                raise ShellError, "No result number %d" % resnum
            result = state.results[resnum]
            resultsem = result.semantics
            print "Comparing result %d to '%s'" % (resnum, song[0])
        
        # Compare the two logical forms on the basis of overlapping dependencies
        options = {
            'output' : 'recall', 
        }
        recall_metric = MaximalDependencyAlignment(options=options)
        
        options = {
            'output' : 'precision', 
        }
        precision_metric = MaximalDependencyAlignment(options=options)
        
        recall = recall_metric.distance(resultsem, songsem)
        precision = precision_metric.distance(resultsem, songsem)
        
        # Print out each comparison
        print "Recall: %s" % recall
        print "Precision: %s" % precision
        print "F-score: %s" % (2.0*recall*precision / (recall+precision))

class RecogniseSongTool(Tool):
    name = "Recognise song"
    commands = ['findsong', 'song']
    usage = ('findsong [<result-num>]', "find the closest matching song "\
                "in the loaded songset")
    help = """\
Compares a parse result (the top probability one by default) to all the songs 
in the loaded songset and finds the closest matches by tonal space path 
similarity. Outputs a list of the closest matches.
"""
    tool_options = Tool.tool_options + [
        ModuleOption('average', filter=int,
                     usage="average=N, where B is an integer",
                     help_text="Average the distance measure over that given "\
                        "by the top N results (starting at the result given "\
                        "in the first argument, if given)"),
        ModuleOption('metric',
                     usage="metric=M, where M is the name of an available metric",
                     help_text="Select a metric to make the comparison with. "\
                        "Call with metric=help to get a list of metrics"),
        ModuleOption('mopts',
                     usage="mopts=OPT=VAL:OPT=VAL:...",
                     help_text="Options to pass to the metric. Use mopts=help "\
                        "to see a list of options"),
    ]
    
    def run(self, args, state):
        from jazzparser.formalisms.music_halfspan.evaluation import \
                        tonal_space_local_alignment, tonal_space_distance
        from jazzparser.formalisms.music_halfspan import Formalism
        
        metric_name = self.options['metric']
        if metric_name == "help":
            # Print a list of available metrics
            print ", ".join([metric.name for metric in Formalism.semantics_distance_metrics])
            return
        
        if len(args) == 0:
            resnum = 0
        else:
            resnum = int(args[0])
        
        if self.options['average'] and self.options['average'] > 1:
            # Average the distance over several results
            resnums = range(resnum, resnum+self.options['average'])
        else:
            # Just a single result
            resnums = [resnum]
        
        resultsems = []
        for resnum in resnums:
            # Get the result semantics that we're going to try to match
            if resnum >= len(state.results):
                raise ShellError, "No result number %d" % resnum
            result = state.results[resnum]
            resultsems.append(result.semantics)
        
        # Get the loaded songset containing the song corpus
        songset = state.get_data("songset", 
                            help_msg="Use command 'loadsongs' to load a songset")
        
        # Load the appropriate metric
        if metric_name is None:
            # Use the first in the list as default
            metric_cls = Formalism.semantics_distance_metrics[0]
        else:
            for m in Formalism.semantics_distance_metrics:
                if m.name == metric_name:
                    metric_cls = m
                    break
            else:
                # No metric found matching this name
                print "No metric '%s'" % metric_name
                sys.exit(1)
        print "Using distance metric: %s\n" % metric_cls.name
        # Now process the metric options
        moptstr = self.options['mopts']
        if moptstr is not None:
            if moptstr == "help":
                # Output this metric's option help
                print options_help_text(metric_cls.OPTIONS, 
                    intro="Available options for metric '%s'" % metric_cls.name)
                return
        else:
            moptstr = ""
        mopts = ModuleOption.process_option_string(moptstr)
        # Instantiate the metric with these options
        metric = metric_cls(options=mopts)
        
        song_distances = {}
        # Try matching against each song
        for resultsem in resultsems:
            for name,song in songset.analyses:
                distance = metric.distance(resultsem, song)
                song_distances.setdefault(name, []).append(distance)
        # Average the scores
        distances = []
        for name,costs in song_distances.items():
            ave_cost = sum(costs)/float(len(costs))
            distances.append((ave_cost,name))

        # Sort so the closest ones come first
        distances.sort(key=lambda x:x[0])
        
        # Output all the songs, ordered by similarity, with their distance
        for i,(distance,name) in enumerate(distances):
            print "%d> %s  (%s)" % (i, name, distance)
    
class SongSelfSimilarityTool(Tool):
    """
    For fooling around with comparing songs to themselves to see what happens.
    
    """
    name = "Self similarity"
    
    commands = ['selfsim']
    usage = ('selfsim <song-num>', "")
    help = ""
    tool_options = Tool.tool_options + [
        ModuleOption('local', filter=str_to_bool,
                     usage="local=B, where B is true or false",
                     default=False,
                     help_text="Sort results by local alignment score, not "\
                        "global"),
    ]
    
    def run(self, args, state):
        from jazzparser.formalisms.music_halfspan.evaluation import \
                        tonal_space_local_alignment, tonal_space_distance
        songnum = int(args[0])
        
        name,song = get_song(songnum, state)
        songset = state.get_data("songset")
        distances = []
        # Try comparing this song to each song in the set
        for other_name,other_song in songset.analyses:
            # Align locally and globally
            ops,steps1,steps2,local_distance = \
                    tonal_space_local_alignment(other_song.lf, song.lf)
            global_distance = \
                    tonal_space_distance(other_song.lf, song.lf)
            distances.append((other_name, local_distance, global_distance))
        
        # Sort the results
        if self.options['local']:
            distances.sort(key=lambda x:x[1])
        else:
            distances.sort(key=lambda x:x[2])
        # Print out each one
        print "Aligned %s with:" % name
        for other_name, local_distance, global_distance in distances:
            print "%s:  local: %s,  global: %s" % \
                (other_name,local_distance,global_distance)


class SongTreeTool(Tool):
    """
    Converts a song's semantics to a tree. Mainly just for debugging.
    
    """
    name = "Song tree"
    commands = ['tree']
    usage = ('tree <song-num>', "converts the semantics of the song to a tree "\
                "representation")
    tool_options = Tool.tool_options + [
        ModuleOption('res', filter=str_to_bool,
                     usage="res=B, where B is true or false",
                     default=False,
                     help_text="Show a result, instead of a corpus song"),
    ]
    help = """\
Converts the semantics of the numbered song to its tree representation that 
will be used for comparison to other logical forms. This is mainly for 
debugging and has no use in itself.
"""
    
    def run(self, args, state):
        from jazzparser.formalisms.music_halfspan.harmstruct import \
                                            semantics_to_dependency_trees
        if self.options['res']:
            resnum = int(args[0])
            res = state.results[resnum]
            song = res.semantics
            print "Dependency tree for result %d\n" % resnum
        else:
            songnum = int(args[0])
            name,song = get_song(songnum, state)
            print "Dependency tree for '%s'\n" % name
        
        print "Semantics:"
        print song
        print "\nTrees:"
        for t in semantics_to_dependency_trees(song):
            print t

class SongDependencyGraphTool(Tool):
    """
    Converts a song's semantics to a tree. Mainly just for debugging.
    
    """
    name = "Song dependency graph"
    commands = ['depgraph', 'dep']
    usage = ('depgraph <song-num>', "converts the semantics of the song to a "\
        "dependency graph representation")
    tool_options = Tool.tool_options + [
        ModuleOption('res', filter=str_to_bool,
                     usage="res=B, where B is true or false",
                     default=False,
                     help_text="Show a result, instead of a corpus song"),
    ]
    help = """\
Converts the semantics of the numbered song to its tree representation that 
will be used for comparison to other logical forms. This is mainly for 
debugging and has no use in itself.
"""
    
    def run(self, args, state):
        from jazzparser.formalisms.music_halfspan.harmstruct import \
                                            semantics_to_dependency_graph
        if self.options['res']:
            resnum = int(args[0])
            res = state.results[resnum]
            song = res.semantics
            print "Dependency graph for result %d\n" % resnum
        else:
            songnum = int(args[0])
            name,song = get_song(songnum, state)
            print "Dependency graph for '%s'\n" % name
        
        print "Semantics:"
        print song
        print
        graph, times = semantics_to_dependency_graph(song)
        print graph


def get_song(num, state):
    """
    Retreive a song from the loaded songset by number. Utility function used 
    by tools above.
    
    """
    songset = state.get_data("songset", 
                        help_msg="Use command 'loadsongs' to load a songset")
    if num >= len(songset):
        raise ShellError, "There is no song %d. Use the 'songs' command to "\
            "see a list of songs" % num
    else:
        return songset.analyses[num]
