"""A formalism that implements my 2nd-year PhD style of syntax: halfspan.

This formalism uses the 03/11 halfspan syntax, a development of the 
old keyspan syntax, and a lambda-calculus semantics to go with it that 
deals in tonal space coordinates.

This is the default (and, at the moment, only) formalism.

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

from . import syntax, semantics, rules, domxml, evaluation, pcfg, songtools
from .semantics import distance
from jazzparser.formalisms import FormalismBase
from jazzparser.formalisms.base.semantics.timetools import TimeOutputTool
from jazzparser.utils.options import ModuleOption, choose_from_list

class Formalism(FormalismBase):
    rules = {
        'application' : rules.ApplicationRule,
        'composition' : rules.CompositionRule,
        'development' : rules.DevelopmentRule,
        'coordination' : rules.CoordinationRule,
        'tonicrepetition' : rules.TonicRepetitionRule,
        'cadencerepetition' : rules.CadenceRepetitionRule,
    }
    
    lexicon_builder = staticmethod(domxml.build_sign_from_node)
    # We don't need to do anything to distinguish variables
    distinguish_categories = staticmethod(lambda x,y: None)
    unify = staticmethod(syntax.unify)
    # This doesn't need to do anything for now
    clean_results = staticmethod(lambda x:x)
    
    shell_tools = [
        TimeOutputTool(),
        songtools.LoadCorpusTool(),
        songtools.ListSongsTool(),
        songtools.PrintAnalysisTool(),
        songtools.ResultSongTSEditDistanceTool(),
        songtools.ResultSongDependencyRecoveryTool(),
        songtools.RecogniseSongTool(),
        songtools.SongSelfSimilarityTool(),
        songtools.SongTreeTool(),
        songtools.SongDependencyGraphTool(),
    ]
    
    output_options = [
        ModuleOption('tsformat',
                 choose_from_list(['coord', 'xycoord', 'roman','alpha']), 
                 help_text="Tonal space output format", 
                 default="coord",
                 usage="tsformat=X, where X is one of 'coord', 'xycoord', "\
                    "'alpha' or 'roman'"),
    ]
    
    backoff_states_to_lf = staticmethod(semantics.backoff_states_to_lf)
    semantics_to_coordinates = staticmethod(semantics.semantics_to_coordinates)
    semantics_to_functions = staticmethod(semantics.semantics_to_functions)
    semantics_to_keys = staticmethod(semantics.semantics_to_keys)
    
    semantics_distance_metrics = [
        distance.TonalSpaceEditDistance,
        distance.LargestCommonEmbeddedSubtrees,
        distance.RandomDistance,
        distance.DependencyGraphSize,
        distance.OptimizedDependencyRecovery,
        distance.DependencyRecovery,
    ]
    
    PcfgModel = pcfg.HalfspanPcfgModel
    
    class Syntax(FormalismBase.Syntax):
        Sign = syntax.Sign
        ComplexCategory = syntax.ComplexCategory
        AtomicCategory = syntax.AtomicCategory
        Slash = syntax.Slash
        DummyCategory = syntax.DummyCategory
        merge_equal_signs = staticmethod(syntax.merge_equal_signs)
        
        # Unlike previous formalisms, we can't use the normal category 
        #  structure abstraction, so we inject our own handling of 
        #  half categories
        pre_generalize_category = staticmethod(syntax.pre_generalize_category)
        
        @classmethod
        def is_complex_category(cls, obj):
            """
            For the sake of efficiency, override this and don't use 
            isinstance.
            This gets called a LOT of times!
            """
            return obj.ATOMIC == False
        
        @classmethod
        def is_atomic_category(cls, obj):
            """
            For the sake of efficiency, override this and don't use 
            isinstance.
            This gets called a LOT of times!
            
            This works because the category classes in this formalism 
            all define ATOMIC, so we don't need to check the type.
            
            """
            return obj.ATOMIC == True
    
    class Semantics(FormalismBase.Semantics):
        Semantics = semantics.Semantics
        apply = staticmethod(semantics.apply)
        compose = staticmethod(semantics.compose)
    
    class PcfgParser(object):
        """ Formalism interface for the PcfgParser parser module. """
        # Function to generate the representation of a category to 
        #  be used to index the model
        category_representation = staticmethod(pcfg.model_category_repr)
        # Mapping between the short names used for rules in annotated 
        #  trees and the rule instantiations
        rule_short_names = {
            'compf' : ('composition', {'dir':'forward'}),
            'compb' : ('composition', {'dir':'backward'}),
            'appf'  : ('application', {'dir':'forward'}),
            'appb'  : ('application', {'dir':'backward'}),
            'cont'  : ('development', {}),
            'coord' : ('coordination', {}),
        }
        category_relative_chord = staticmethod(pcfg.category_relative_chord)
    
    class Evaluation(FormalismBase.Evaluation):
        tonal_space_alignment_costs = staticmethod(evaluation.tonal_space_alignment_costs)
        tonal_space_distance = staticmethod(evaluation.tonal_space_distance)
        tonal_space_f_score = staticmethod(evaluation.tonal_space_f_score)
        tonal_space_alignment_score = staticmethod(evaluation.tonal_space_alignment_score)
        tonal_space_alignment = staticmethod(evaluation.tonal_space_alignment)
        
        tonal_space_length = staticmethod(evaluation.tonal_space_length)
        """ Number of points on the tonal space path represented by the semantics """
