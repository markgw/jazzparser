"""Constants relating to MIDI data.

These constants are used by MIDI data operations.

I'm not convinced all of these are useful. It might be nice to tidy 
them up a bit and make it clear what they're all for.

"""
OCTAVE_MAX_VALUE = 12
OCTAVE_VALUES = range( OCTAVE_MAX_VALUE )

NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
"""A set of names for each note in the 12-tet octave."""

WHITE_KEYS = [0, 2, 4, 5, 7, 9, 11]
"""Indices in the octave of the white notes on a piano keyboard."""

BLACK_KEYS = [1, 3, 6, 8, 10]
"""Indices in the octave of the black notes on a piano keyboard."""

NOTE_PER_OCTAVE = len( NOTE_NAMES )
NOTE_VALUES = range( OCTAVE_MAX_VALUE * NOTE_PER_OCTAVE )
NOTE_NAME_MAP_FLAT = {}
NOTE_VALUE_MAP_FLAT = []
NOTE_NAME_MAP_SHARP = {}
NOTE_VALUE_MAP_SHARP = []

for value in range( 128 ):
    noteidx = value % NOTE_PER_OCTAVE
    octidx = value / OCTAVE_MAX_VALUE
    name = NOTE_NAMES[noteidx]
    if len( name ) == 2:
        # sharp note
        flat = NOTE_NAMES[noteidx+1] + 'b'
        NOTE_NAME_MAP_FLAT['%s-%d' % (flat, octidx)] = value
        NOTE_NAME_MAP_SHARP['%s-%d' % (name, octidx)] = value
        NOTE_VALUE_MAP_FLAT.append( '%s-%d' % (flat, octidx) )
        NOTE_VALUE_MAP_SHARP.append( '%s-%d' % (name, octidx) )
        globals()['%s_%d' % (name[0] + 's', octidx)] = value
        globals()['%s_%d' % (flat, octidx)] = value
    else:
        NOTE_NAME_MAP_FLAT['%s-%d' % (name, octidx)] = value
        NOTE_NAME_MAP_SHARP['%s-%d' % (name, octidx)] = value
        NOTE_VALUE_MAP_FLAT.append( '%s-%d' % (name, octidx) )
        NOTE_VALUE_MAP_SHARP.append( '%s-%d' % (name, octidx) )
        globals()['%s_%d' % (name, octidx)] = value

BEATNAMES = ['whole', 'half', 'quarter', 'eighth', 'sixteenth', 'thiry-second', 'sixty-fourth']
BEATVALUES = [4, 2, 1, .5, .25, .125, .0625]
WHOLE = 0
HALF = 1
QUARTER = 2
EIGHTH = 3
SIXTEENTH = 4
THIRTYSECOND = 5
SIXTYFOURTH = 6

DEFAULT_MIDI_HEADER_SIZE = 14


CONTROL_MESSAGE_DICTIONARY = \
{0:'Bank Select, MSB',
 1:'Modulation Wheel',
 2:'Breath Controller',
 4:'Foot Controller',
 5:'Portamento Time',
 6:'Data Entry',
 7:'Channel Volume',
 8:'Balance',
 10:'Pan',
 11:'Expression Controller',
 12:'Effect Control 1',
 13:'Effect Control 2',
 16:'Gen Purpose Controller 1',
 17:'Gen Purpose Controller 2',
 18:'Gen Purpose Controller 3',
 19:'Gen Purpose Controller 4',
 32:'Bank Select, LSB',
 33:'Modulation Wheel',
 34:'Breath Controller',
 36:'Foot Controller',
 37:'Portamento Time',
 38:'Data Entry',
 39:'Channel Volume',
 40:'Balance',
 42:'Pan',
 43:'Expression Controller',
 44:'Effect Control 1',
 45:'Effect Control 2',
 48:'General Purpose Controller 1',
 49:'General Purpose Controller 2',
 50:'General Purpose Controller 3',
 51:'General Purpose Controller 4',
 64:'Sustain On/Off',
 65:'Portamento On/Off',
 66:'Sostenuto On/Off',
 67:'Soft Pedal On/Off',
 68:'Legato On/Off',
 69:'Hold 2 On/Off',
 70:'Sound Controller 1  (TG: Sound Variation;   FX: Exciter On/Off)',
 71:'Sound Controller 2   (TG: Harmonic Content;   FX: Compressor On/Off)',
 72:'Sound Controller 3   (TG: Release Time;   FX: Distortion On/Off)',
 73:'Sound Controller 4   (TG: Attack Time;   FX: EQ On/Off)',
 74:'Sound Controller 5   (TG: Brightness;   FX: Expander On/Off)',
 75:'Sound Controller 6   (TG: Decay Time;   FX: Reverb On/Off)',
 76:'Sound Controller 7   (TG: Vibrato Rate;   FX: Delay On/Off)',
 77:'Sound Controller 8   (TG: Vibrato Depth;   FX: Pitch Transpose On/Off)',
 78:'Sound Controller 9   (TG: Vibrato Delay;   FX: Flange/Chorus On/Off)',
 79:'Sound Controller 10   (TG: Undefined;   FX: Special Effects On/Off)',
 80:'General Purpose Controller 5',
 81:'General Purpose Controller 6',
 82:'General Purpose Controller 7',
 83:'General Purpose Controller 8',
 84:'Portamento Control (PTC)   (0vvvvvvv is the source Note number)   (Detail)',
 91:'Effects 1 (Reverb Send Level)',
 92:'Effects 2 (Tremelo Depth)',
 93:'Effects 3 (Chorus Send Level)',
 94:'Effects 4 (Celeste Depth)',
 95:'Effects 5 (Phaser Depth)',
 96:'Data Increment',
 97:'Data Decrement',
 98:'Non Registered Parameter Number (LSB)',
 99:'Non Registered Parameter Number (MSB)',
 100:'Registered Parameter Number (LSB)',
 101:'Registered Parameter Number (MSB)',
 120:'All Sound Off',
 121:'Reset All Controllers',
 122:'Local Control On/Off',
 123:'All Notes Off',
 124:'Omni Mode Off (also causes ANO)',
 125:'Omni Mode On (also causes ANO)',
 126:'Mono Mode On (Poly Off; also causes ANO)',
 127:'Poly Mode On (Mono Off; also causes ANO)'}
