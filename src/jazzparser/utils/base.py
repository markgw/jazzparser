"""Miscellaneous utility functions.

A load of common utilities used in various places in the codebase 
and not specific to any formalism, tagger, etc.

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

from .latex import filter_latex
import sys, traceback

def check_directory(filename, is_dir=False):
    """
    Given path to a file or directory, checks that the directory (or that 
    containing the file) exists and creates it if not. This is useful to put 
    in before you try creating or outputing to a file.
    
    @type is_dir: bool
    @param is_dir: in general, we assume the input name is a file and we 
        want to check its directory. Set is_dir=True if the input is in fact 
        a directory
    
    @return: True if the directory was created, False if it already existed.
    
    """
    import os.path
    from os import makedirs
    filename = os.path.abspath(filename)
    
    if is_dir:
        dirname = filename
    else:
        dirname = os.path.dirname(filename)
    
    if os.path.exists(dirname):
        return False
    else:
        makedirs(dirname)
        return True

def group_pairs(inlist, none_final=False, none_initial=False):
    inlist = iter(inlist)
    last = inlist.next()
    if none_initial:
        yield (None, last)
    for el in inlist:
        yield (last, el)
        last = el
    if none_final:
        yield (last, None)

def exception_tuple(str_tb=False):
    """
    Returns a tuple containing information about the currently raised 
    exception. This is (type,value,traceback).
    
    @type str_tb: bool
    @param str_tb: format the traceback as a string instead of returning 
        it as an object. You'll need to do this if you want to pickle the 
        result.
    
    """
    typ = sys.exc_type
    val = sys.exc_value
    if str_tb:
        tb = "".join(traceback.format_exception(typ, val, sys.exc_traceback))
    else:
        tb = sys.exc_traceback
    return (typ, val, tb)

def load_class(full_name):
    """
    Given the full python path to a class, imports the class 
    dynamically  and returns it.
    """
    # Split up the module name and the model class name
    module_name,__,model_name = full_name.rpartition(".")
    # Use the __import__ builtin to import the model dynamically
    module = __import__(module_name, globals(), locals(), [model_name])
    # Get the class from the module
    return getattr(module,model_name)
    
def load_optional_package(full_name, dependency_name=None, task=None):
    """
    Given the full python path to a package, imports it if possible.
    If the import fails, raises an OptionalImportError.
    This is designed for loading packages that come from optional 
    dependencies, so that a sensible error message can uniformly be 
    displayed.
    
    Only works with absolute paths, because relative paths would be 
    relative to this function's module. Relative paths are explicitly 
    disabled.
    
    @param dependency_name: a readable name for the package being loaded.
    @type dependency_name: string
    @param task: a string identifying the task you're loading it for. This 
        is for readable error output.
    @type task: string
    
    """
    try:
        module = __import__(full_name, globals(), locals(), level=0)
    except ImportError:
        error = "could not load the module %s." % full_name
        if dependency_name is not None:
            error += " You seem not to have the optional dependency %s "\
                "installed." % dependency_name
        else:
            error += " This is an optional dependency which you don't "\
                "have installed."
        if task is not None:
            error += " This package is required for %s" % task
        raise OptionalImportError, error
    return module
    
def load_from_optional_package(package_name, object_name, dependency_name=None, task=None):
    """
    Works in the same way as load_optional_package, but corresponds to 
    doing a C{from X import Y}. Note that X and Y do not correspond 
    directly to package_name and object_name, though. Part of X may 
    be found in object_name: this is so that the import of the optional 
    package can be tested before we try loading anything from it, which 
    may generate unrelated import errors, even if the optional 
    package is installed correctly.
    
    E.g. instead of doing::
     from nltk.model.ngram import NgramModel
    we would do::
     load_from_optional_package('nltk', 'model.ngram.NgramModel')
    so that we can distinguish between errors loading 'nltk' due to its 
    not being installed and errors importing 'nltk.model.ngram.NgramModel'
    due to bugs in the module, incorrect class name, etc.
    
    @param package_name: Python path to the optional package root
    @param object_name: remainder of the Python path to the object to be 
        returned.
    """
    # First try loading the optional module to check it works
    # Let errors from this get raised - they're nice and explanatory
    load_optional_package(package_name, dependency_name=dependency_name, task=task)
    # That done, we can go ahead and try the import
    from_module = package_name
    middle_bit,__,obj_name = object_name.rpartition(".")
    if middle_bit != "":
        from_module += ".%s" % middle_bit
    # Import the object we want from the optional module
    module = __import__(from_module, globals(), locals(), [obj_name], level=0)
    # Get the named object out of this imported module
    return getattr(module, obj_name)

def abstractmethod(fn, cls=None):
    """
    Decorator to make a method abstract. Just raises a 
    NotImplementedError when the method is called.
    
    """
    def _get_abstract():
        def _abstract(*args, **kwargs):
            # The method was called - raise an error
            message = "Tried to call abstract method %s" % fn.__name__
            if cls is not None:
                message += " on instance of %s" % cls.__name__
            raise NotImplementedError, message
        return _abstract
    return _get_abstract()

def comb(n, k):
    """
    Binomial coefficient: n choose k.
    
    """
    from math import factorial
    return float(factorial(n)) / (factorial(k) * factorial(n - k))

class ExecutionTimer(object):
    """
    Very simple class to wrap up a common method for measuring the 
    execution time of some code. A timer is started when the object 
    is created. Then call get_time() to find out how long its been 
    running in miliseconds.
    
    By default, this will use C{time.time()} and will therefore measure 
    wall time between starting the timer and ending. You can specify 
    C{clock=True} to report CPU clock time used by the process, using 
    C{time.clock()}. This will make a difference on Unix, but not on 
    Windows, where C{time.clock()} just returns wall time.
    
    """
    def __init__(self, clock=False):
        import time
        self.clock = clock
        if clock:
            self.start_time = time.clock()
        else:
            self.start_time = time.time()
        
    def get_time(self):
        import time
        if self.clock:
            return time.clock() - self.start_time
        else:
            return time.time() - self.start_time

class OptionalImportError(Exception):
    pass
