# Parts of the state labels
# Tonic value names
TONIC_NAMES = {
    0: 'C', 1: 'Db', 2: 'D', 3: 'Eb', 4: 'E', 5: 'F', 6: 'Gb', 7: 'G', 
    8: 'Ab', 9: 'A', 10: 'Bb', 11: 'B'
}
RELATIVE_TONIC_NAMES = {
    0: 'I', 1: 'bII', 2: 'II', 3: 'bIII', 4: 'III', 5: 'IV', 6: 'bV', 7: 'V',
    8: 'bVI', 9: 'VI', 10: 'bVII', 11: 'VII'
}
# Mode part
MODE_MAJOR = 0
MODE_MINOR = 1
# Mode part names
MODE_NAMES = {
    MODE_MAJOR : 'major',
    MODE_MINOR : 'minor',
}
MODE_SHORT_NAMES = {
    MODE_MAJOR : 'M',
    MODE_MINOR : 'm',
}
# Chord part (chord label within mode)
CHORD_I =    0
CHORD_II =   1
CHORD_III =  2
CHORD_IV =   3
CHORD_V =    4
CHORD_VI =   5
CHORD_VII =  6
CHORD_V7 =   7
# Chord part names
CHORD_NAMES = {
    CHORD_I : 'I',
    CHORD_II : 'II',
    CHORD_III : 'III',
    CHORD_IV : 'IV',
    CHORD_V : 'V',
    CHORD_VI : 'VI',
    CHORD_VII : 'VII',
    CHORD_V7 : 'V7',
}
# All possible chord labels
CHORDS = [ CHORD_I, CHORD_II, CHORD_III, CHORD_IV, CHORD_V, CHORD_VI, CHORD_VII, CHORD_V7 ]
# All possible modes
MODES = [ MODE_MAJOR, MODE_MINOR ]

# The notes that make up each chord in each mode
CHORD_NOTES = {
    MODE_MAJOR : {
        CHORD_I : (0, 4, 7),
        CHORD_II : (2, 5, 9),
        CHORD_III : (4, 7, 11),
        CHORD_IV : (5, 9, 0),
        CHORD_V : (7, 11, 2),
        CHORD_VI : (9, 0, 4),
        CHORD_VII : (11, 2, 5),
        CHORD_V7 : (7, 11, 2, 5),
    },
    MODE_MINOR : {
        CHORD_I : (0, 3, 7),
        CHORD_II : (2, 5, 8),
        CHORD_III : (3, 7, 11),
        CHORD_IV : (5, 8, 0),
        CHORD_V : (7, 11, 2),
        CHORD_VI : (8, 0, 3),
        CHORD_VII : (11, 2, 5),
        CHORD_V7 : (7, 11, 2, 5),
    }
}
# The scale notes of each mode
SCALES = {
    MODE_MAJOR : ( 0, 2, 4, 5, 7, 9, 11 ),
    MODE_MINOR : ( 0, 2, 3, 5, 7, 8, 11 )
}

TRIAD_TYPE_MAJOR = 0
TRIAD_TYPE_MINOR = 1
TRIAD_TYPE_DIMINISHED = 2
TRIAD_TYPE_AUGMENTED = 3
TRIAD_TYPE_DOM7 = 4

TRIAD_TYPE_NAMES = {
    TRIAD_TYPE_MAJOR : 'maj',
    TRIAD_TYPE_MINOR : 'min',
    TRIAD_TYPE_DIMINISHED : 'dim',
    TRIAD_TYPE_AUGMENTED : 'aug',
    TRIAD_TYPE_DOM7 : 'dom7',
}
TRIAD_TYPE_SYMBOLS = {
    TRIAD_TYPE_MAJOR : '',
    TRIAD_TYPE_MINOR : 'm',
    TRIAD_TYPE_DIMINISHED : 'dim',
    TRIAD_TYPE_AUGMENTED : 'aug',
    TRIAD_TYPE_DOM7 : '7',
}

# The triad type of each chord in each mode
SCALE_TRIADS = {
    MODE_MAJOR : {
        CHORD_I : TRIAD_TYPE_MAJOR,
        CHORD_II : TRIAD_TYPE_MINOR,
        CHORD_III : TRIAD_TYPE_MINOR,
        CHORD_IV : TRIAD_TYPE_MAJOR,
        CHORD_V : TRIAD_TYPE_MAJOR,
        CHORD_VI : TRIAD_TYPE_MINOR,
        CHORD_VII : TRIAD_TYPE_DIMINISHED,
        CHORD_V7 : TRIAD_TYPE_DOM7,
    },
    MODE_MINOR : {
        CHORD_I : TRIAD_TYPE_MINOR,
        CHORD_II : TRIAD_TYPE_DIMINISHED,
        CHORD_III : TRIAD_TYPE_AUGMENTED,
        CHORD_IV : TRIAD_TYPE_MINOR,
        CHORD_V : TRIAD_TYPE_MAJOR,
        CHORD_VI : TRIAD_TYPE_MAJOR,
        CHORD_VII : TRIAD_TYPE_DIMINISHED,
        CHORD_V7 : TRIAD_TYPE_DOM7,
    }
}

TRIAD_NOTES = {
    TRIAD_TYPE_MAJOR : (0, 4, 7),
    TRIAD_TYPE_MINOR : (0, 3, 7),
    TRIAD_TYPE_DIMINISHED : (0, 3, 6),
    TRIAD_TYPE_AUGMENTED : (0, 4, 8),
    TRIAD_TYPE_DOM7 : (0, 4, 7, 10),
}

# Named sets of chords that can be used by different types of models
CHORD_SETS = {
    # The scale degrees, plus the dominant seventh
    # This is the default, since it's what R&S use in their experiments
    'scale+dom7' : [ CHORD_I, CHORD_II, CHORD_III, CHORD_IV, CHORD_V, CHORD_VI, CHORD_VII, CHORD_V7 ],
    # Just the scale degrees
    'scale' : [ CHORD_I, CHORD_II, CHORD_III, CHORD_IV, CHORD_V, CHORD_VI, CHORD_VII ],
    # Three-chord variant
    # Currently there's a special model subclass for this
    'three-chord' : [ CHORD_I, CHORD_IV, CHORD_V ],
    # Four-chord variant
    # Also has its own subclass
    'four-chord' : [ CHORD_I, CHORD_II, CHORD_IV, CHORD_V ],
}
