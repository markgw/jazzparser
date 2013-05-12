"""The basic set of tools for the shell.

The basic tools for the Jazz Parser interactive shell for examining 
the output of the parser. These are all generic to all formalisms 
are parsers. Other formalism- and parser-specific tools can be defined 
separately.

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

from jazzparser.utils.options import ModuleOption
from textwrap import wrap

class Tool(object):
    """
    Base class for interactive shell tools. A basic set of subclasses 
    is provided here, others may be provided by a formalism, tagger, parser, 
    etc.
    
    """
    name = None
    commands = []
    usage = ('command','help text')
    help = """
No help text defined for this command.
"""
    tool_options = []
    
    def run(self, args, state):
        """
        Main operation of tool, taking arguments in args and reading 
        and potentially manipulating the shell state.
        
        By the time this is called, the options dict is available in 
        self.options.
        
        """
        pass
    
    def process_option_list(self, options):
        optdict = ModuleOption.process_option_string(options)
        self.options = ModuleOption.process_option_dict(optdict, self.tool_options)

#################################################
#### Core tools

class DerivationTraceTool(Tool):
    """
    Shell tool for outputing derivation traces.
    """
    name = "Derivation Trace"
    commands = ['deriv', 'd']
    usage = ('deriv <res>', 'show derivation of numbered result.')
    help = """
Shows a full derivation trace for a specific result.
This includes all possible derivations of the sign. In order to use this,
the parser must have been run with the -d option, so that it stored 
the traces during parsing.
Specify the result by its enumeration in the result list.
"""
    
    def run(self, args, state):
        results = state.results
        # We must have an argument
        from .shell import ShellError
        if len(args) == 0:
            raise ShellError, "You must specify the number of a result"
        # Display the trace for this result
        result_num = int(args[0])
        if result_num < len(results):
            if results[result_num].derivation_trace is None:
                raise ShellError, "Derivation traces have not been stored. Run parser with -d flag to create them"
            else:
                print "Derivation trace for result %d: %s" % (result_num,results[result_num])
                print "\n%s" % results[result_num].derivation_trace
        else:
            raise ShellError, "There are only %d results" % len(results)

class DerivationTraceExplorerTool(Tool):
    """
    Shell tool for exploring large derivation traces in more detail.
    """
    name = "Derivation Trace Explorer"
    commands = ['derivex', 'de']
    usage = ('derivex <res>', 'explore derivation of numbered result.')
    help = """
Explores the derivation trace of a particular result.

Unlike deriv, which shows the full derivation trace, this shows just 
one level at a time, from the top of the tree. It then recurses 
interactively.
"""
    
    def run(self, args, state):
        results = state.results
        # We must have an argument
        from .shell import ShellError
        if len(args) == 0:
            raise ShellError, "You must specify the number of a result"
        # Display the trace for this result
        result_num = int(args[0])
        if result_num < len(results):
            if results[result_num].derivation_trace is None:
                raise ShellError, "Derivation traces have not been stored. Run parser with -d flag to create them"
            else:
                print "Derivation trace for result %d: %s" % (result_num,results[result_num])
                top_trace = results[result_num].derivation_trace
                root_traces = [top_trace]
                while True:
                    print
                    trace = root_traces[-1]
                    print " <- ".join([str(t.result) for t in reversed(root_traces)])
                    if trace.word is not None:
                        print " lexical category for %s" % trace.word
                        root_traces.pop()
                    else:
                        print " derived from:"
                        for i,(rule,traces) in enumerate(trace.rules):
                            print "%d  %s ->\t %s" % (i,rule.name,"\t ".join([str(t.result) for t in traces]))
                        cmd = raw_input("Expand number (up: .., stop: q): ")
                        if cmd == "q":
                            return
                        if cmd == "..":
                            root_traces.pop()
                        else:
                            # Recurse to inspect one level down
                            rec_num = int(cmd)
                            next_traces = trace.rules[rec_num][1]
                            # Choose which sign to recurse on
                            arg = raw_input("Which argument (0-%d)? " % (len(next_traces)-1))
                            arg = int(arg)
                            root_traces.append(next_traces[arg])
        else:
            raise ShellError, "There are only %d results" % len(results)

class AtomsOnlyTool(Tool):
    """
    Removes all complex categories from the results list.
    """
    name = "Atoms Only"
    commands = ['atoms']
    usage = ('atoms', "remove any complex category results from the results list.")
    help = """
Removes any results from the result list that are not atomic categories.
Also prints out the resulting result list.
Any subsequent commands will operate on this filtered result list.
"""
    
    def run(self, args, state):
        from jazzparser.parser import list_results, remove_complex_categories
        
        state.results = remove_complex_categories(state.results, state.formalism)
        # Print the new list
        list_results(state.results, state.options.silent)

class ResultListTool(Tool):
    """
    Prints out a particular range of results, or the whole list.
    """
    name = "Result Slice"
    commands = ['res']
    usage = ("res [<start> [<end>]]", "show the results list again, optionally giving a range.")
    help = """
