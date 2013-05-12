"""Tonal space manipulations and analysis.

Note that this module is only intended for formalism-independent 
tonal space manipulations. Functions should not rely on representations 
that are formalism-specific, like 
L{TonalDenotation<jazzparser.formalisms.music_keyspan.semantics.TonalDenotation>}.
They may use things like coordinates, which could be produced from 
an formalism-specific semantics.

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


def nearest_neighbour(base_coord, root_number):
    """
    Returns the coordinate of the point with the given root number 
    that is closest to the given point base_coord. Coordinates are 
    represented as (x,y) tuples. The root number is the semitone 
    number of the root (0->I, 1->bII, etc). 0 is assumed to be the 
    ET equivalence set including the central point (0,0).
    
    @rtype: (x,y) coordinate
    @return: the location of the point with the given ET root number 
        that is closest to the base point.
    
    """
    base_x, base_y = base_coord
    # Get the root number of the base coord
    base_root = (7*base_x + 4*base_y) % 12
    # Decide which nearby point to pick, relative to the base, by 
    # looking at the interval
    interval = (root_number - base_root) % 12
    # Now we just consult the predefined mapping of intervals to nearest 
    # neighbours:
    #     9  4 11  6
    # 10  5  0  7  2
    #     1  8  3
    rel_coord = {
        0 : (0,0),
        1 : (-1,-1),
        2 : (2,0),
        3 : (1,-1),
        4 : (0,1),
        5 : (-1,0),
        6 : (-2,-1),
        7 : (1,0),
        8 : (0,-1),
        9 : (-1,1),
        10 : (-2,0),
        11 : (1,1)
    }[interval]
    # Now add this to the base coord to get the actual coord of the neighbour
    return (base_x+rel_coord[0], base_y+rel_coord[1])

def coordinates_to_roman_names(coords):
    """
    Given a list of tonal space coordinates, return a list of strings 
    giving the roman numeral names of the points. The name is the 
    unambiguous unique specifier of the point (e.g. bbIII++).
    
    """
    return [coordinate_to_roman_name(coord) for coord in coords]
    
def coordinate_to_roman_name(coord, sharp="#", flat="b", plus="+", minus="-", 
            names=None, accidentals_after=False):
    """
    Given a coordinate (x,y), returns the unique roman numeral name of 
    that point in the space, assuming that I is at (0,0).
    
    """
    region = coordinate_key_region(coord)
    # Work out where this coordinate lies within its local region
    x,y = coordinate_within_region(coord)
    # This gives us the base name (without accidentals or +/-s)
    if names is None:
        roman_name = {
            (0,0) : "IV",
            (1,0) : "I",
            (2,0) : "V",
            (3,0) : "II",
            (0,1) : "VI",
            (1,1) : "III",
            (2,1) : "VII"
        }[(x,y)]
    else:
        roman_name = names[(x,y)]
    # The accidentals are defined by the y value of the region's identifier
    acc_count = region[1]
    if acc_count > 0:
        accidentals = sharp * acc_count
    elif acc_count < 0:
        accidentals = flat * (-1*acc_count)
    else:
        accidentals = ""
    # The -/+s are simply a function of the x coordinate
    plus_count = (coord[0] + 1) / 4
    if plus_count > 0:
        mods = plus * plus_count
    elif plus_count < 0:
        mods = minus * (-1*plus_count)
    else:
        mods = ""
    if accidentals_after:
        return u"%s%s%s" % (roman_name, accidentals, mods)
    else:
        return u"%s%s%s" % (accidentals, roman_name, mods)

def coordinate_to_alpha_name_c(*args, **kwargs):
    """
    Does the same as L{coordinate_to_roman_name}, but generates alphabetic 
    note names in the key of C (i.e. (0,0)=C).
    
    """
    names = {
        (0,0) : "F",
        (1,0) : "C",
        (2,0) : "G",
        (3,0) : "D",
        (0,1) : "A",
        (1,1) : "E",
        (2,1) : "B"
    }
    kwargs['names'] = names
    kwargs['accidentals_after'] = True
    return coordinate_to_roman_name(*args, **kwargs)

def coordinate_key_region(coord):
    """
    Given a tonal space coordinate, returns the 2D identifier of the 
    key region that it lies in. A key region is the 
    not-quite-rectangular region of notes in a major scale. The central 
    one contains IV (at (-1,0)), rightwards to II ((2,0)), and VI 
    ((-1,1)), rightwards to VII ((1,0)). These regions are tessellated 
    across the infinite space.
    
    The coordinate returned identifies the region. (0,0) is the central 
    region, with bottom left at point (-1,0). (1,0) is strictly to the 
    right and down one, so has its bottom left at (-1,3).
    
    """
    x,y = coord
    return ((y + 2*x + 2) / 7, (4*y + x + 1) /7)

def coordinate_within_region(coord):
    """
    Given a tonal space coordinate, returns the coordinate of this point 
    relative to the bottom left corner of the local key region in which 
    it lies (see L{coordinate_key_region}).
    
    This coordinate will be among (0,0),...,(3,0),(0,1),...,(2,1).
    
    """
    x,y = coord
    spacex, spacey = coordinate_key_region(coord)
    localx = x - 4*spacex + spacey + 1
    localy = y - 2*spacey + spacex
    return localx,localy
    
def equate_ends(coords0, coords1):
    """
    Translates the second list of coordinates so that it ends at the 
    same point as the first and returns the result.
    
    """
    # Work out how much to translate by
    shift = (coords0[-1][0] - coords1[-1][0]), (coords0[-1][1] - coords1[-1][1])
    # Shift all the points of coords1 by this amount
    return [(x+shift[0], y+shift[1]) for (x,y) in coords1]

def coordinate_to_et(coord):
    """
    Takes a point in the tonal space and returns the number of 
    semitones above the origin's pitch that point would be in 
    equal temperament.
    
    The coordinate is 3-dimensional.
    
    """
    x,y,z = coord
    # We go 7 semitones up for every right step
    # And 4 for every up step
    return (7*x + 4*y + 12*z)
    
def coordinate_to_et_2d(coord):
    """
    2-dimensional version of L{coordinate_to_et}. Returns an interval 
    within one octave upwards ([0-12]).
    
    """
    x,y=coord
    return coordinate_to_et((x,y,0))%12

def cents_to_pitch_ratio(cents):
    """
    Converts a number of cents (tuning theory unit of pitch ratio) into 
    a floating point pitch multiplier.
    
    @type cents: float
    @param cents: number of cents
    
    """
    return 2 ** (float(cents)/1200)
    
def pitch_ratio_to_cents(ratio):
    """
    Inverse of L{cents_to_pitch_ratio}. Given a pitch multiplier, 
    returns the equivalent interval expressed in cents.
    
    """
    import math
    return float(1200) * math.log(float(ratio), 2)


def tonal_space_pitch(coord):
    """
    Given a 3D coordinate in the tonal space, returns the pitch ratio 
    of that point from the origin's pitch.
    x: fifths
    y: thirds
    z: octaves
    
    """
    import math
    x,y,z = coord
    return math.pow(2, z) * math.pow(1.5, x) * math.pow(1.25, y)

def tonal_space_pitch_2d(coord):
    """
    Given a 2D coordinate in the tonal space, returns the pitch ratio 
    of that point from the origin's pitch assuming that the point is 
    within one octave above the origin.
    
    """
    x,y = coord
    pitch = tonal_space_pitch((x,y,0))
    # Get it within an octave
    if pitch < 1.0:
        ratio = 2.0
    else:
        ratio = 0.5
    while pitch < 1.0 or pitch >= 2.0:
        pitch *= ratio
    return pitch
    
def tonal_space_et_pitch(coord):
    """
    Given a (2D) point in the tonal space, returns the pitch ratio from the 
    origin that it would have in the equal-temperament wrapped space.
    
    """
    if len(coord) == 3:
        return et_interval(coordinate_to_et(coord))
    else:
        return et_interval(coordinate_to_et_2d(coord))

def et_interval(st=1, oct=0):
    """
    Frequency ratio corresponding to a number of ET semitones and octaves.
    
    """
    import math
    semitones = oct*12 + st
    return math.exp(math.log(2.0)/12*semitones)
et_semitone = et_interval(1)


def add_z_coordinates(coords, center=(0,0,0), pitch_range=1):
    """
    Given a list of (x,y) coordinates, adds a z-coordinate to each 
    such that the pitch of the notes is kept within a given number of 
    octaves around the given center.
    
    @type coords: list of 2-tuples
    @param coords: (x,y) coordinates
    @type center: 3-tuple
    @param center: point that defines the center of the range of 
        pitches within which the output coordinates will lie
    @type pitch_range: int
    @param pitch_range: width of the range of pitches, as an integer 
        number of octaves.
    
    """
    center_pitch = tonal_space_pitch(center)
    half_range = float(pitch_range) / 2
    # Work out the bounds of the allowed pitch range
    bottom = center_pitch / (2**half_range)
    top = center_pitch * (2**half_range)
    
    coords3d = []
    for (x,y) in coords:
        z = 0
        while tonal_space_pitch((x,y,z)) > top:
            z -= 1
        while tonal_space_pitch((x,y,z)) < bottom:
            z += 1
        coords3d.append((x,y,z))
    return coords3d

def root_to_et_coord(root):
    """
    Given a ET root as an integer in the range 0 <= r < 12, returns the 
    2D ET coordinate in the range (0,0) <= (x,y) < (4,3) that that 
    root has in the 4x3 ET space.
    
    If the root is not within that range, it will be taken mod 12.
    
    """
    # The map looks like this:
    #  8  3  10 5
    #  4  11 6  1
    #  0  7  2  9
    root_map = {
        0  : (0,0),
        1  : (3,1),
        2  : (2,0),
        3  : (1,2),
        4  : (0,1),
        5  : (3,2),
        6  : (2,1),
        7  : (1,0),
        8  : (0,2),
        9  : (3,0),
        10 : (2,2),
        11 : (1,1)
    }
    return root_map[root % 12]
