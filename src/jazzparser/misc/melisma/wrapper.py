"""Simple wrapper for making calls to David Temperley's Melisma 2.

Requires both Melisma 1 and Melisma 2, since mftext is not included in 
Melisma 2. Since only the mxtext executable is needed, only the path to 
that need be specified.

Timings returned correspond to MIDI ticks.

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
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile
import os, re

class MelismaRunner(object):
    def __init__(self, path, mftext_path):
        self.path = path
        self.mftext_path = mftext_path
    
    def run_mftext(self, midi_file):
        command = [self.mftext_path, os.path.abspath(midi_file)]
        proc = Popen(command, stdout=PIPE, stderr=PIPE)
        proc.wait()
        if proc.returncode:
            raise MelismaError, "error running mftext: %s" % proc.stderr.read()
        return proc.stdout.read()
    
    def mftext_temp_file(self, midi_file):
        mftext_data = self.run_mftext(midi_file)
        with NamedTemporaryFile(delete=False) as mftext_file:
            mftext_file.write(mftext_data)
        return mftext_file.name
    
    def run(self, mftext_filename):
        command = [os.path.join(self.path, "polyph"), os.path.abspath(mftext_filename)]
        proc = Popen(command, stdout=PIPE, stderr=PIPE)
        proc.wait()
        # For some reason, melisma has a returncode of 1 when it succeeds, 
        #  so we can't tell if it's failed
        return MelismaResponse.from_output(proc.stdout.read())
        
    def run_midi(self, midi_filename):
        # First convert the midi data to mftext
        tmp_mftext = self.mftext_temp_file(midi_filename)
        try:
            # Run melisma on this input
            return self.run(tmp_mftext)
        finally:
            # Get rid of the tmp file
            os.remove(tmp_mftext)


class MelismaResponse(object):
    def __init__(self, beats):
        self.beats = beats
    
    @staticmethod
    def from_output(data):
        line_re = re.compile(r'^\s*(?P<time>\d+)\s+\(\s*(?P<time2>\d+)\)\s+(?P<chord>.*?)\s+(?P<metgrid>.{7})\s(?P<notes>.*)$')
        in_header = True
        beats = []
        
        for line in data.split("\n"):
            # Skip blank lines
            if line.strip():
                match = line_re.match(line)
                if match:
                    # We've matched a line: we can't be in the header now
                    in_header = False
                    parts = match.groupdict()
                    beats.append(Beat(
                            int(parts['time']),
                            parts['metgrid'].count('x'),
                            chord = parts['chord'],
                            time2 = int(parts['time2'])
                    ))
                elif not in_header:
                    # The first lines are allowed not to match the pattern: 
                    #  they're a header
                    raise MelismaError, "failed to parse melisma output on "\
                            "line: %s" % line
        return MelismaResponse(beats)
    
    def level_beats(self, level=1):
        return [b for b in self.beats if b.level <= level]

class Beat(object):
    def __init__(self, time, level, chord=None, time2=None):
        self.time = time
        self.level = level
        self.chord = chord
        self.time2 = time2

class MelismaError(Exception):
    pass
