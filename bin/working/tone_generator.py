from jazzparser.harmonical.tones import *
from jazzparser.harmonical.files import SoundFile
from numpy.fft import fft
import math

# Generate some waves
f0 = 528 # Middle C
harm = lambda i: f0*(i+1)
file = SoundFile('test.wav')
env = fade_in_out_envelope()
qenv = fade_in_out_envelope(hold_ratio=100)

if False:
    # Build a complex tone out of several harmonics
    dur = 2
    
    sig = MultiSineToneEvent(duration=dur, amplitude=0.8, envelope=env, tones=[ 
            (f0, 1.0),
            (harm(1), 0.5),
            (harm(2), 0.75),
            (harm(3), 0.6)
        ]).get_samples()
    sig = normalize(sig)
    file.add_signal(sig)
    file.add_silence(0.5)

if False:
    # Play a scale of pure tones
    dur = 0.5
    freq=f0
    for i in range(12):
        sig = SineToneEvent(frequency=freq, envelope=env, duration=dur).get_samples()
        file.add_signal(sig)
        freq *= et_semitone
    file.add_silence(0.5)

if False:
    dur = 1.5
    # Play a pure tone, followed by the fifth, then the ET fifth
    file.add_signal( SineToneEvent(frequency=f0, envelope=env, duration=dur).get_samples() )
    file.add_signal( SineToneEvent(frequency=f0*math.pow(et_semitone,7), envelope=env, duration=dur).get_samples() )
    file.add_signal( SineToneEvent(frequency=f0*3/2, envelope=env, duration=dur).get_samples() )
    file.add_silence(0.5)

if False:
    dur = 2.5
    env = fade_in_out_envelope(hold_ratio=100)
    # Play around with thirds
    ## Just the fundamental
    file.add_signal( SineToneEvent(frequency=f0, envelope=env, duration=dur).get_samples() )
    ## The third
    file.add_signal( SineToneEvent(frequency=f0*5/4, envelope=env, duration=dur).get_samples() )
    ## ET third
    file.add_signal( SineToneEvent(frequency=f0*math.pow(et_semitone,4), envelope=env, duration=dur).get_samples() )
    file.add_silence(0.5)
    ## Fundamental + third
    file.add_signal( MultiSineToneEvent(duration=3, envelope=env, amplitude=0.8, tones=[
            (f0, 1.0),
            (f0*5/4, 1.0)
        ]).get_samples() )
    file.add_silence(0.5)
    ## Fundamental + ET third
    file.add_signal( MultiSineToneEvent(duration=3.5, envelope=env, amplitude=0.8, tones=[
            (f0, 1.0),
            (f0*math.pow(et_semitone,4), 1.0)
        ]).get_samples() )
    file.add_silence(1.0)
    ## ET against natural
    file.add_signal( MultiSineToneEvent(duration=3.5, envelope=env, amplitude=0.8, tones=[
            (f0, 1.0),
            (f0*5/4, 1.0),
            (f0*math.pow(et_semitone,4), 1.0)
        ]).get_samples() )
    file.add_silence(0.5)
    
if False:
    ## Fundamental + ET third
    file.add_signal( MultiSineToneEvent(duration=4, envelope=fade_in_envelope(hold_ratio=100), amplitude=0.8, tones=[
            (f0, 1.),
            (f0*5/4, 1.0)
        ]).get_samples() )
    file.add_silence(0.1)
    file.add_signal( MultiSineToneEvent(duration=4, amplitude=0.8, tones=[
            (f0, 1.0),
            (f0*math.pow(et_semitone,4), 1.0)
        ]).get_samples() )
    file.add_silence(0.1)
    file.add_signal( MultiSineToneEvent(duration=4, envelope=fade_out_envelope(hold_ratio=100), amplitude=0.8, tones=[
            (f0, 1.0),
            (f0*5/4, 1.0),
            (f0*math.pow(et_semitone,4), 1.0)
        ]).get_samples() )
    file.add_silence(0.5)
    # Chords
    file.add_signal( MultiSineToneEvent(duration=4, envelope=fade_in_out_envelope(hold_ratio=100), amplitude=0.8, tones=[
            (f0, 1.0),
            (f0*5/4, 1.0),
            (f0*3/2, 1.0)
        ]).get_samples() )
    file.add_signal( MultiSineToneEvent(duration=4, envelope=fade_in_out_envelope(hold_ratio=100), amplitude=0.8, tones=[
            (f0, 1.5),
            (f0*math.pow(et_semitone, 4), 1.0),
            (f0*math.pow(et_semitone, 7), 1.0)
        ]).get_samples() )
    file.add_silence(1.0)
    
