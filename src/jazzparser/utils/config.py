"""Config file parsing

All of the scripts in this project use the optparse package to handle 
command line options.

This module provides a very simple mechanism for taking config files 
as input instead of specifying options on the command line. This is 
convenient, for example, for running experiments repeatedly where a 
whole load of options need to be given to set parameters.

The options in the file are stored in the following format::
 optname=value

 - The files may contain comments beginning with a '#'.
 - To specify arguments, just put the argument on a line of its own.
 - To specify flags, put the flag name on a line of its own preceded by a +.

You can only use long option names currently. This is best practice 
anyway, as it makes the file more readable.

The config options are simply transformed into a string of 
command-line-like options and added to the actual command-line options.

Don't forget to put a comment in the file so you know what script it's 
for!

Additionally, lines beginning with '%%' are treated as directives.
 - C{%% INCLUDE filename}: includes another config file.
 - C{%% ARG i value}: treats C{value} as the ith argument. If you 
    specify any arguments in this way, you should specify them all like
    this. Allows the arguments not to be given in order.
 - C{%% DEF name value}: defines or defines the value of the variable 
    C{name}. This value may subsequently be used with a %{name} 
    substitution.
 - C{%% ABSTRACT}: declares the whole file to be abstract, i.e. it cannot 
    be used directly, but only as an include in another file. You should 
    put this in any file that relies on including files to supply required 
    options/arguments.
 - C{%% REQUIRE option}: requires the user to specify the named option on 
    the command line when using this config file.

You may use certain substitutions in the options. %{X} will be replaced 
by a value if one can be found. The following sources are consulted (in 
this order):
 - a variable X defined with a DEF directive;
 - a constant X from the settings file.
One purpose of this is to allow you to specify paths relative to the 
project root, etc, rather than where the script is run.

A linebreak preceded by a \ will be ignored. Whitespace at the start 
of the subsequent line will be ignored (but not whitespace before the 
\).

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

class ConfigFile(object):
    """
    A really simple interface to options stored in config files.
    Can also process a string as if read from the contents of a file.
    
    """
    def __init__(self, filename, string=False):
        self.options = []
        self.flags = []
        self.arguments = []
        self.required_options = []
        
        if string:
            # Take the config lines as a string directly
            self.filename = None
            self.lines = filename.split("\n")
        else:
            # Read config lines from a file
            self.filename = filename
            with  open(self.filename, 'r') as cfile:
                self.lines = cfile.readlines()
        self.parse_lines()
    
    @staticmethod
    def from_string(string):
        return ConfigFile(string, string=True)
        
    def parse_lines(self):
        """
        Parses the lines stored in self.lines. Called by initialization.
        You can call this straight off if you've instantiated with a string.
        
        """
        from jazzparser import settings
        import os
        
        conf_lines = self.lines
        
        numbered_args = {}
        defined_variables = {}
        
        def _do_substitutions(value, full_line):
            # Look for any placeholders in the value and perform the 
            #  appropriate substitution
            while "%{" in value:
                opener = value.index("%{")
                closer = value.find("}", opener)
                if closer == -1:
                    # No matching close brace
                    raise ConfigFileReadError, "no matching close brace (}) found in %s" % full_line
                const_name = value[opener+2:closer]
                
                if const_name in defined_variables:
                    # First check whether a value is defined for this name
                    sub_value = defined_variables[const_name]
                elif hasattr(settings, const_name):
                    # Try getting a constant from the settings file
                    sub_value = getattr(settings, const_name)
                else:
                    raise ConfigFileReadError, "no setting or variable "\
                        "'%s' found to make substitution in: %s" % \
                        (const_name, full_line.strip())
                # Replace every occurrence of this placeholder with the value
                value = value.replace("%{"+const_name+"}", sub_value)
            return value
        
        # Preprocess the lines
        def _preprocess_lines(lines, included=False):
            _proc_lines = []
            
            # Remove line breaks from the end
            lines = [l.rstrip("\n") for l in lines]
            # Concatenate lines where a \ precedes the line break
            joined_lines = []
            to_join = []
            for line in lines:
                if line.endswith("\\"):
                    to_join.append(line[:-1].lstrip())
                else:
                    if len(to_join) > 0:
                        to_join.append(line.lstrip())
                        joined_lines.append("".join(to_join))
                        to_join = []
                    else:
                        joined_lines.append(line)
            
            for line in joined_lines:
                use_line = True
                # Ignore anything after a #
                if "#" in line:
                    line = line[:line.index("#")]
                line = line.strip()
                
                # Check for directives
                if line.startswith("%%"):
                    # Eliminate this line from the preprocessed set
                    use_line = False
                    
                    line = _do_substitutions(line[2:], line)
                    # Pull out the first word and make it case insensitive
                    directive = line.split()[0].strip().lower()
                    args = line.split()[1:]
                    # Check what the directive is a process the lines accordingly
                    if directive == "include":
                        if len(args) != 1:
                            raise ConfigFileReadError, "INCLUDE directive "\
                                "requires a filename argument"
                        # Include another config file
                        if self.filename is None:
                            # Can't make paths relative to filename
                            filename = args[0]
                        else:
                            filename = os.path.join(
                                            os.path.dirname(self.filename), 
                                            args[0])
                        filename = os.path.abspath(filename)
                        try:
                            file = open(filename, 'r')
                        except IOError:
                            raise ConfigFileReadError, "could not open "\
                                "included config file %s" % filename
                        
                        try:
                            # Replace this line with the lines of the other file
                            file_lines = _preprocess_lines(file.readlines(), included=True)
                            _proc_lines.extend(file_lines)
                        finally:
                            file.close()
                    elif directive == "arg":
                        if len(args) != 2:
                            raise ConfigFileReadError, "ARG directive "\
                                "requires an argument number and a value"
                        arg_num = int(args[0])
                        numbered_args[arg_num] = args[1]
                    elif directive == "def":
                        if len(args) != 2:
                            raise ConfigFileReadError, "DEF directive "\
                                "requires a variable name and a value"
                        defined_variables[args[0]] = args[1]
                    elif directive == "abstract":
                        if not included:
                            # The file isn't being read because it's included 
                            #  in another, but it's marked as abstract, so 
                            #  shouldn't be used directly
                            raise ConfigFileReadError, "encountered ABSTRACT "\
                                "directive in a non-included file. You should "\
                                "not use this file directly, but as an include "\
                                "in another config file."
                    elif directive == "require":
                        if len(args) != 1:
                            raise ConfigFileReadError, "REQUIRE directive "\
                                "needs an option name"
                        self.required_options.append(args[0])
                    # Define any more directives here
                    else:
                        raise ConfigFileReadError, "unknown directive: %s" % directive
            
                if use_line and len(line) > 0:
                    _proc_lines.append(line)
            return _proc_lines
        
        proc_lines = _preprocess_lines(conf_lines)
        if len(numbered_args) > 0:
            # Check that the numbered args make sense
            num_args = max(numbered_args.keys())
            for i in range(num_args+1):
                if i not in numbered_args:
                    raise ConfigFileReadError, "missing argument: "\
                        "arg number %s was given but %s was not" % \
                        (num_args, i)
            # Transform these into ordinary ordered args
            self.arguments = [numbered_args[i] for i in range(num_args+1)]
                
        for line in proc_lines:
            if line.startswith("+"):
                # Take the + off and store this as a flag
                self.flags.append(line[1:])
            elif "=" in line:
                # Split the optname=val into optname and val
                opt, __, val = line.partition("=")
                self.options.append((opt.strip(), _do_substitutions(val.strip(), line)))
            else:
                # Just a plain argument
                if len(numbered_args) > 0:
                    raise ConfigFileReadError, "cannot mix numbered args "\
                        "and non-numbered args: %s" % line
                self.arguments.append(_do_substitutions(line.strip(), line))
                
    def get_strings(self):
        """
        Get a list of strings containing all the config options in a form ready 
        to be passed to optparse as if they were command-line options.
        
        """
        return sum([["--%s" % opt, "%s" % val] for (opt,val) in self.options], []) \
                + ["--%s" % flag for flag in self.flags] \
                + self.arguments

def parse_args_with_config(parser, option_name="config"):
    """
    An alternative to calling parser.parse_args() which adds a --config
    option to the parser's options and uses it to read in a config 
    file if it's given.
    
    The args will potentially get parsed twice: once to get the config 
    file and then again to incorporate options from the file.
    
    @return: (options, arguments) tuple, as given by parser.parse_args().
    
    """
    import sys
    # Add the config file option
    parser.add_option("--%s" % option_name, dest="%s" % option_name, action="store", help="read options in from a config file.")
    # Do the initial (standard) parse
    options,arguments = parser.parse_args()
    
    conf_file = getattr(options, option_name)
    if conf_file is not None:
        # Read in options from the config file
        conf = ConfigFile(conf_file)
        # Check that any options the file requires the user to give are there
        for required in conf.required_options:
            if not hasattr(options, required):
                raise ConfigFileReadError, "config file requires non-existent "\
                    "command line option '%s'" % required
            elif getattr(options, required) is None:
                print "Error: config file requires that you "\
                        "give the option '%s' on the command line" % required
                sys.exit(1)
        # Produce arguments that incorporate the file and cmd-line opts
        conf_strings = conf.get_strings()
        if len(conf_strings) > 0:
            # Parse the opts and args from the config file first
            options, file_arguments = parser.parse_args(args=conf_strings)
            # Reparse the command line options so that values given there 
            #  override those in the file
            options, cl_arguments = parser.parse_args(values=options)
            # Include arguments from both sources, file first
            arguments = file_arguments + cl_arguments
    return options,arguments

class ConfigFileReadError(Exception):
    pass