Prints out the current result list, with result numbers.
Optionally, you may specify a valid range of result numbers to display.
"""
    
    def run(self, args, state):
        from jazzparser.parser import list_results
        from .shell import ShellError
        
        if len(args) == 1:
            res = int(args[0])
            print "Showing result %d" % res
            result_list = [state.results[res]]
        elif len(args) == 2:
            start,end = int(args[0]), int(args[1])
            print "Showing results in range [%s:%s]" % (start,end)
            result_list = state.results[start:end]
        else:
            result_list = state.results
        
        # Display results again
        if state.options is not None:
            list_results(result_list, state.options.silent)
        else:
            list_results(result_list)

class RuleApplicationTool(Tool):
    """
    Manually applies a named rule to signs in the chart.
    """
    name = "Rule Application"
    commands = ['apply']
    usage = ("apply <rule> <sign> [<sign2> [...]]", "manually apply a named rule to "\
        "signs in the chart.")
    help = """
Apply a grammatical rule to signs in the chart.
The rule to apply is selected by its short name (type "apply" for a list 
of commands). The signs to use as input are selected by their position 
in the chart. Use the syntax x/y/i, where x and y are the starting and 
ending nodes for the arc and i is the index of the sign to select 
from that arc.

See also:
  chart, to display the current chart contents.
"""
    
    def run(self, args, state):
        from .shell import ShellError
        # Fetch the available rules from the grammar
        rules_by_name = dict([(rule.internal_name,rule) for rule in state.parser.grammar.rules])
        if len(args) == 0:
            raise ShellError, "You must specify one of the following rules to apply: %s" % ", ".join(rules_by_name.keys())
        elif len(args) == 1:
            raise ShellError, "You must specify at least one sign from the chart to apply the rule to. Specify a sign in the form 'arc_start/arc_end/index'."
        # Check the given rule name is available
        if args[0] not in rules_by_name:
            raise ShellError, "%s is not a valid rule name. You must specify one of the following rules to apply: %s" % (args[0],", ".join(rules_by_name.keys()))
        # Got a valid rule name. Get the rule that we'll use
        rule = rules_by_name[args[0]]
        signs = []
        # Get signs from the chart
        for arg in args[1:]:
            parts = arg.split("/")
            if len(parts) != 3:
                raise ShellError, "%s is not a valid chart sign. Specify a sign in the form 'arc_start/arc_end/index'." % arg
            parts = [int(p) for p in parts]
            sign = state.parser.chart.get_sign(parts[0], parts[1], parts[2])
            if sign is None:
                raise ShellError, "There is no sign at %s/%s/%s in the chart" % tuple(parts)
            signs.append(sign)
        # Try applying the rule to the signs
        if len(signs) != rule.arity:
            raise ShellError, "Rule %s requires %d arguments. Got %d." % (rule.internal_name, rule.arity, len(signs))
        result = rule.apply_rule(signs)
        if result is not None:
            result = result[0]
        print "Applied rule %s to %s => %s" % (rule.internal_name,", ".join(["%s" % s for s in signs]),result)

class TonalSpaceCoordinatesTool(Tool):
    name = "Longuet-Higgins tonal space coordinates"
    commands = ['tscoords', 'ts']
    usage = ("tscoords [<result>]", "displays the tonal space coordinates for the numbered result. Show the first result by default.")
    help = """\
Uses the formalism's function for converting a logical form to tonal space 
coordinates. Prints out the coordinates for a particular result.

"""
    
    def run(self, args, state):
        from .shell import ShellError
        
        if len(args) > 0:
            # First arg should be a result number
            resultnum = int(args[0])
        else:
            # Show the first by default
            resultnum = 0
        if resultnum >= len(state.results):
            raise ShellError, "no such result: %d" % resultnum
        result = state.results[resultnum]
        # Convert this result's semantics to coordinates
        coords = state.formalism.semantics_to_coordinates(result.semantics)
        print coords

class LoadResultsTool(Tool):
    name = "Load results"
    commands = ['loadresults', 'loadres']
    usage = ("loadresults <filename>", "loads a saved parse results file")
    help = """\
Loads parse results from a file to which they've been saved by the parser on 
a previous occasion. These results will replace any already in the shell state, 
so all other tools will henceforth operate on the loaded results.

