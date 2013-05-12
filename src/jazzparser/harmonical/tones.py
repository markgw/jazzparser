"""Tone generation tools.

This is the tone representation and rendering engine for the Harmonical.
The Harmonical is an instrument that can play music in any tuning 
system, including just intonation, by allowing the music to specify 
a precise pitch for each note.
Its name is that given by Helmholtz to his specially tuned harmonium 
that allowed him to experiment with just tuning systems.

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

import numpy
import math, logging
from .files import DEFAULT_SAMPLE_RATE, save_wave_data
from . import CHORD_TYPES
from jazzparser.data import Fraction
from jazzparser.utils.base import group_pairs
from jazzparser.utils.tonalspace import coordinate_to_et, \
                    coordinate_to_et_2d, tonal_space_pitch, tonal_space_pitch_2d, \
                    tonal_space_et_pitch

MAX_SAMPLE = 32767

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class ToneMatrix(object):
    """
    A timesheet of tones, with pitches, onset times and durations, 
    designed for specifying input to the tone generator. This allows 
    music to be generated using precise pitches, rather than equal
    temperament note values, as with MIDI or something similar.
    Time values are discretized according to the sample rate.
    
    """
    def __init__(self, sample_rate=DEFAULT_SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._events = {}
        
    def add_tone(self, time, event):
        self._events.setdefault(int(time*self.sample_rate), []).append(event)
        
    def render(self):
        """
        Renders the wave and returns a list of samples.
        
        """
        samples = []
        def _add_samples(new_samples, offset):
            # Pad out until we reach the start time
            while len(samples) < offset:
                samples.append(0.0)
            for intime in range(len(new_samples)):
                cursor = offset + intime
                if len(samples) <= cursor:
                    # We've not added any samples at this time yet
                    samples.append(new_samples[intime])
                else:
                    # This timestep already has a sample in it - just add
                    samples[cursor] += new_samples[intime]
        for time in sorted(self._events.keys()):
            # Get the samples for the given tones
            for tone in self._events[time]:
                tone_samples = tone.get_samples(self.sample_rate)
                # Add them to the global matrix
                _add_samples(tone_samples, time)
        # This mustn't go over the max sample, so we normalize to 1.0
        # If you want a different volume, renormalize afterwards
        samples = normalize(samples, level=1.0)
        return samples
        
class BaseToneEvent(object):
    """
    A single event in the tone matrix. This is an abstract class to 
    define the interface for tone events.
    
    """
    def get_samples(self, sample_rate=DEFAULT_SAMPLE_RATE):
        """
        This should return a list of samples for the event's whole 
        duration at the given sample rate.
        
        """
        raise NotImplementedError
        
class SineToneEvent(BaseToneEvent):
    """
    A single event in the tone matrix.
    
    """
    def __init__(self, frequency, duration=1, amplitude=0.8, envelope=None):
        self.frequency = frequency
        self.duration = duration
        self.amplitude = amplitude
        self.envelope = envelope
    
    def get_samples(self, sample_rate=DEFAULT_SAMPLE_RATE):
        """
        Generates samples from a sine wave.
        """
        wave = generate_sine_wave(self.frequency, self.duration, self.amplitude, sample_rate)
        if self.envelope is not None:
            # Apply an envelope to shape the wave
            wave = apply_envelope(wave, self.envelope)
        return wave

class MultiSineToneEvent(BaseToneEvent):
    """
    Generates a tone by summing several sine waves (simple additive 
    synthesis).
    The tones are given as a list of (frequency,amplitude) pairs.
    
    The result is normalized to the given amplitude, so absolute 
    scaling of the individual amplitudes makes no difference.
    
    """
    def __init__(self, duration=1, amplitude=0.8, envelope=None, tones=[]):
        self.duration = duration
        self.amplitude = amplitude
        self.envelope = envelope
        self.tones = tones
        
    def get_samples(self, sample_rate=DEFAULT_SAMPLE_RATE):
        waves = []
        for frequency,amplitude in self.tones:
            waves.append(generate_sine_wave(frequency, self.duration, amplitude, sample_rate))
        wave = sum_signals(waves, norm=self.amplitude)
        # Apply an envelope to the final wave
        if self.envelope is not None:
            wave = apply_envelope(wave, self.envelope)
        return wave
        
class SineClusterEvent(MultiSineToneEvent):
    """
    Generates a tone by summing the notes of a tonal space cluster.
    
    """
    def __init__(self, frequency, points, duration=1, \
            amplitude=0.8, envelope=None, root_weight=1.2, root_octave=0, \
            double_root=False, equal_temperament=False):
        """
        @type root_weight: float
        @param root_weight: amplitude ratio between the root note and 
            any other note. Set >1.0 to make the root louder than 
            other notes.
        @type root_octave: int
        @param root_octave: octave to transpose the root to relative 
            to other notes. Default (0) has the other notes in the 
            octave above the root.
        @type double_root: bool
        @param double_root: if True, an extra tone will be added an 
            octave below the root
        
        @see: L{MultiSineToneEvent}
        
        """
        tones = []
        
        if equal_temperament:
            _pitch_ratio = tonal_space_et_pitch
        else:
            _pitch_ratio = tonal_space_pitch
            
        for x,y,z in points:
            if x==0 and y==0:
                tones.append((frequency*(2**(z+root_octave)), 1.0))
                if double_root:
                    tones.append((frequency*(2**(z+root_octave-1)), 1.0/8.0))
            else:
                tones.append(
                        (frequency*_pitch_ratio((x,y,z)),
                         1.0/root_weight))
        super(SineClusterEvent, self).__init__(duration=duration, 
                                             amplitude=amplitude,
                                             envelope=envelope,
                                             tones=tones)
        
class SineChordEvent(SineClusterEvent):
    """
    Generates a tone by summing the notes of a chord of a standard 
    type.
    
    """
    
    def __init__(self, frequency, chord_type='', *args, **kwargs):
        """
        @see: L{SineClusterEvent}
        
        """
        if chord_type in CHORD_TYPES:
            ts_notes = CHORD_TYPES[chord_type]
        else:
            logger.warn("harmonical could not find realisation for chord "\
                "type '%s'. Using plain major instead." % chord_type)
            ts_notes = CHORD_TYPES['']
        
        super(SineChordEvent, self).__init__(frequency, ts_notes, *args, **kwargs)

def generate_sine_wave(frequency, duration, amplitude, sample_rate):
    samples = duration*sample_rate
    period = sample_rate / float(frequency) # in sample points
    omega = numpy.pi * 2 / period
    
    # A x values to serve as input to the sin wave
    xaxis = numpy.arange(samples, dtype = numpy.float) * omega
    # Run this through the sin function to get a sine wave
    wave = MAX_SAMPLE * numpy.sin(xaxis) * amplitude
    return wave
    
def apply_envelope(wave, envelope):
    return [s * envelope[i*len(envelope)/len(wave)] for i,s in enumerate(wave)]
        
def sum_signals(sigs, norm=1.0):
    """
    Sum two wave signals.
    
    """
    wave = normalize([sum(samps) for samps in zip(*sigs)], level=norm)
    return wave
    
def normalize(wave, level=0.8):
    """
    Normalize the amplitude of the wave data.
    
    """
    if len(wave) == 0:
        return wave
    # This should be the amplitude of the highest sample
    targ_max = level * MAX_SAMPLE
    current_max = max(max(wave), -1*min(wave))
    wave = [s*targ_max/current_max for s in wave]
    return wave
    
######################### Envelopes #############################
def fade_in_out_envelope(precision=200, hold_ratio=10):
    """
    Generates an envelope that fades in linearly, holds for a time 
    adjusted by hold_ratio, then fades out linearly.
    
    """
    return [1.0*i/precision for i in range(precision)] + \
           [1.0]*(precision*hold_ratio) + \
           [1.0*(precision-i)/precision for i in range(precision)]
def smooth_fade_in_out_envelope(precision=200, hold_ratio=10):
    """
    Generates an envelope that fades in with a log curve, holds for a time 
    adjusted by hold_ratio, then fades out similarly.
    
    """
    sq_prec = precision**2
    return [1.0*(i+1)**2/sq_prec for i in range(precision)] + \
           [1.0]*(precision*hold_ratio) + \
           [1.0*(1.0-float(i+1)**2/sq_prec) for i in range(precision)]
           
def fade_in_envelope(precision=200, hold_ratio=10):
    return [1.0*i/precision for i in range(precision)] + \
           [1.0]*(precision*hold_ratio)
def fade_out_envelope(precision=200, hold_ratio=10):
    return [1.0]*(precision*hold_ratio) + \
           [1.0*(precision-i)/precision for i in range(precision)]
def adsr_envelope(attack_time, decay_time, sustain_time, release_time, sustain_level=0.6, sustain_level_end=0.4, pause_time=0):
    """
    Create an envelope according to ADSR (attack-decay-sustain-release) 
    specifications. Unlike real ADSR, the timings are all proportional. 
    Attack, decay and release should be absolute, and sustain shouldn't 
    have a time, but this kind of envelope can't do that.
    
    """
    return [1.0*i/attack_time for i in range(attack_time)] + \
           [1.0-(1.0-sustain_level)*i/decay_time for i in range(decay_time)] + \
           [sustain_level-(sustain_level-sustain_level_end)*i/sustain_time for i in range(sustain_time)] + \
           [sustain_level_end*(1-float(i)/release_time) for i in range(release_time)] + \
           [0.0] * pause_time
def piano_envelope():
    """
    Produces an envelope designed to sound a tiny bit like a piano.
    Don't expect too much of it!
    
    """
    attack = 50
    decay = 200
    sustain = 5000
    release = 400
    sus_level = 0.4
    sus_end_level = 0.2
    return adsr_envelope(attack, decay, sustain, release, sus_level, sus_end_level, pause_time=50)

def no_envelope():
    return None
# Dictionary of envelopes, so we can access them by name
ENVELOPES = {
    'piano' : piano_envelope,
    'in' : fade_in_envelope,
    'out' : fade_out_envelope,
    'inout' : fade_in_out_envelope,
    'smooth' : smooth_fade_in_out_envelope,
    'square' : no_envelope,
}
    
#################################################################

def path_to_tones(path, tempo=120, chord_types=None, root_octave=0, 
        double_root=False, equal_temperament=False, timings=False):
    """
    Takes a tonal space path, given as a list of coordinates, and 
    generates the tones of the roots.
    
    @type path: list of (3d-coordinate,length) tuples
    @param path: coordinates of the points in the sequence and the length 
        of each, in beats
    @type tempo: int
    @param tempo: speed in beats per second (Maelzel's metronome)
    @type chord_types: list of (string,length)
    @param chord_types: the type of chord to use for each tone and the 
        time spent on that chord type, in beats. See 
        L{CHORD_TYPES} keys for possible values.
    @type equal_temperament: bool
    @param equal_temperament: render all the pitches as they would be 
        played in equal temperament.
    @rtype: L{ToneMatrix}
    @return: a tone matrix that can be used to render the sound
    
    """
    # Use this envelope for all notes
    envelope = piano_envelope()
    
    sample_rate = DEFAULT_SAMPLE_RATE
    
    beat_length = 60.0 / tempo
    if timings:
        root_times = path
    else:
        # Work out when each root change occurs
        time = Fraction(0)
        root_times = []
        for root,length in path:
            root_times.append((root,time))
            time += length
    def _root_at_time(time):
        current_root = root_times[0][0]
        for root,rtime in root_times[1:]:
            # Move through root until we get the first one that 
            #  occurs after the previous time
            if rtime > time:
                return current_root
            current_root = root
        # If we're beyond the time of the last root, use that one
        return current_root
    
    if chord_types is None:
        # Default to just pure tones
        chord_types = [('prime',length) for __,length in path]
        
    if equal_temperament:
        _pitch_ratio = tonal_space_et_pitch
    else:
        _pitch_ratio = tonal_space_pitch_2d
    
    # Build the tone matrix by adding the tones one by one
    matrix = ToneMatrix(sample_rate=sample_rate)
    time = Fraction(0)
    for ctype,length in chord_types:
        coord = _root_at_time(time)
        pitch_ratio = _pitch_ratio(coord)
        duration = beat_length * float(length)
        # We want all enharmonic equivs of I to come out close to I, 
        #  not an octave above
        if not equal_temperament and coordinate_to_et_2d(coord) == 0 \
                and pitch_ratio > 1.5:
            pitch_ratio /= 2.0
        # Use a sine tone for each note
        tone = SineChordEvent(220*pitch_ratio, chord_type=ctype, duration=duration, envelope=envelope, root_octave=root_octave, root_weight=1.2, double_root=double_root)
        matrix.add_tone(beat_length * float(time), tone)
        time += length
    return matrix

def render_path_to_file(filename, path, *args, **kwargs):
    """
    Convenience function that takes a path and set of timings and 
    uses the harmonical to render audio from it and writes it to a 
    file.
    Additional args/kwargs are passed to the L{path_to_tones} function.
    
    """
    tones = path_to_tones(path, *args, **kwargs)
    # Generate the audio samples
    samples = tones.render()
    # Output to a wave file
    save_wave_data(samples, filename)
