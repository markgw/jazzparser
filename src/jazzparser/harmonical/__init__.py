"""The Harmonical: a just-intonation music generator module.

The Harmonical is an instrument that can play music in any tuning 
system, including just intonation, by allowing the music to specify 
a precise pitch for each note.

Its name is that given by Alexander J. Ellis, in his translation of 
Helmholtz's On the Sensations of Tone, to his specially tuned harmonium 
that allowed him to experiment with just tuning systems.

"""

"""Tonal space clusters to realize different chord types."""
CHORD_TYPES = {
    'M7' : [(0,0,0),(1,0,1),(0,1,1),(1,1,0)],
    'm'  : [(0,0,0),(1,0,1),(1,-1,1)],
    # Not entirely certain this is the right 7
    'm7' : [(0,0,0),(1,0,1),(1,-1,1),(-2,0,2)],
    '7'  : [(0,0,0),(1,0,1),(0,1,1),(-2,0,2)],
    ''   : [(0,0,0),(1,0,1),(0,1,1)],
    'prime' : [(0,0,0)],
}