if False:
    # Generate a scale correctly tune in just intonation
    tonic = f0/2
    freqs = [
        tonic,     # I
        tonic*9/8, # II
        tonic*5/4, # III
        tonic*4/3, # IV
        tonic*3/2, # V
        tonic*5/3, # VI
        tonic*15/8,# VII
        tonic*2    # I'
    ]
    mat = ToneMatrix()
    mat.add_tone(1, SineToneEvent(frequency=tonic, envelope=fade_in_out_envelope(hold_ratio=100), duration=7) ) 
    for i,f in enumerate(freqs):
        mat.add_tone(i, SineToneEvent(frequency=f, envelope=fade_in_out_envelope(hold_ratio=100), duration=1) )
    file.add_signal(mat.render())
    file.add_silence(1.0)
if True:
    # Do the same for ET
    tonic = f0/2
    mat2 = ToneMatrix()
    mat2.add_tone(1, SineToneEvent(frequency=tonic, envelope=fade_in_out_envelope(hold_ratio=100), duration=7) ) 
    notes = [0,2,4,5,7,9,11,12]
    for i,st in enumerate(notes):
        mat2.add_tone(i, SineToneEvent(frequency=tonic*et_interval(st), envelope=fade_in_out_envelope(hold_ratio=100), duration=1) )
    file.add_signal(mat2.render())
    file.add_silence(1.0)
    
if False:
    # Just testing the tone matrix
    test_mat = ToneMatrix()
    test_mat.add_tone(0, SineToneEvent(frequency=f0, duration=10))
    test_mat.add_tone(2, SineToneEvent(frequency=f0*3/2, duration=8))
    test_mat.add_tone(4, SineToneEvent(frequency=f0*5/4, duration=6))
    file.add_signal(normalize(test_mat.render(), 0.4))
    
if False:
    dur=2
    # Play the notorious wolf tone of JI
    mat = ToneMatrix()
    # Prime
    mat.add_tone(0, SineToneEvent(frequency=f0, envelope=env, duration=3*dur))
    # VI
    mat.add_tone(1*dur, SineToneEvent(frequency=f0*5/3, envelope=env, duration=1*dur))
    # II
    mat.add_tone(2*dur, SineToneEvent(frequency=f0*9/8, envelope=env, duration=1*dur))
    # II with its V
    mat.add_tone(3*dur, SineToneEvent(frequency=f0*9/8, envelope=env, duration=5*dur))
    mat.add_tone(4*dur, SineToneEvent(frequency=f0*27/16, envelope=env, duration=4*dur))
    # II with VI
    mat.add_tone(8*dur, SineToneEvent(frequency=f0*9/8, envelope=env, duration=5*dur))
    mat.add_tone(9*dur, SineToneEvent(frequency=f0*5/3, envelope=env, duration=4*dur))
    file.add_signal(mat.render())
    
if False:
    # Play the harmonic series
    dur = 2
    low_f0 = f0 / 2
    for i in range(1, 15):
        file.add_signal( SineToneEvent(frequency=i*low_f0, duration=dur, envelope=qenv).get_samples() )
        file.add_silence(1)
        
