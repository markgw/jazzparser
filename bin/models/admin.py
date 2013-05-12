#!/usr/bin/env ../jazzshell
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

from jazzparser.taggers import TAGGERS
from jazzparser.taggers.models import ModelTagger, ModelLoadError
from jazzparser.taggers.loader import get_tagger
from jazzparser.utils.strings import group_numerical_suffixes
from jazzparser.utils.interface import boolean_input

def main():
    usage = "%prog <model-type> <command> [<command-arg> ...]"
    description = "Provides administrative operations for trained "\
                "tagger models. Use the 'help' command to get a list "\
                "of commands or command usage."
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    if len(arguments) < 2:
        print >>sys.stderr, "You must specify a model type and a command"
        sys.exit(1)
    model_type = arguments[0]
    command = arguments[1].lower()
    command_args = arguments[2:]

    if model_type not in TAGGERS:
        print >>sys.stderr, "'%s' isn't a registered model type. Check that "\
            "the name  is correct" % model_type
        sys.exit(1)
    
    tagger_cls = get_tagger(model_type)
    if not issubclass(tagger_cls, ModelTagger):
        print >>sys.stderr, "'%s' tagger cannot be modified with this script. Only model taggers can be." % (tagger_cls.__name__)
        sys.exit(1)
    model_cls = tagger_cls.MODEL_CLASS
    
    def _load_model(name):
        # Load the model from its file
        return model_cls.load_model(name)
        
    # Define behaviour for each command
    list_help = "Lists all the trained models available"
    def _list(args):
        # List the available models for the given model type
        models = model_cls.list_models()
        print "Available models for %s:" % model_cls.MODEL_TYPE
        print ", ".join(list(sorted(group_numerical_suffixes(models))))
        
    desc_help = "Outputs the descriptive text associated with the model at training time"
    def _desc(args):
        if len(args) == 0:
            raise CommandError, "desc requires a model name as an argument"
        try:
            model = _load_model(args[0])
        except ModelLoadError, err:
            # Try loading a model with 0 on the end - allows you to use 
            #  just the base name for crossval models
            try:
                model = _load_model("%s0" % args[0])
                print >>sys.stderr, "No model %s, but %s0 does exist\n" % (args[0], args[0])
            except ModelLoadError:
                print >>sys.stderr, "No model %s or %s0\n" % (args[0], args[0])
                raise err
        print "Model descriptor"
        print "================"
        print model.description
    del_help = "Deletes a model and all its associated files"
    def _del(args):
        if len(args) != 1:
            raise CommandError, "del requires a model name as an argument"
        models = model_cls.list_models()
        name_match = re.compile("^%s\d*$" % args[0])
        # Get all models that begin with this string
        matching = [m for m in models if name_match.match(m)]
        if len(matching) > 1:
            print "Multiple numbered models have this name: %s" % ", ".join(group_numerical_suffixes(matching))
            if not boolean_input("Delete all of them?"):
                if args[0] in matching:
                    print "Deleting only exact match"
                    matching = [args[0]]
                else:
                    matching = []
        elif len(matching) == 1:
            if not boolean_input("Delete model %s?" % matching[0]):
                matching = []
        
        if len(matching) == 0:
            print "No models to delete"
        else:
            for name in matching:
                model = _load_model(name)
                print "Deleting %s" % name
                model.delete()
    params_help = "Outputs the model's parameters in a human-readable format "\
            "(not available for all model types)"
    def _params(args):
        if len(args) == 0:
            raise CommandError, "params requires a model name as an argument"
        try:
            model = _load_model(args[0])
        except ModelLoadError, err:
            # Try loading a model with 0 on the end - allows you to use 
            #  just the base name for crossval models
            try:
                model = _load_model("%s0" % args[0])
                print >>sys.stderr, "No model %s, but %s0 does exist\n" % (args[0], args[0])
            except ModelLoadError:
                print >>sys.stderr, "No model %s or %s0\n" % (args[0], args[0])
                raise err
        try:
            params = getattr(model, "readable_parameters")
        except AttributeError:
            print "Model type %s does not provide a readable form of its "\
                    "parameters" % model_type
            sys.exit(1)
        else:
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
