"""Audio output for the harmonical.

Routines for preparing and using audio output. These rely on PyGame, 
which is an optional dependency.

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

from jazzparser.utils.base import load_from_optional_package, \
            load_optional_package
from jazzparser.harmonical.files import SoundFile
from StringIO import StringIO
import wave

def check_pygame():
    """
    Checks that PyGame can be imported and outputs an error if not.
    
    """
    load_optional_package('pygame', 'PyGame', "outputing audio")
    
def init_mixer():
    """
    Check that the mixer's initialized and initialize it if not.
    
    """
    # Check PyGame is available
    # This will raise an error if it's not
    check_pygame()
    from pygame import init, mixer
    # Set the mixer settings before initializing everything
    mixer.pre_init(frequency=44100)
    init()
    
def play_audio(samples, wait_for_end=False):
    """
    Uses PyGame to play the audio samples given as a list of samples.
    
    """
    init_mixer()
    from pygame.mixer import music
    from pygame.sndarray import make_sound
    from pygame import USEREVENT, event
    import numpy
    
    # Prepare the wave data to play
    # Make it stereo and the right number format
    smp_array = numpy.array(zip(samples,samples)).astype(numpy.int16)
    
    # Generate the sound object from the sample array
    snd = make_sound(smp_array)
    # Set it playing
    channel = snd.play()
    # Set an event to be triggered when the music ends, so we can 
    #  wait for it if necessary
    channel.set_endevent(USEREVENT)
    
    if wait_for_end:
        # Wait until the music finishes
        event.wait()
