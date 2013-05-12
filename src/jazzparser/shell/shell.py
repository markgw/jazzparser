"""Jazz Parser interactive shell for examining the output of the parser.

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

import sys, traceback, logging, os
from jazzparser import settings
from jazzparser.formalisms.loader import get_default_formalism
from . import tools
from . import gstools

try:
    import readline
except ImportError:
    readline_loaded = False
else:
    readline_loaded = True

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

CORE_TOOLS = [ 
    tools.HelpTool(),
    tools.DerivationTraceTool(),
    tools.DerivationTraceExplorerTool(),
    tools.AtomsOnlyTool(),
    tools.ResultListTool(),
    tools.RuleApplicationTool(),
    tools.LogLevelTool(),
    tools.PythonTool(),
    tools.SaveStateTool(),
    tools.TonalSpaceCoordinatesTool(),
    tools.LoadResultsTool(),
    gstools.LoadGoldStandardTool(),
    gstools.MarkCorrectTool(),
]

def interactive_shell(results,options,tagger,parser,formalism,env,seq_id=None,input_data=None):
    """
    Use an interactive shell to display and give detailed access to 
    the given results, produced by the parser.
    
    """
    tool_sources = formalism.shell_tools + \
                   parser.shell_tools + \
                   tagger.shell_tools
    # Get commands for the input type
    if input_data is not None:
        # Add all tools for this data type
        tool_sources.extend(input_data.SHELL_TOOLS)
    
    state = ShellState(results, options, tagger, parser, formalism, env, 
                        seq_id=seq_id, input_data=input_data)
    # Pass over to the shell function to run the actual shell
    shell(state, tools=tool_sources)
    
def restore_shell(name, tools=[]):
    """
    Restores an interactive shell session from a saved state. Such a state 
    is stored using the 'save' command from a shell session (e.g. after 
    parsing).
    
    """
    state = ShellState.load(name)
    
    tool_sources = []
    # Load tools for the formalism, parser and tagger if they're available
    if state.formalism is not None:
        tool_sources.extend(state.formalism.shell_tools)
    if state.parser is not None:
        tool_sources.extend(state.parser.shell_tools)
    if state.tagger is not None:
        tool_sources.extend(state.tagger.shell_tools)
    if state.input_data is not None:
        tool_sources.extend(state.input_data.SHELL_TOOLS)
    
    print "Restoring shell state from saved session '%s'\n" % name
    # Pass over to the main shell function
    shell(state, tools=tool_sources+tools)

def empty_shell(tools=[]):
    """
    Starts up the interactive shell with no shell state.
    
    """
    state = ShellState()
    
    tool_sources = []
    # Load tools for the formalism, parser and tagger if they're available
    if state.formalism is not None:
        tool_sources.extend(state.formalism.shell_tools)
    
    # Pass over to the main shell function
    shell(state, tools=tool_sources+tools)
    
def shell(state, tools=[]):
    """
    Starts up the shell with a given L{ShellState}. This is called by 
    L{interactive_shell}, as used by the parser, and also by L{restore_shell}.
    
    """
    # Load the shell history if possible
    if readline_loaded:
        try:
            readline.read_history_file(settings.SHELL_HISTORY_FILE)
        except IOError:
            # No history file found. No problem
            pass
    
    # We should have received a list of tools and we add to this the standard ones
    tool_sources = CORE_TOOLS + tools
    # Build the list of available commands
    tools = {}
    all_tools = []
    for tool in tool_sources:
        for cmd in tool.commands:
            if cmd in tools:
                raise ShellError, "The command '%s' provided by '%s' is already "\
                    "provided by '%s'" % (cmd, tools[cmd].name, tool.name)
            tools[cmd] = tool
        all_tools.append(tool)
    state.tools = tools
    state.all_tools = all_tools
    
    # Display the shell intro
    print "<<<< Jazz Parser interactive shell >>>>"
    print "Type 'help' for command list"
    
    input = ""
    while input != "quit":
        sys.stdout.flush()
        try:
            input = raw_input(">> ")
        except EOFError:
            print
            break
            
        if input:
            try:
                # Pull out the command
                input = input.rstrip("\n").strip()
                command = input.split()[0]
                # A special command
                if command == "q" or command == "quit":
                    break
                
                # Get the args and try finding a tool for this command
                tokens = input.split()[1:]
                if command not in tools:
                    raise ShellError, "Unknown command: %s. Use 'help' for a list of available commands." % command
                else:
                    tool = tools[command]
                    
                    # Look for args that are actually options
                    args = []
                    options = []
                    for token in tokens:
                        if "=" in token:
                            # This must be an option
                            opt,__,val = token.partition("=")
                            if len(opt) == 0 or len(val) == 0:
                                raise ShellError, "Options must be given in "\
                                    "the form OPT=VALUE. Could not parse %s"\
                                        % token
                            options.append(token)
                        else:
                            # Otherwise, we just treat it as an arg
                            args.append(token)
                    
                    tool.process_option_list(options)
                    tool.run(args, state)
                
            except ShellError, msg:
                # We raised an error because something in the input was bad
                print msg
            except:
                # Any other error: just output it and go on
                traceback.print_exc(file=sys.stderr)
    # Write the history out to a file
    if readline_loaded:
        readline.write_history_file(settings.SHELL_HISTORY_FILE)
    print "Bye!"
    
class ShellState(object):
    """
    Class to wrap up the various bits of state that need to be stored 
    in the shell and that may be manipulated by tools.
    """
    def __init__(self, results=[], options=None, tagger=None, parser=None, 
                    formalism=None, env=None, seq_id=None, input_data=None):
        self.results = results
        self.options = options
        self.parser = parser
        self.env = env
        self.seq_id = seq_id
        self.input_data = input_data
        self.tagger = tagger
        self.data = {}
        
        if formalism is None:
            # Use the default formalism
            self.formalism = get_default_formalism()
        else:
            self.formalism = formalism
        
        self.tools = {}
        self.all_tools = []
    
    def get_data(self, name, help_msg=""):
        """
        Get previously loaded data, or raise a ShellError saying it's not 
        been loaded.
        
        """
        if name in self.data:
            return self.data[name]
        else:
            # Data hasn't been loaded
            # Display an error and any additional help info given by requester
            raise ShellError, "Data set '%s' has not been loaded. %s" % \
                (name, help_msg)
    
    def save(self, name):
        """
        Pickles the shell state and stores it to a file.
        
        """
        import cPickle as pickle
        
        filename = os.path.join(settings.SHELL_STATE_DIR, "%s.shst" % name)
        outfile = open(filename, "wb")
        # Only include certain bits of the state: not everything is picklable
        data = {
            'results' : self.results,
            'options' : self.options,
            'tools' : self.tools,
            'all_tools' : self.all_tools,
            'seq_id' : self.seq_id,
            'input_data' : self.input_data,
            'data' : self.data,
            'formalism' : self.formalism,
        }
        try:
            # Pickle the object
            pickle.dump(data, outfile, protocol=-1)
        finally:
            outfile.close()
    
    @staticmethod
    def load(name):
        """
        Loads a pickled state representation.
        
        """
        import cPickle as pickle
        
        filename = os.path.join(settings.SHELL_STATE_DIR, "%s.shst" % name)
        # Check this state has been saved
        if not os.path.exists(filename):
            raise ShellRestoreError, "saved shell state '%s' does not exist" % \
                name
        infile = open(filename, "rb")
        
        try:
            # Unpickle the data
            data = pickle.load(infile)
        finally:
            infile.close()
        
        # Create a shell state from this data
        return ShellState(
                results = data['results'],
                options = data['options'],
                formalism = data['formalism'],
                seq_id = data['seq_id'],
                input_data = data['input_data'])
    
    @staticmethod
    def list():
        """
        List the names of stored shell sessions.
        
        """
        files = os.listdir(settings.SHELL_STATE_DIR)
        files = [filename.rpartition(".") for filename in files]
        # Only include files with the right extension
        names = [name for (name,__,ext) in files if ext == "shst"]
        return names
    
    @staticmethod
    def remove(name):
        """
        Remove the named saved session.
        
        """
        filename = os.path.join(settings.SHELL_STATE_DIR, "%s.shst" % name)
        if not os.path.exists(filename):
            raise ValueError, "couldn't not delete shell state '%s': it "\
                "doesn't exist" % name
        os.remove(filename)

class ShellError(Exception):
    pass

class ShellRestoreError(Exception):
    pass
