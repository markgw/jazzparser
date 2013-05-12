"""File I/O classes for the harmonical

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

import wave, os.path

DEFAULT_SAMPLE_RATE = 44100

class SoundFile(object):
    """
    A wave file to store uncompressed audio signal data.
    """
    def  __init__(self, filename="audio.wav", sample_rate=DEFAULT_SAMPLE_RATE):
        self.filename = filename
        self._signal = []
        self.sr = sample_rate

    def save(self):
        file = wave.open(self.filename, 'wb')
        # Convert the numerical data into a binary string
        str_signal = self.get_data()

        file.setparams((1, 2, self.sr, self.sr*4, 'NONE', 'noncompressed'))
        file.writeframes(str_signal)
        file.close()
    
    def set_signal(self, signal):
        self._signal = signal
        
    def add_signal(self, signal):
        self._signal.extend(signal)
        
    def add_silence(self, seconds=1.0):
        self.add_signal([0]*int(self.sr*seconds))
        
    def get_data(self):
        """
        Return the raw data that will be written to the file.
        
        """
        return ''.join([wave.struct.pack('h', samp) for samp in self._signal])
        
    def get_buffer(self):
        """
        Returns a file-like object containing the data that would be 
        written to the file. This object won't get updated if the 
        SoundFile is changed.
        
        """
        from StringIO import StringIO
        return StringIO(self.get_data())

def save_wave_data(signal, filename):
    """
    Shortcut to store a wave file given some sample data.
    Assumes the standard sample rate.
    
    """
    filename = os.path.abspath(filename)
    f = SoundFile(filename)
    f.set_signal(signal)
    f.save()

