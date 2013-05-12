#!/usr/bin/env ./jazzshell

import sys

from optparse import OptionParser
from jazzparser.shell import ShellState, restore_shell, empty_shell
from jazzparser.parsers.loader import get_parser
    
def main():
    usage = "%prog [options] [<session-name>]"
    description = "Restores a previously saved interactive shell session. "\
        "If no session name is given, starts up the interactive shell with "\
        "an empty state. "\
        "Sessions are saved using the 'save' command from the interactive "\
        "shell after parsing"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-l", "--list", dest="list", action="store_true", help="list stored shell sessions")
    parser.add_option("-r", "--remove", dest="remove", action="store_true", help="remove a previously stored shell session")
    parser.add_option("-p", "--parser", dest="parser", action="store", help="load tools associated with the named parser")
    options, arguments = parser.parse_args()
    
    tools = []
    if options.parser:
        parser = get_parser(options.parser)
        tools.extend(parser.shell_tools)
    
    if options.list:
        # List sessions and exit
        print ", ".join(ShellState.list())
        sys.exit(0)
    
    if options.remove:
        # Delete the session and exit
        ShellState.remove(name)
        sys.exit(0)
    
    if len(arguments) < 1:
        # No shell session name: start with an empty shell state
        empty_shell(tools=tools)
    else:
        name = arguments[0]
        # Start up the shell
        restore_shell(name, tools=tools)
    
if __name__ == "__main__":
    main()