"""
    
    def run(self, args, state):
        from .shell import ShellError
        from jazzparser.data.parsing import ParseResults
        
        # Load the file
        pres = ParseResults.from_file(args[0])
        
        if not hasattr(pres, "signs") or not pres.signs:
            raise ShellError, "loaded parse results, but they're stored as "\
                "logical forms, not signs, so we can't load them into the "\
                "state"
        # Replace the results in the state
        state.results = [res for (prob,res) in pres.parses]


class LogLevelTool(Tool):
    """
    Change the log level from the shell.
    """
    name = "Set Log Level"
    commands = ['logging']
    usage = ("logging <level>", "sets the main logger's log level to the given level name (\"DEBUG\", etc).")
    help = """
Change the log level.
The whole parser uses a main logger to output debugging info, warnings, 
etc. By default, this will only show warnings and errors, but this 
command allows you to change its log level. All subsequent commands 
will output logging at this level.

See constants in the Python logging module for log level names.
"""
    
    def run(self, args, state):
        from .shell import ShellError
        import logging
        
        if len(args) != 1:
            raise ShellError, "Specify a log level to change to"
        # Change the logging level
        logging_name = args[0].upper()
        try:
            loglevel = getattr(logging, logging_name)
        except AttributeError:
            raise ShellError, "%s is not a recognised logging level" % logging_name
            
        # Get the logger so we can set the log level
        logger = logging.getLogger("main_logger")
        logger.setLevel(loglevel)
        print "Changed the logging level to %s" % logging_name

class PythonTool(Tool):
    """
    Excecutes arbitrary python commands. The commands have access to 
    the parser, formalism, options and results in the environment.
    """
    name = "Python"
    commands = ['python', 'py']
    usage = ("python <command>", "run an arbitrary Python command.")
    help = """
Runs an arbitrary Python command.
The given command will just be executed. Various references are 
available in the environment:
  results: the results list
  parser: the parser object
  formalism: the loaded formalism
  options: the command-line options
Also available is a dictionary called env, containing any further 
references made available when the shell was started. Usually this 
will include all local and global names.
"""
    
    def run(self, args, state):
        command = " ".join(args)
        results = state.results
        parser = state.parser
        formalism = state.formalism
        options = state.options
        env = state.env
        chart = parser.chart
        
        # Run the command
        exec command

class HelpTool(Tool):
    """
    Display shell help.
    """
    name = "Help"
    commands = ['help', 'h']
    usage = ("help [<command>]", "print out usage info for commands or help info.")
    help = """
Display usage info for a particular command.
If no command is given, displays brief usage info for all commands.
"""
    
    def run(self, args, state):
        from jazzparser.utils.tableprint import pprint_table
        import sys
        
        if len(args) == 0:
            # Print the command usage info
            table = []
            for tool in state.all_tools:
                if len(tool.commands) > 1:
                    alts = " [Alternatively: %s]" % ", ".join(tool.commands[1:])
                else: alts = ""
                # If the command has options, list them here as well
                if len(tool.tool_options) != 0:
                    opts = "\nOptions: %s" % ", ".join(\
                                [opt.name for opt in tool.tool_options])
                else:
                    opts = ""
                table.append([tool.usage[0], tool.usage[1]+alts+opts])
            pprint_table(sys.stdout, table, default_just=True, widths=[30,50], \
                            blank_row=True, hanging_indent=4)
            print "\nType 'help <command>' for detailed help about a command"
        else:
            command = args[0]
            if command not in state.tools:
                print "%s is not a valid command." % command
                print "Type 'help' for a full command list."
            else:
                tool = state.tools[command]
                title = "%s Shell Command" % tool.name
                # Compile the help text for the tool's options
                if len(tool.tool_options):
                    opts = "\nOptions:"
                    # Put required options first
                    for opt in [o for o in tool.tool_options if o.required]:
                        opts += "\n  %s  %s (REQUIRED)\n  %s" % \
                                    (opt.name, opt.usage, \
                                     "\n    ".join(wrap(opt.help_text, 75)))
                    # Then all the rest
                    for opt in [o for o in tool.tool_options if not o.required]:
                        opts += "\n%s  %s\n  %s" % \
                                    (opt.name, opt.usage, \
                                     "\n    ".join(wrap(opt.help_text, 75)))
                else:
                    opts = ""
                # Print out all of the info
                print """\
%s
%s
  Usage: %s     %s
  Command aliases: %s

%s%s""" % (title, "=" * len(title), 
            tool.usage[0], tool.usage[1], 
            ", ".join(tool.commands), 
            tool.help, opts)

class SaveStateTool(Tool):
    name = "Save state"
    commands = ['save']
    usage = ("save <name>", "save shell state to a file")
    help = """\
Saves the shell state to a file. The state can be resumed later using the 
'shell' option to the JazzParser.
"""
    
    def run(self, args, state):
        name = args[0]
        state.save(name)
