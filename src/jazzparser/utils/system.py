"""Utilities relating to the system the software is running on.

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

import platform
import subprocess

def set_proc_title(title):
    """
    Tries to set the current process title. This is very system-dependent 
    and may fail in many cases.
    
    @return: True if the process succeeds, False if there's an error
    
    """
    try:
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        retcode = libc.prctl(15, '%s\0' % title, 0, 0, 0)
        if retcode:
            return False
    except:
        return False
    else:
        return True

def get_host_info_string():
    """
    Returns a string containing information to identify the system on which 
    you're currently running. This is useful to logging info. Don't try 
    matching against it - you'll be better off getting the components 
    separately.
    
    """
    import socket, os
    
    # This should usually give the system's hostname
    hostname = socket.gethostname()
    # In case this doesn't give a good answer, we also get all the uname info
    #  (we might want to know something more about the system anyway)
    uname = ", ".join(os.uname())
    return "%s (%s)" % (hostname, uname)

def open_file(filename):
    """
    Tries to use a system-recommended application to open the given file.
    Uses C{xdg-open} on Linux, C{start} on Windows and C{open} 
    on Mac.
    
    """
    if is_windows():
        cmd = "start"
    elif is_mac():
        cmd = "open"
    else:
        # Otherwise assume linux
        cmd = "xdg-open"
    # Run the command
    subprocess.call([cmd, filename])

def is_windows():
    return platform.system().lower() == 'windows'
def is_mac():
    return platform.system().lower() == 'darwin'
def is_linux():
    return platform.system().lower() == 'linux'
