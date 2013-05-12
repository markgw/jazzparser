"""Initialization of the logging system.

An application that calls methods that use logging should first call 
init_logging, or else the logging messages will all get lost.

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

import logging

def init_logging(log_level=None):
    """
    Set up a logger to output test/error messages
    """
    # Get a logger to configure from the logging system: 
    #  will get the same one when logging later.
    logger = logging.getLogger("main_logger")
    if log_level is not None:
        logger.setLevel(log_level)
    
    # Create a console handler to output message to the console
    chandler = logging.StreamHandler()
    chandler.setLevel(logging.DEBUG)
    # Format the logging messages thusly
    format = "%(levelname)s: %(message)s"
    formatter = logging.Formatter(format)
    chandler.setFormatter(formatter)
    
    # Add the console handler to the logger
    logger.addHandler(chandler)
    # Maybe add a file handler to the logger

def create_logger(log_level=None, name=None, stdout=False, filename=None, stderr=False):
    """
    Set up a logger to log to a file.
    
    @type filename: string
    @param filename: the file to write the logs to. If None, doesn't add a 
        handler for file output.
    @param log_level: one of the level constants in L{logging}; the log level 
        to give the logger. Defaults to B{INFO}.
    @type name: string
    @param name: name to give to the logger. By default, uses the filename. If 
        neither is given, raises an exception.
    @type stdout: bool
    @param stdout: if True, also adds a handler to output to stdout
    
    @return: the Logger instance created
    
    """
    import sys
    from jazzparser.utils.base import check_directory
    
    if name is None:
        if filename is None:
            raise ValueError, "neither a name nor a filename was given for the "\
                "logger"
        name = filename
    
    # Create the logger
    logger = logging.getLogger(name)
    
    # Set the log level, or leave it as the default
    if log_level is None:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(log_level)
        
    formatter = logging.Formatter("%(levelname)s %(asctime)s: %(message)s",
                                    "%Y-%m-%d %H:%M:%S")
    
    if filename is not None:
        # Make sure the containing directory exists
        check_directory(filename)
        # Create a file handler
        fhandler = logging.FileHandler(filename, 'a')
        fhandler.setLevel(logging.DEBUG)
        fhandler.setFormatter(formatter)
        # Use this handler
        logger.addHandler(fhandler)
    
    if stderr:
        shandler = logging.StreamHandler()
        shandler.setLevel(logging.DEBUG)
        shandler.setFormatter(formatter)
        logger.addHandler(shandler)
        
    if stdout:
        sohandler = logging.StreamHandler(sys.stdout)
        sohandler.setLevel(logging.DEBUG)
        sohandler.setFormatter(formatter)
        logger.addHandler(sohandler)
    
    return logger

def create_dummy_logger():
    """
    Creates a new logger that won't ever output anything.
    
    """
    logger = logging.getLogger("dummy")
    if len(logger.handlers) == 0:
        logger.addHandler(NullHandler())
    return logger

global _logger_id
_logger_id = 0

def create_plain_stderr_logger(log_level=None, stdout=False):
    """
    Creates a new logging that just outputs the messages to stderr, with no 
    extra logging information. The log level will be set to debug by default, 
    so logging anything to this logger is just the same as writing to stderr.
    
    If you call this more than once, a different logger will be returned.
    
    @type stdout: bool
    @param stdout: if True, uses stdout instead of stderr
    
    """
    global _logger_id
    if stdout:
        logger = logging.getLogger("_stdout_logger_%d" % _logger_id)
    else:
        logger = logging.getLogger("_stderr_logger_%d" % _logger_id)
    _logger_id += 1
    
    if log_level is None:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(log_level)
        
    # If this has been initialized before, remove all handlers and create a new one
    if len(logger.handlers) > 0:
        for h in logger.handlers:
            logger.removeHandler(h)
    
    if stdout:
        import sys
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.StreamHandler()
    fmt = logging.Formatter("%(message)s")
    handler.setFormatter(fmt)
    
    logger.addHandler(handler)
    return logger


class NullHandler(logging.Handler):
    """
    A handler that drops all the logs.
    
    This in the library for Python 3.1, but needs to be manually defined in 
    earlier versions.
    
    """
    def emit(self, record):
        pass
