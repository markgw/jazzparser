#!/usr/bin/env ../../jazzshell
"""
Supplies a set of admin operations for trained models.

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

import sys, math, os, re
from optparse import OptionParser

from jazzparser.utils.interface import boolean_input
from jazzparser.misc.chordlabel import HPChordLabeler, ModelLoadError

def main():
    usage = "%prog <command> [<command-arg> ...]"
    description = "Provides administrative operations for trained "\
                "chord labeler models. Use the 'help' command to get a list "\
                "of commands or command usage."
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print >>sys.stderr, "You must specify a command"
        sys.exit(1)
    command = arguments[0].lower()
    command_args = arguments[1:]
    
    def _load_model(name):
        # Load the model from its file
        return HPChordLabeler.load_model(name)
        
    # Define behaviour for each command
    list_help = "Lists all the trained models available"
    def _list(args):
        # List the available models for the given model type
        models = HPChordLabeler.list_models()
        print "Available models:"
        print ", ".join(list(sorted(models)))
        
    desc_help = "Outputs the descriptive text associated with the model at training time"
    def _desc(args):
        if len(args) == 0:
            raise CommandError, "desc requires a model name as an argument"
        try:
            model = _load_model(args[0])
        except ModelLoadError, err:
            print >>sys.stderr, "No model %s\n" % (args[0])
            raise err
        print "Model descriptor"
        print "================"
        print model.description
    
    del_help = "Deletes a model and all its associated files"
    def _del(args):
        if len(args) != 1:
            raise CommandError, "del requires a model name as an argument"
        models = HPChordLabeler.list_models()
        model_name = args[0]
        if model_name not in models:
            print >>sys.stderr, "No model %s" % model_name
        
        model = _load_model(model_name)
        print "Deleting %s" % model_name
        model.delete()
    
    params_help = "Outputs the model's parameters in a human-readable format "\
            "(not available for all model types)"
    def _params(args):
        if len(args) == 0:
            raise CommandError, "params requires a model name as an argument"
        try:
            model = _load_model(args[0])
        except ModelLoadError, err:
            print >>sys.stderr, "No model %s\n" % (args[0])
            raise err
        
        print "Model parameters"
        print "================"
        print model.readable_parameters
    
    # Add commands by adding an entry to this dictionary
    # The key is the command name
    # The value is a tuple of a function to call and the help text for the command
    commands = {
        'list' : (_list, list_help),
        'desc' : (_desc, desc_help),
        'del' : (_del, del_help),
        'params' : (_params, params_help),
    }
    all_commands = commands.keys() + ['help']
    try:
        if command == "help":
            if len(command_args) == 0:
                print "Available commands: %s" % ", ".join(all_commands)
                print "Use 'help' followed by the command name to get command-specific usage."
                sys.exit(0)
            elif len(command_args) > 1:
                raise CommandError, "to get command help, use the command 'help' followed by the command name"
            if command_args[0] not in commands:
                raise CommandError, "unknown command '%s'. Available commands are: %s" % \
                        (command_args[0], ", ".join(all_commands))
            # Print out the help text given for the command
            print "Help for command '%s':" % command_args[0]
            print commands[command_args[0]][1]
            sys.exit(0)
        elif command in commands:
            # Run the command
            commands[command][0](command_args)
        else:
            # The command wasn't found in our defined commands
            raise CommandError, "unknown command '%s'. Available "\
                "commands are: %s" % (command, ", ".join(all_commands))
    except CommandError, err:
        print "Error running command: %s" % err
        sys.exit(1)
    except ModelLoadError, err:
        print "Error loading the model: %s" % err
        sys.exit(1)

class CommandError(Exception):
    pass

if __name__ == "__main__":
    main()