if False:
    # Dominant 7th chord versus major m7 chord
    file.add_signal( MultiSineToneEvent(duration=3, envelope=qenv, tones=[
            (f0, 1.0),
            (f0*3/2, 1.0),
            (f0*5/4, 1.0)
        ]).get_samples() )
    file.add_silence(0.5)
    file.add_signal( MultiSineToneEvent(duration=3, envelope=qenv, tones=[
            (f0, 1.0),
            (f0*3/2, 1.0),
            (f0*5/4, 1.0),
            (f0*9/5, 1.0)
        ]).get_samples() )
    file.add_silence(0.5)
    file.add_signal( MultiSineToneEvent(duration=3, envelope=qenv, tones=[
            (f0, 1.0),
            (f0*3/2, 1.0),
            (f0*5/4, 1.0),
            (f0*16/9, 1.0)
        ]).get_samples() )
    file.add_silence(1)
    
if False:
    # Play the three major chords
    dur = 1
    def _major_chord(prime):
        mat = ToneMatrix()
        mat.add_tone(0, SineToneEvent(frequency=prime, envelope=qenv, duration=dur*4))
        mat.add_tone(dur, SineToneEvent(frequency=prime*5/4, envelope=qenv, duration=dur*3))
        mat.add_tone(dur*2, SineToneEvent(frequency=prime*3/2, envelope=qenv, duration=dur*2))
        return mat
    tonic = f0/2
    # Tonic major
    file.add_signal( _major_chord(tonic).render() )
    file.add_silence(dur)
    # Subdominant major
    file.add_signal( _major_chord(tonic*4/3).render() )
    file.add_silence(dur)
    # Dominant major
    file.add_signal( _major_chord(tonic*3/2).render() )
    file.add_silence(dur)

if False:
    # Generate a nasty scale that you'd get for Db major if you tuned 
    #  your piano to JI in C major and B major (need two to get all 
    #  chromatic notes)
    prime = f0*tonal_space_pitch_2d((3,1))
    freqs = [
        prime,
        prime*tonal_space_pitch_2d((-2,1)),
        prime*tonal_space_pitch_2d((-4,-1)),
        prime*tonal_space_pitch_2d((-1,0)),
        prime*tonal_space_pitch_2d((-3,1)),
        prime*tonal_space_pitch_2d((-1,1)),
        prime*tonal_space_pitch_2d((-3,-1)),
        prime*2
    ]
    freqs.extend(reversed(freqs))
    mat = ToneMatrix()
    mat.add_tone(1, SineToneEvent(frequency=prime, envelope=fade_in_out_envelope(hold_ratio=100), duration=14) ) 
    for i,f in enumerate(freqs):
        mat.add_tone(i, SineToneEvent(frequency=f, envelope=fade_in_out_envelope(hold_ratio=100), duration=1) )
    file.add_signal(mat.render())
    file.add_silence(1.0)
    
if False:
    # The real Basin Street root sequence
    dur = 1.5
    prime = f0/2
    freqs = [
        (prime, 1),
        (prime*tonal_space_pitch((0,1,-2)), 1),
        (prime*tonal_space_pitch((-1,1,0)), 1),
        (prime*tonal_space_pitch((-2,1,1)), 2),
        (prime*tonal_space_pitch((-3,1,3)), 1),
        (prime*tonal_space_pitch((-4,1,4)), 1),
    ]
    mat = ToneMatrix()
    #mat.add_tone(0, SineToneEvent(frequency=prime, envelope=fade_in_out_envelope(hold_ratio=100), duration=dur) ) 
    cursor = 0.0
    for f,d in freqs:
        mat.add_tone(cursor, SineToneEvent(frequency=f, envelope=qenv, duration=dur*d) )
        cursor += d*dur
    mat.add_tone(cursor, SineToneEvent(frequency=prime, envelope=qenv, duration=dur) ) 
    file.add_signal(mat.render())
    file.add_silence(1.0)
    
file.save()

