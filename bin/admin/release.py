#!../jazzshell
from __future__ import absolute_import
"""Prepare codebase for release.

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

import sys, os, tarfile
from optparse import OptionParser
from fnmatch import fnmatch
from shutil import rmtree, copy2
from subprocess import call
from datetime import datetime

from jazzparser.settings import PROJECT_ROOT, RELEASE_BUILD_DIR, \
                                CURRENT_VERSION

EXCLUDE_FILES = [
    # The version of the database that the annotator stores has information 
    #  in it we wish to exclude from the release
    'annotator/annotator/sequences.db',
    # Exclude local and temporary files
    'etc/local/*',
    'etc/log/*',
    'etc/tmp/*',
    'etc/shell_state/*',
    # Don't distribute C&C with our parser
    'lib/candc/*',
    # No need to distribute Melisma either
    'lib/melisma/*', 
    # These are results from CMJ experiments
    # They take up a lot of space, because I was storing all parses back then
    'etc/output/cmj',
    # These were the original downloaded midi files and aren't really needed
    'input/midi/*.tar.gz',
    # Don't include the documentation
    # This gets uploaded to the website and makes the tarball too big
    'doc',
    # Exclude the directory that this script (and other admin tools) are in
    'bin/admin',
    # No need to include all the experimental results
    # I can make these available separately if I want
    'etc/output/*',
    # No entirely sure whether I'm entitled to release these and they're no 
    #  important to my project really
    'input/corpora',
    # Importantly, any identification of the songs in the chord sequence 
    #  corpus by name must be excluded
    'input/fullseqs_names.txt',
    'input/fullseqs_named',
]
REMOVE_PATTERNS = [
    # Remove .pyc files
    '*.pyc',
    # Remove all subversion directories
    '.svn',
]

def main():
    parser = OptionParser(description="Prepare codebase for release and "\
        "make a tarball")
    parser.add_option("-d", "--doc", dest="doc", action="store_true", help="rebuild the documentation and upload it")
    parser.add_option("-a", "--annotator", dest="annotator", action="store_true", help="include the annotator in the tarball. Left out by default")
    options, arguments = parser.parse_args()
    
    if not options.annotator:
        EXCLUDE_FILES.append('annotator')
    
    PATH_SKIP_PATTERNS = [
        os.path.join(PROJECT_ROOT, filename) for filename in EXCLUDE_FILES
    ]
    
    print "Building release %s" % CURRENT_VERSION
    
    # Prepare some things before we start copying files
    if options.doc:
        # Compile the API documentation
        makedoc_cmd = os.path.join(PROJECT_ROOT, "bin", "admin", "makedoc")
        print "Building API documentation\n"
        call(makedoc_cmd, shell=True)
        # Upload the documentation
        updoc_cmd = os.path.join(PROJECT_ROOT, "bin", "admin", "updoc")
        print "Uploading API documentation\n"
        call(updoc_cmd, shell=True)
    
    temp_build_dir = os.path.join(RELEASE_BUILD_DIR, "jazzparser")
    
    # Clear the build dir
    print "\nClearing old build"
    rmtree(temp_build_dir, ignore_errors=True)
    os.makedirs(temp_build_dir)
    
    walk = os.walk(PROJECT_ROOT, topdown=True)
    print "Copying all files..."
    # Filter the list of files to include in the release directories
    for root, dirs, files in walk:
        remove_dirs = []
        remove_files = []
        # Check dir names and filenames for patterns we should skip
        for dirname in dirs:
            for pattern in REMOVE_PATTERNS:
                if fnmatch(dirname, pattern):
                    remove_dirs.append(dirname)
        for filename in files:
            for pattern in REMOVE_PATTERNS:
                if fnmatch(filename, pattern):
                    remove_files.append(filename)
        # These patterns are on the full path
        for dirname in dirs:
            full_path = os.path.join(root, dirname)
            for pattern in PATH_SKIP_PATTERNS:
                if fnmatch(full_path, pattern):
                    remove_dirs.append(dirname)
        for filename in files:
            full_path = os.path.join(root, filename)
            for pattern in PATH_SKIP_PATTERNS:
                if fnmatch(full_path, pattern):
                    remove_files.append(filename)
        # Remove the dirs and files we're skipping
        for remove_dir in set(remove_dirs):
            dirs.remove(remove_dir)
        for remove_file in set(remove_files):
            files.remove(remove_file)
        
        # Get the root dir relative to the project root
        rel_root = os.path.relpath(root, PROJECT_ROOT)
        if rel_root == ".":
            rel_root = ""
        
        # Create all directories as necessary
        for dirname in dirs:
            release_dirname = os.path.join(
                                os.path.abspath(temp_build_dir), 
                                    rel_root, dirname)
            os.mkdir(release_dirname)
        # Copy all the files
        for filename in files:
            copy2(os.path.join(root, filename), 
                  os.path.join(temp_build_dir, rel_root, filename))
    
    # Create a file with release information
    with open(os.path.join(temp_build_dir, "RELEASE"), 'w') as release_file:
        print >>release_file, """\
===================
= The Jazz Parser =
===================

Release version %s
Released %s
"""         % (CURRENT_VERSION, datetime.now().strftime("%e-%m-%Y"))
    
    print "Building tarball..."
    if options.annotator:
        ball_name = "jazzparser-annotator"
    else:
        ball_name = "jazzparser"
    ball_filename = "%s-%s.tar.gz" % (ball_name, CURRENT_VERSION)
    tarfile_path = os.path.join(RELEASE_BUILD_DIR, ball_filename)
    with tarfile.open(tarfile_path, 'w:gz') as tar:
        tar.add(temp_build_dir, arcname="jazzparser", recursive=True)
    # Remove the uncompressed directories
    rmtree(temp_build_dir)
    
    print "\nTarball for release written to %s" % tarfile_path
    # Output the latest version name, so the latest alias can redirect
    latest_path = os.path.join(RELEASE_BUILD_DIR, "LATEST")
    with open(latest_path, 'w') as latest_file:
        print >>latest_file, CURRENT_VERSION
    # Upload the files
    print "Uploading tarball"
    call("scp %s %s markwild@granroth-wilding.co.uk:~/www/jazzparser/code/" % \
            (tarfile_path, latest_path), shell=True)
    os.remove(latest_path)
    
if __name__ == "__main__":
    main()
