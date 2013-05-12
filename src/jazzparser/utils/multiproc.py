"""Multiprocessing utilities.
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

from multiprocessing import TimeoutError
from threading import Thread

class Result(object):
    def __init__(self):
        self.result = None

def timeout(fun, *args, **kwargs):
    """
    Decorator that applies a function with the given args and kwargs, 
    enforcing a timeout. Blocks until the function completes or the 
    timeout expires. If the timeout expires, raises a TimeoutError.
    
    The intended use of this is to submit a job to a multiprocessing 
    pool with a timeout, after which the whole processing terminates.
    This only makes sense if you have just one task per process or 
    set C{maxtasksperchild=1} on the pool.
    
    @note: the function execution does not actually halt when the 
    exception is raised, but continues in another thread. There is 
    no way to terminate this thread from outside it.
    
    """
    result = Result()
    timeout_length = kwargs.pop('timeout', 60)
    def _get_target():
        # Closure to capture result
        def _target(*args, **kwargs):
            result.result = fun(*args, **kwargs)
        return _target
    
    # Run the function in a thread
    runner = Thread(target=_get_target(), args=args, kwargs=kwargs)
    # Wait until it finishes or the timeout expires
    runner.start()
    runner.join(timeout_length)
    if runner.is_alive():
        # The function timed out
        raise TimeoutError, "call to %s timed out (%s secs)" % (fun,timeout_length)
    else:
        return result.result
