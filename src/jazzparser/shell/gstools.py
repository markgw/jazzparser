"""Gold standard comparison shell tools

Some additional tools for the Jazz Parser interactive shell for 
comparing results to a gold standard.

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

from .tools import Tool

class LoadGoldStandardTool(Tool):
    """
    Load an annotated chord sequence file.
    """
    name = "Gold Standard"
    commands = ['loadgs', 'lgs']
    usage = ("loadgs <filename>", "load an annotated data file for use by other GS tools")
    help = """
Given a filename of a db mirror data file, loads the data ready for 
use by other GS comparison tools.
"""
    
    def run(self, args, state):
        from jazzparser.data.db_mirrors import SequenceIndex
        from .shell import ShellError
        if len(args) < 1:
            raise ShellError, "Please specify a file to load"
        filename = args[0]
        # Load the data file
        si = SequenceIndex.from_file(filename)
        # Store it in the state
        state.gs_sequences = si
        print "Loaded %d gold standard sequences from %s" % (len(si),filename)

class MarkCorrectTool(Tool):
    name = "Mark Correct"
    commands = ['markcorrect', 'mark']
    usage = ("markcorrect", "marks all the lexical entries in the "\
                "chart that are correct according to the gold standard")
    help = """
Goes through the chart and marks those lexical signs that were the 
correct choice according to the gold standard. Each correct sign has its 
__str__ wrapped so it will display a marker of its correctness when 
printed.
"""
    
    def run(self, args, state):
        from .shell import ShellError
        # Only allow this to be run once
        if hasattr(state, '_markcorrect_run'):
            raise ShellError, "Correct entries have already been marked"
        id = _get_seq_id(state)
        _check_gs_has_sequence(state, id)
        # We've got an id and the right GS sequence
        gs_seq = state.gs_sequences.sequence_by_id(id)
        
        # Decorate the str method of Sign so that we can put in an extra marker
        def _mark_str(str_fn):
            def _correct_str(obj):
                prepend = getattr(obj, '_str_prepend', '')
                return "%s%s" % (prepend, str_fn(obj))
            return _correct_str
        state.formalism.Syntax.Sign.__str__ = _mark_str(state.formalism.Syntax.Sign.__str__)
        
        # Go through each chord in the gold standard
        for i,chord in enumerate(gs_seq.iterator()):
            tag = chord.category
            found = False
            for sign in state.parser.chart.get_signs(i, i+1):
                # If the sign stores a tag we can check whether it was right
                if hasattr(sign, 'tag') and sign.tag == tag:
                    found = True
                    print "Found correct tag for position %d: %s" % (i,sign)
                    sign._str_prepend = "***"
            if not found:
                print "Correct tag not found for position %d" % i
        state._markcorrect_run = True

def _check_gs_loaded(state):
    from .shell import ShellError
    if not hasattr(state, 'gs_sequences'):
        raise ShellError, "The no gold standard has been loaded. Use the loadgs command to load a file."
    
def _check_gs_has_sequence(state, id):
    _check_gs_loaded(state)
    if id not in state.gs_sequences.ids:
        raise ShellError, "The loaded gold standard doesn't include the sequence with id %s" % id

def _get_seq_id(state):
    from .shell import ShellError
    if state.seq_id is None:
        raise ShellError, "Not sequence id available for parsed sequence: cannot run this tool"
    return state.seq_id
