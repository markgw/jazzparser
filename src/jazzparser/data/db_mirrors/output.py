"""Output chord corpus data to a text file that others can use.

Data structures and utilities are provided elsewhere in the codebase for 
loading, editing, converting, saving, etc. chord sequence data with 
annotations. It's stored either as a sqlite database or as pickled Python 
object, neither of which is useful to many other people. This format is 
designed to be easily readable by others.

I don't currently provide any implementation of reading this file format, 
since all scripts take their input from an internally-used format. The 
description below of the file format should be enough to implement a function 
to read this in the language of your choice.

File format
===========
The standard file extension to use for these file shall be C{jcc}.

The first line is always::
 JAZZPARSER CHORD CORPUS

Chord sequences are preceded by a blank line. They begin with the line::
 BEGIN SEQUENCE

The lines that follow, up to the C{BEGIN CHORDS} line, contain metadata 
about the sequence.
 - C{INDEX}: sequences are numbered sequentially and this is the index of 
   the sequence within the file.
 - C{ID}: database id of the sequence. This provides a way of referring to 
   a sequence in a corpus that is not tied to its position in the file 
   (you might want a different ordering, or selection of sequences).
 - C{NAME}: unicode name of the song (utf-8 encoded).
 - C{KEY}: key of the piece in the source. Chords are stored relative to 
   this key. E.g. in C major, a chord 5 is F. The formatting of this wasn't 
   originally intended to be machine readable, so might be a little 
   inconsistent. It is generally a note name (using C{b} and C{#} for flat 
   and sharp) followed by C{major} or C{minor} (C{major} assumed if omitted).
 - C{BAR LENGTH}: integer number of beats per bar (durations of chords are 
   stored in beats.
 - C{SOURCE}: where the chord sequence was taken from. Almost always 
   "C{The Real Book, Sixth Edition}".
   
Lines between C{BEGIN CHORDS} and C{END CHORDS} each represent a single 
chord, with comma-separated fields. The fields are the following:
 - B{root}: equal-temperament pitch class (integer) relative to key.
 - B{chord type}: chord type label.
 - B{duration}: integer number of beats.
 - B{additions}: any further additions to the chord notated in the input 
   not covered by the chord type (anything above the seventh degree).
 - B{bass}: integer pitch class of bass note, if written in the input 
   (e.g. C7/B{G}). Otherwise blank.
 - B{category}: lexical category of annotation, from the jazz CCG grammar.
 - B{coordination middle}: unresolved dominant/subdominant chord which 
   marks the middle point of a coordination. E.g. G7 in (Dm7 G7) (A7 Dm7 G7) 
   CM7. C{T} or C{F}.
 - B{coordination end}: dominant/subdominant sharing its resolution with a 
   previously marked coordination-middle chord. C{T} or C{F}.

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

def output_sequence_index(index, outfile):
    """
    Outputs the sequences in the sequence index to a text file.
    
    @type index: jazzparser.data.db_mirrors.SequenceIndex
    @param index: index to get sequences from
    @type outfile: file-like object
    @param outfile: file to write to
    
    """
    _write_header(index, outfile)
    for ind,seq in enumerate(index.sequences):
        _write_sequence(seq, ind, outfile)


def _write_header(index, outfile):
    """
    Writes a header to the outfile for this sequence index.
    
    """
    # Required first line to identify the filetype
    print >>outfile, "JAZZPARSER CHORD CORPUS"

def _write_sequence(seq, index, outfile):
    """
    Writes the data for one chord sequence to the outfile.
    
    """
    print >>outfile
    print >>outfile, "BEGIN SEQUENCE"
    print >>outfile, "INDEX: %d" % index
    print >>outfile, "ID: %d" % seq.id
    print >>outfile, "NAME: %s" % seq.name.encode('utf8')
    print >>outfile, "KEY: %s" % seq.key
    print >>outfile, "BAR LENGTH: %d" % seq.bar_length
    print >>outfile, "SOURCE: %s" % seq.source
    print >>outfile, "BEGIN CHORDS"
    for chord in seq.iterator():
        _write_chord(chord, outfile)
    print >>outfile, "END CHORDS"

def _write_chord(crd, outfile):
    """
    Writes a single line of data for a chord to the outfile.
    
    """
    print >>outfile, "%d, %s, %d, %s, %s, %s, %s, %s" % \
            (crd.root, crd.type, crd.duration, crd.additions, 
                crd.bass or "", crd.category, 
                "T" if crd.treeinfo.coord_unresolved else "F", 
                "T" if crd.treeinfo.coord_resolved else "F")
