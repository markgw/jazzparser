"""Semantics module for the music_halfspan formalism.

Lambda calculus semantics for the halfspan formalism.
This is the form of the semantics described in our paper appendix and in 
my 2nd-year review.

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

import copy, re, math
from ...base.semantics.lambdacalc import \
            Semantics as SemanticsBase, LambdaAbstraction as LambdaAbstractionBase, \
            FunctionApplication as FunctionApplicationBase, \
            Variable as VariableBase, Literal, LogicalForm, \
            DummyLogicalForm as DummyLogicalFormBase, \
            next_unused_variable, multi_apply as multi_apply_base, \
            multi_abstract as multi_abstract_base, Terminal
from ...base.semantics.temporal import Temporal, TemporalSemantics, \
            earliest_time
from jazzparser.utils.base import group_pairs
from jazzparser.utils.tonalspace import root_to_et_coord, \
            coordinate_to_roman_name, coordinate_to_et_2d, \
            coordinate_to_alpha_name_c
from jazzparser.settings import OPTIONS
from itertools import izip

# We set this here so that we don't have to look it up every time we output 
#  something. It's a little inelegant to hard-code it, but we can't get it 
#  from the Formalism now, because this needs to be imported to prepare the 
#  Formalism
# This is just for efficiency
FORMALISM_NAME = "music_halfspan"

class Semantics(SemanticsBase, TemporalSemantics):
    def __init__(self, *args, **kwargs):
        SemanticsBase.__init__(self, *args, **kwargs)
        TemporalSemantics.__init__(self)
    
    def format_result(self):
        return self.lf.format_result()

class DummyLogicalForm(DummyLogicalFormBase, Temporal):
    def __init__(self, *args, **kwargs):
        DummyLogicalFormBase.__init__(self, *args, **kwargs)
        Temporal.__init__(self)
    
    def set_time(self, time):
        self.time = time
        
    def get_literal_time_list(self):
        return [self.time]
    
    def format_result(self):
        return str(self)


INTERVAL_TO_NN = {
    0 : (0,0),
    1 : (-1,-1),
    2 : (2,0),
    3 : (1,-1),
    4 : (0,1),
    5 : (-1,0),
    # We consistently make this arbitrary choice (not (2,1))
    6 : (-2,-1),
    7 : (1,0),
    8 : (0,-1),
    9 : (-1,1),
    10 : (-2,0),
    11 : (1,1)
}

class EnharmonicCoordinate(Terminal, Temporal):
    """
    A four-dimensional coordinate. Stores the coordinate (x,y) within 
    an enharmonic (4x3) block, and the coordinate (X,Y) that locates 
    the enharmonic block within the infinite space.
    
    Note that if x and y are set outside the range, they'll just be taken 
    mod 4 and 3 respectively. If you want to set x,y and X,Y from a 2D 
    coordinate, use from_harmonic_coord or the + operator.
    
    This is used in the semantics as a tonic point.
    
    """
    timed_object = True
    delta = False
    
    def __init__(self, coord=(0,0), block=(0,0), time=None, duration=None, delta=False, *args, **kwargs):
        """
        @type delta: bool
        @param delta: whether this represents a vector, rather than a 
            point, in the tonal space. A delta coordinate will never show in 
            roman numeral format
        
        """
        Terminal.__init__(self, *args, **kwargs)
        Temporal.__init__(self, time=time, duration=duration)
        
        self.delta = delta
        self.x, self.y = coord
        self.X, self.Y = block
        
    def __str__(self):
        # Representation depends on the selected output format
        fmt = OPTIONS.OUTPUT[FORMALISM_NAME]["tsformat"]
        if self.delta or fmt == "xycoord":
            # 2D coordinate
            # Always use this format for deltas
            return self.harmonic_str()
        elif fmt == "roman":
            # Roman numeral output
            strng = "<%s>" % coordinate_to_roman_name(self.harmonic_coord)
        elif fmt == "alpha":
            # Note name output
            strng = "<%s>" % coordinate_to_alpha_name_c(self.harmonic_coord)
        else:
            strng =  "<(%d,%d)/(%d,%d)>" % (self.x, self.y, self.X, self.Y)
        
        if self.time is not None:
            strng = "%s@%d" % (strng,self.time)
        return strng
    
    def format_result(self):
        """
        When displaying LFs for results, the enharmonic block has no meaning 
        and is just confusing. Just show the (x,y) pair.
        
        """
        return "<%d,%d>" % (self.x, self.y)
        
    def __repr__(self):
        return str(self)
    
    def get_start_time(self):
        return self.time
        
    def harmonic_str(self):
        """
        A string representation of the coordinate that's like the normal 
        __str__, but displays the harmonic coordinate, rather than the 
        enharmonic 4-tuple.
        
        """
        strng =  "(%d,%d)" % self.harmonic_coord
        if self.time is not None:
            strng = "%s@%d" % (strng,self.time)
        return strng
        
    def __eq__(self, other):
        return type(self) == type(other) and \
                self.x == other.x and \
                self.y == other.y and \
                self.X == other.X and \
                self.Y == other.Y and \
                self.time == other.time
        
    def copy(self):
        return EnharmonicCoordinate((self.x, self.y), (self.X, self.Y), 
                time=self._time, duration=self._duration, 
                delta=self.delta)
        
    def set_time(self, time):
        self.time = earliest_time([time, self.time])
        
    @property
    def zero_coord(self):
        """
        Returns the 2D coordinate within an enharmonic block.
        Equivalently, locates this coordinate in the zeroth enharmonic 
        block.
        
        """
        return (self.x, self.y)
        
    @property
    def block_coord(self):
        """
        Returns the 2D location of the enharmonic block in which this 
        coordinate lies.
        
        """
        return (self.X, self.Y)
        
    @property
    def harmonic_coord(self):
        """
        Returns the 2D coordinate (relative to the origin block) that 
        this enharmonic coordinate represents.
        
        """
        return (4*self.X + self.x,
                3*self.Y - self.X + self.y)
    
    @staticmethod
    def from_harmonic_coord(coord):
        """
        Creates an enharmonic coordinate from a harmonic coordinate, 
        given as a 2-tuple.
        
        """
        # Check this is a 2-tuple
        x,y = coord
        encoord = EnharmonicCoordinate()
        # add_coord has all the arithmetic we need
        encoord += (x,y)
        return encoord
        
    def _get_x(self):
        return self._x
    def _set_x(self, x):
        self._x = x % 4
    x = property(_get_x, _set_x)
    
    def _get_y(self):
        return self._y
    def _set_y(self, y):
        self._y = y % 3
    y = property(_get_y, _set_y)
    
    def _get_X(self):
        return self._X
    def _set_X(self, X):
        self._X = X
    X = property(_get_X, _set_X)
    
    def _get_Y(self):
        return self._Y
    def _set_Y(self, Y):
        self._Y = Y
    Y = property(_get_Y, _set_Y)
    
    def nearest(self, coord):
        """
        Given a 2D coord within an enharmonic block, returns an 
        L{EnharmonicCoordinate} for the instance of that point that is 
        closest to this enharmonic coordinate.
        
        @type coord: 2-tuple or L{EnharmonicCoordinate}
        @param coord: if given as a tuple, should be a coordinate within 
            a block (i.e. between (0,0) and (4,3)); if an EC, the EC's zero 
            coord will be used
        
        """
        if type(coord) == EnharmonicCoordinate:
            coord = coord.zero_coord
        else:
            assert 0 <= coord[0] <= 4
            assert 0 <= coord[1] <= 3
        
        base_x, base_y = self.harmonic_coord
        # Get the ET pitch class note number of the base coord
        base_note = 7*base_x + 4*base_y
        # Do the same for the candidate coordinate
        candidate_note = 7*coord[0] + 4*coord[1]
        # Decide which nearby point to pick, relative to the base, by 
        # looking at the interval
        interval = (candidate_note - base_note) % 12
        # Now we just consult the predefined mapping of intervals to nearest 
        # neighbours:
        #     9  4 11  6
        # 10  5  0  7  2
        #     1  8  3
        rel_coord = INTERVAL_TO_NN[interval]
        # Now add this to the base coord to get the actual coord of the neighbour
        return EnharmonicCoordinate.from_harmonic_coord(
                                    (base_x+rel_coord[0], base_y+rel_coord[1]))
        
    def add_coord(self, coord=(0,0), delta=False):
        """
        Returns an enharmonic coordinate that results from adding the 
        2D harmonic coordinates to this enharmonic coordinate.
        
        E.g.
        <(0,1)/(0,0)> + (-1,0) = <(3,0)/(-1,0)>
        and
        <(1,0)/(0,0)> + (-1,0) = <(0,0)/(0,0)>
        
        """
        absx = self.x + coord[0]
        absy = self.y + coord[1]
        # Work out what block we're in, relative to where we started
        blockshiftx = (absx / 4)
        blockshifty = (absy + blockshiftx) / 3
        # x coords just wrap around every 4
        newx = absx % 4
        # y coords wrap around at a position that depends on how much 
        #  we're moving in x
        newy = (absy+blockshiftx) % 3
        
        newX = self.X + blockshiftx
        newY = self.Y + blockshifty
        return EnharmonicCoordinate((newx, newy), (newX, newY), delta=delta)
        
    def __add__(self, other):
        """
        Define addition for 2D coordinates (same as L{add_coord})
        and C{EnharmonicCoordinate}s.
        
        """
        if type(other) == tuple:
            if len(other) == 2:
                return self.add_coord(other)
            else:
                raise TypeError, "tuples added to an "\
                    "EnharmonicCoordinate must be 2-tuples (got %d)" % len(other)
        elif type(other) == EnharmonicCoordinate:
            # Just convert the encoord into a 2D harmonic coord and add that 
            #  to ourselves
            delta = self.delta and other.delta
            # If both inputs are deltas, the output should be
            # Otherwise, the output is never a delta
            # We don't complain if neither input is a delta, though we probably should
            return self.add_coord(other.harmonic_coord, delta=delta)
        else:
            raise TypeError, "cannot add object of type %s to an "\
                "EnharmonicCoordinate" % type(other).__name__
                
    def __sub__(self, other):
        """
        Define subtraction for 2D coordinates and C{EnharmonicCoordinate}s.
        
        Result is always a delta.
        
        """
        if type(other) == tuple:
            if len(other) == 2:
                return self.add_coord((-other[0],-other[1]), delta=True)
            else:
                raise TypeError, "tuples subtracted from an "\
                    "EnharmonicCoordinate must be 2-tuples (got %d)" % len(other)
        elif type(other) == EnharmonicCoordinate:
            # Just convert the encoord into a 2D harmonic coord and subtract 
            #  that from ourselves
            hc = other.harmonic_coord
            return self.add_coord((-hc[0], -hc[1]), delta=True)
        else:
            raise TypeError, "cannot add object of type %s to an "\
                "EnharmonicCoordinate" % type(other).__name__

class LexicalCoordinate(Terminal, Temporal):
    """
    When a logical form is read in from the lexicon, coordinates 
    must be specified relative to the root of the chord. Only when the 
    sign is used as the interpretation of a chord will this root 
    be known. In the meantime, we store a coordinate 
    (0,0) <= (cx,cy) <= (4,3) that specifies the position of the point 
    relative to the (equal temperament) position (x,y) of the chord 
    root.
    Once this is known, an L{EnharmonicCoordinate} will be produced 
    at ((x+cx)%4, (y+cy)%3).
    
    """
    timed_object = True
    
    def __init__(self, coord=(0,0), time=None, duration=None, *args, **kwargs):
        Terminal.__init__(self, *args, **kwargs)
        Temporal.__init__(self, time=time, duration=duration)
        self.x, self.y = coord
    
    def __str__(self):
        return "X(%d,%d)" % (self.x, self.y)
    
    def format_result(self):
        return str(self)
    
    def get_start_time(self):
        return self.time
        
    def harmonic_str(self):
        """
        Same as __str__. Only here for compatibility with EnharmonicCoordinate.
        
        """
        return str(self)
        
    def __eq__(self, other):
        return type(self) == type(other) and \
            self.x == other.x and self.y == other.y
        
    def set_time(self, time):
        self.time = earliest_time([time, self.time])
        
    def resolve(self, coord=(0,0)):
        """
        Produces the actual L{EnharmonicCoordinate}, given the 2D 
        position of the chord root.
        
        """
        return EnharmonicCoordinate(
                    ((self.x+coord[0])%4, (self.y+coord[1])%3))
    
    def copy(self):
        return LexicalCoordinate((self.x, self.y), 
                    time=self.time, duration=self.duration)

class GhostCoordinate(Terminal, Temporal):
    """
    Wrapper that stores an L{EnharmonicCoordinate}. The idea of this is 
    that it can be used in getting a path from coordinations to represent 
    the resolution of a cadence, but without the coordinate itself 
    featuring in the path. It just signals that things should be taken relative 
    to this point, but that the point itself should be burnt after reading.
    
    """
    def __init__(self, coordinate, *args, **kwargs):
        Terminal.__init__(self, *args, **kwargs)
        Temporal.__init__(self)
        
        self.coordinate = coordinate
    
    def get_start_time(self):
        return self.time
        
    def __str__(self):
        return "~%s~" % self.coordinate
    
    def format_result(self):
        return str(self)
        
    def __eq__(self, other):
        return type(self) == type(other) and \
            self.coordinate == other.coordinate
    
    def copy(self):
        return GhostCoordinate(self.coordinate.copy())

class List(LogicalForm, Temporal):
    """
    The I{Path} or I{List} data structure. Primarily this is a list of 
    enharmonic coordinates or logical forms. In the written semantics, this 
    is shown as a list, but it is subject to certain reductions, such as when 
    a predicate (like I{leftonto}) is applied to it.
    
    The items are implemented simply as a Python list, which should 
    make list processing much more efficient than if we used a 
    linked list implementation that corresponds better to the 
    theoretical definition of the semantics.
    
    """
    def __init__(self, items=[], *args, **kwargs):
        LogicalForm.__init__(self, *args, **kwargs)
        Temporal.__init__(self)
        
        self._items = []
        self.extend(items)
        
    def __str__(self):
        return "[%s]" % ", ".join(str(child) for child in self)
    
    def format_result(self):
        return "[%s]" % ", ".join(child.format_result() for child in self)
        
    def __eq__(self, other):
        return type(self) == type(other) and \
            all(this==that for (this,that) in zip(self,other))
    
    def get_start_time(self):
        if len(self) > 0:
            return self[0].get_start_time()
        else:
            # This should never happen in practice
            return None
        
    def set_time(self, time):
        if len(self) > 0:
            self[0].set_time(time)
        
    def append(self, point):
        """
        Appends the point to the path.
        
        """
        self._items.append(point)
        point.parent = self
        
    def prepend(self, point):
        """
        Prepends the point to the start of the path.
        
        Same as L{insert}(0, point).
        
        """
        self.insert(0, point)
        
    def extend(self, points):
        """
        Appends all points in the given list to the points of the path.
        
        """
        self._items.extend(points)
        for p in points:
            p.parent = self
    
    def __len__(self):
        return len(self._items)
        
    def __getitem__(self, i):
        return self._items[i]
    def __setitem__(self, i, val):
        self._items[i] = val
        val.parent = self
        
    def pop(self, i):
        """Removes and returns the ith point from the path"""
        child = self._items.pop(i)
        # Orphan the child
        child.parent = None
        return child
        
    def insert(self, i, point):
        """Inserts a point at the given position on the path"""
        self._items.insert(i, point)
        point.parent = self
        
    def shift_block(self, shift):
        """
        Moves all the points on the path to another block, given relative to 
        their old one C{shift}.
        
        @type shift: 2-tuple of ints
        @param shift: block shift to apply to each point on the path.
        
        """
        raise NotImplementedError, "I haven't got round to doing this yet"
            
    def copy(self):
        items = [p.copy() for p in self]
        return List(items=items)
            
    def to_list(self):
        """
        Implemented for backward-compatibility with older formalisms. Just 
        returns list(path).
        """
        return list(self)
    
    ######## LogicalForm abstract methods
    def alpha_convert(self, src, trg):
        for child in self.get_children():
            child.alpha_convert(src, trg)
            
    def beta_reduce(self, *args, **kwargs):
        for child in self.get_children():
            child.beta_reduce()
        return self
            
    def substitute(self, src, trg):
        for child in self.get_children():
            child.substitute(src, trg)
            
    def replace_immediate_constituent(self, old_lf, new_lf):
        # Check for the constituent in each position on the path
        for i,point in enumerate(self):
            if point is old_lf:
                self.pop(i)
                self.insert(i, new_lf)
                
    def get_variables(self):
        return list(set(sum([p.get_variables() for p in self.get_children()], [])))
        
    def get_bound_variables(self):
        return list(set(sum([p.get_bound_variables() for p in self.get_children()], [])))
        
    def get_children(self):
        return list(self)
        
    def alpha_equivalent(self, other, substitution):
        if type(self) != type(other):
            return False
        if len(self) != len(other):
            return False
        # Using izip here means we don't have to produce the whole list if 
        #  something in it fails to match
        for our_child,its_child in izip(self, other):
            if not our_child.alpha_equivalent(its_child, substitution):
                return False
        return True

class ListCat(LogicalForm, Temporal):
    """
    Represents the concatenation of multiple L{List}s. As soon as all of the 
    elements beta-reduce to L{List}s, this will beta-reduce to a list as 
    well. This allows you to concatenate things that will be lists, but 
    aren't yet.
    
    """
    def __init__(self, lists=[], *args, **kwargs):
        LogicalForm.__init__(self, *args, **kwargs)
        Temporal.__init__(self)
        self.lists = lists
        
        for lst in lists:
            lst.parent = self
        
    def __str__(self):
        return "+".join([str(l) for l in self.lists])
    
    def format_result(self):
        # This should appear in results
        return "+".join([l.format_result() for l in self.lists])
        
    def __eq__(self, other):
        return type(self) == type(other) and \
            self.lists == other.lists
    
    def __len__(self):
        return len(self.lists)
    
    def get_start_time(self):
        if len(self.lists) > 0:
            return self.lists[0].get_start_time()
        else:
            return []
        
    def set_time(self, time):
        if len(self.lists) > 0:
            self.lists[0].set_time(time)
        
    def copy(self):
        lists = [l.copy() for l in self.lists]
        return ListCat(lists=lists)
    
    ######## LogicalForm abstract methods
    def alpha_convert(self, src, trg):
        for child in self.get_children():
            child.alpha_convert(src, trg)
            
    def beta_reduce(self, *args, **kwargs):
        # Reduce all children first
        for child in self.get_children():
            child.beta_reduce()
        # See whether all the children are lists now
        if all(isinstance(l, List) for l in self.lists):
            # We're ready to do the concatenation
            biglist = self.lists[0]
            for latter in self.lists[1:]:
                biglist.extend(latter)
            # Now replace ourselves with this path
            self.replace_in_parent(biglist)
            return biglist
        else:
            return self
            
    def substitute(self, src, trg):
        for child in self.get_children():
            child.substitute(src, trg)
            
    def replace_immediate_constituent(self, old_lf, new_lf):
        # Check for the constituent in each of our paths
        for i,lst in enumerate(self.lists):
            if lst is old_lf:
                old_lf.parent = None
                self.lists.pop(i)
                self.lists.insert(i, new_lf)
                new_lf.parent = self
                
    def get_variables(self):
        return list(set(sum([p.get_variables() for p in self.get_children()], [])))
        
    def get_bound_variables(self):
        return list(set(sum([p.get_bound_variables() for p in self.get_children()], [])))
        
    def get_children(self):
        return [p for p in self.lists]
        
    def alpha_equivalent(self, other, substitution):
        if type(self) != type(other):
            return False
        if len(self.lists) != len(other.lists):
            return False
        for our_child,its_child in zip(self.lists, other.lists):
            if not our_child.alpha_equivalent(its_child, substitution):
                return False
        return True
    ########

class Coordination(LogicalForm, Temporal):
    """
    Special operator to represent coordination. Beta reduction collapses 
    nested coordinations into one.
    
    """
    def __init__(self, cadences=[], *args, **kwargs):
        LogicalForm.__init__(self, *args, **kwargs)
        Temporal.__init__(self)
        
        self._cadences = []
        self.extend(cadences)
        
    def __str__(self):
        return "(%s)" % " & ".join([str(c) for c in self._cadences])
    
    def format_result(self):
        return "(%s)" % " & ".join([c.format_result() for c in self._cadences])
        
    def __eq__(self, other):
        return type(self) == type(other) and \
            all(this==that for (this,that) in zip(self,other))
    
    def __len__(self):
        return len(self._cadences)
    def __getitem__(self, i):
        return self._cadences[i]
    def __setitem__(self, i, val):
        self._cadences[i] = val
        val.parent = self
    
    def get_start_time(self):
        if len(self):
            return self[0].get_start_time()
        else:
            return None
    
    def append(self, cad):
        self._cadences.append(cad)
        cad.parent = self
    
    def extend(self, other):
        for cad in other:
            self.append(cad)
    
    def insert(self, i, item):
        self._cadences.insert(i, item)
        item.parent = self
        
    def set_time(self, time):
        if len(self):
            self[0].set_time(time)
        
    def copy(self):
        cads = [c.copy() for c in self]
        return Coordination(cads)
    
    ######## LogicalForm abstract methods
    def alpha_convert(self, src, trg):
        for child in self.get_children():
            child.alpha_convert(src, trg)
            
    def beta_reduce(self, *args, **kwargs):
        # Reduce all children first
        for child in self.get_children():
            child.beta_reduce()
        # Look for coordinations as children and flatten them
        coords = [(i,c) for (i,c) in enumerate(self) if isinstance(c, Coordination)]
        shift = 0
        for i,coord in coords:
            # Remove the coordination from our children
            self._cadences.pop(i+shift)
            shift -= 1
            # Add its children instead
            for child in coord:
                self.insert(i+shift+1, child)
                shift += 1
            # Disown the original child
            coord.parent = None
        return self
            
    def substitute(self, src, trg):
        for child in self.get_children():
            child.substitute(src, trg)
            
    def replace_immediate_constituent(self, old_lf, new_lf):
        # Check for the constituent in each of our paths
        for i,lst in enumerate(self):
            if lst is old_lf:
                old_lf.parent = None
                self._cadences.pop(i)
                self._cadences.insert(i, new_lf)
                new_lf.parent = self
                
    def get_variables(self):
        return list(set(sum([c.get_variables() for c in self.get_children()], [])))
        
    def get_bound_variables(self):
        return list(set(sum([c.get_bound_variables() for c in self.get_children()], [])))
        
    def get_children(self):
        return list(self)
        
    def alpha_equivalent(self, other, substitution):
        if type(self) != type(other):
            return False
        if len(self) != len(other):
            return False
        for our_child,its_child in zip(self, other):
            if not our_child.alpha_equivalent(its_child, substitution):
                return False
        return True
    ########
    
    def _function_apply(self, argument):
        """
        Just as with predicates, reduce when this is applied to a list.
        
        """
        if isinstance(argument, List):
            argument[0] = FunctionApplication(self, argument[0])
            return argument
        else:
            # Do nothing special with the predicate
            return None

class Variable(VariableBase, Temporal):
    """
    Standard variable implementation overridden to add time 
    processing.
    
    """
    def __init__(self, *args, **kwargs):
        VariableBase.__init__(self, *args, **kwargs)
        Temporal.__init__(self)
    
    def set_time(self, time):
        pass
    
    def get_start_time(self):
        return None
    
    def copy(self):
        return Variable(self.name, self.index)
    
    def format_result(self):
        return str(self)

class LambdaAbstraction(LambdaAbstractionBase, Temporal):
    """
    Standard abstraction implementation overridden to add time 
    processing.
    
    """
    VARIABLE_CLASS = Variable
        
    def __init__(self, *args, **kwargs):
        LambdaAbstractionBase.__init__(self, *args, **kwargs)
        Temporal.__init__(self)
        
    def set_time(self, time):
        self.expression.set_time(time)
    
    def get_start_time(self):
        return self.expression.get_start_time()
    
    def result_comma_string(self):
        var = self.variable.format_result()
        ## If the sub-expression is another abstraction, use comma notation for that
        if type(self.expression) == type(self):
            return "%s,%s" % (var, self.expression.result_comma_string())
        else:
            return "%s.%s" % (var, self.expression.format_result())
    
    def format_result(self):
        return "\\%s" % self.result_comma_string()

class FunctionApplication(FunctionApplicationBase, Temporal):
    """
    Standard application implementation overridden to add time 
    processing.
    
    """
    def set_time(self, time):
        self.functor.set_time(time)
        
    def __str__(self):
        """
        Special str to make predicates appear in FOL style, rather than HOL 
        style, which is the default.
        
        """
        if isinstance(self.functor, Predicate):
            return "%s(%s)" % (self.functor.predicate_str(), self.argument)
        else:
            return FunctionApplicationBase.__str__(self)
    
    def format_result(self):
        if isinstance(self.functor, Predicate):
            return "%s(%s)" % (self.functor.predicate_str(), 
                                self.argument.format_result())
        else:
            return self._format(lambda x:x.format_result())
    
    def get_start_time(self):
        return self.functor.get_start_time()

class Predicate(Literal, Temporal):
    """
    Superclass of literal predicates (such as leftonto).
    
    """
    timed_object = True
    
    def __init__(self, *args, **kwargs):
        time = kwargs.pop("time", None)
        duration = kwargs.pop("duration", None)
        Literal.__init__(self, *args, **kwargs)
        Temporal.__init__(self, time=time, duration=duration)
    
    def __eq__(self, other):
        return type(self) == type(other) and \
                self.time == other.time
    
    def __str__(self):
        base = super(Predicate, self).__str__()
        if self.time is not None:
            return "%s@%d" % (base, self.time)
        else:
            return base
    
    def predicate_str(self):
        """
        Returns a string that should be used as the str representation of 
        this predicate when it's used in a function application:
        e.g. leftonto(...)
        
        """
        if self.time is not None and OPTIONS.OUTPUT_ALL_TIMES:
            return "%s@%d" % (self.name, self.time)
        else:
            return self.name
    
    def format_result(self):
        # This shouldn't get called in practice
        return str(self)
            
    def _function_apply(self, argument):
        """
        Implements the special behaviours of predicates when applied to 
        lists.
        
        """
        if isinstance(argument, List):
            argument[0] = FunctionApplication(self, argument[0])
            return argument
        else:
            # Do nothing special with the predicate
            return None
            
    def copy(self):
        return type(self)(time=self.time, duration=self.duration)
        
    def set_time(self, time):
        self.time = earliest_time([time, self.time])
    
    def get_start_time(self):
        return self.time

class Leftonto(Predicate):
    """
    A leftonto predicate literal. Apply leftonto to a path using 
    a function application:
    (leftonto ...)
    
    """
    def __init__(self, *args, **kwargs):
        Predicate.__init__(self, "leftonto", *args, **kwargs)

class Rightonto(Predicate):
    """
    A rightonto predicate literal, analagous to L{Leftonto}.
    
    """
    def __init__(self, *args, **kwargs):
        Predicate.__init__(self, "rightonto", *args, **kwargs)

class Now(Predicate):
    """
    A special predicate that doesn't change its argument at all, except to 
    set its start time to be no later than the start time associated with the 
    predicate.
    
    """
    def __init__(self, *args, **kwargs):
        Predicate.__init__(self, "now", *args, **kwargs)
    
    def predicate_str(self):
        """
        Returns a string that should be used as the str representation of 
        this predicate when it's used in a function application:
        e.g. leftonto(...)
        
        """
        if self.time is not None:
            return "%s@%d" % (self.name, self.time)
            
    def _function_apply(self, argument):
        """
        Override function application behaviour.
        
        If we're applied to a coordinate or a predicate application, we give 
        them our time and burn after reading.
        
        """
        # First apply the general predicate behaviour
        modified = super(Now, self)._function_apply(argument)
        if modified is not None:
            # The parent's reduction transplanted this predicate
            # Return this for now. It'll get beta-reduced again before being 
            #  considered beta-normal and we'll deal with any further 
            #  behaviour then
            return modified
        
        if isinstance(argument, EnharmonicCoordinate):
            # Set the time on the coordinate and return it
            argument.set_time(self.time)
        elif isinstance(argument, FunctionApplication) and \
                isinstance(argument.functor, (Leftonto,Rightonto,Coordination,Now)):
            # These are functors that will never be reduced any further
            # Set the time on the predicate and return the application
            # This includes eliminating recursive Nows, which should take the 
            #  the outermost time
            argument.functor.set_time(self.time)
        elif isinstance(argument, Coordination):
            # Set the time of the first constituent cadence and disappear
            argument[0].set_time(self.time)
        else:
            return None
        return argument


############# Special logical forms for representing paths directly #########
# These should not be used in the parsers anywhere. They're here mainly 
# for the backoff models, which need to produce a LF to store as a result

class PathCoordinate(EnharmonicCoordinate):
    """
    Simple subclass of EnharmonicCoordinate to store points on a path directly.
    Doesn't provide all of the fancy coordinate manipulation stuff provided 
    by EC: use EC itself for that.
    
    This is a special 
    kind of semantics for storing results from backoff models.
    
    """
    def __init__(self, *args, **kwargs):
        self.function = kwargs.pop('function', 'T')
        super(PathCoordinate, self).__init__(*args, **kwargs)
    
    def format_result(self):
        """ In this case, we output the full harmonic coordinate """
        return self.harmonic_str()
        
    def copy(self):
        return PathCoordinate((self.x, self.y), (self.X, self.Y), 
                time=self._time, duration=self._duration, 
                delta=self.delta, function=self.function)
        
    def __eq__(self, other):
        return super(EnharmonicCoordinate, self).__eq__(other) and \
            self.function == other.function
        
    def to_enharmonic_coord(self):
        return EnharmonicCoordinate((self.x, self.y), (self.X, self.Y), 
                time=self._time, duration=self._duration, 
                delta=self.delta)
    
    @staticmethod
    def from_enharmonic_coord(ec):
        return PathCoordinate((ec.x, ec.y), (ec.X, ec.Y), 
                time=ec._time, duration=ec._duration, 
                delta=ec.delta)

class CoordinateList(LogicalForm, Temporal):
    """
    Just a list of enharmonic coordinates, forming a tonal space path. 
    Should not be used as part of the regular semantics. This is a special 
    kind of semantics for storing results from backoff models.
    
    """
    def __init__(self, items=[], *args, **kwargs):
        LogicalForm.__init__(self, *args, **kwargs)
        Temporal.__init__(self)
        self._items = []
        self.extend(items)
        
    def __str__(self):
        return "[%s]" % ", ".join(str(child) for child in self)
    
    def format_result(self):
        return "[%s]" % ", ".join(child.format_result() for child in self)
        
    def __eq__(self, other):
        return type(self) == type(other) and \
            all(this==that for (this,that) in zip(self,other))
        
    def set_time(self, time):
        if len(self) > 0:
            self[0].set_time(time)
        
    def append(self, point):
        """
        Appends the point to the path.
        
        """
        if type(point) != PathCoordinate:
            raise TypeError, "CoordinateList can only store PathCoordinates"
        self._items.append(point)
        point.parent = self
        
    def extend(self, points):
        """
        Appends all points in the given list to the points of the path.
        
        """
        if not all(type(p) == PathCoordinate for p in points):
            raise TypeError, "CoordinateList can only store PathCoordinates"
        self._items.extend(points)
        for p in points:
            p.parent = self
    
    def __len__(self):
        return len(self._items)
        
    def __getitem__(self, i):
        return self._items[i]
    def __setitem__(self, i, val):
        if type(val) != PathCoordinate:
            raise TypeError, "CoordinateList can only store PathCoordinates"
        self._items[i] = val
        val.parent = self
            
    def copy(self):
        items = [p.copy() for p in self]
        return CoordinateList(items=items)
    
    def alpha_convert(self, src, trg):
        # No variables allowed
        return
            
    def beta_reduce(self, *args, **kwargs):
        # Always in BNF
        return self
            
    def substitute(self, src, trg):
        # No variables allowed
        return
            
    def replace_immediate_constituent(self, old_lf, new_lf):
        # Check for the constituent in each position on the path
        for i,point in enumerate(self):
            if point is old_lf:
                old = self._items.pop(i)
                old.parent = None
                self._items.insert(i, new_lf)
                new_lf.parent = self
                
    def get_variables(self):
        return []
        
    def get_bound_variables(self):
        return []
        
    def get_children(self):
        return list(self)
        
    def alpha_equivalent(self, other, substitution):
        # No variables allowed, so only a-equiv if equal
        return self == other

################# Shortcut functions ##############################
def apply(fn, arg, grammar=None):
    """
    Applies fn to arg by creating a FunctionApplication and returns the 
    result. This is used for formalism-unspecific access to this feature.
    
    """
    new_sem = Semantics(FunctionApplication(fn.lf, arg.lf))
    new_sem.beta_reduce()
    return new_sem
    
def compose(f, g, grammar=None):
    """
    Performs logical composition in this semantic formalism.
    
    """
    f_vars = set(f.lf.get_variables())
    g_vars = set(g.lf.get_variables())
    used_vars = f_vars | g_vars
    # Get a variable that isn't found in either function
    var = Variable("x")
    var = next_unused_variable(var, used_vars)
    new_sem = Semantics(
                LambdaAbstraction(\
                    var,
                    FunctionApplication(\
                        f.lf,
                        FunctionApplication(\
                            g.lf,
                            var
                        )
                    )
                )
              )
    new_sem.beta_reduce()
    return new_sem

def multi_apply(*args):
    return multi_apply_base(FunctionApplication, *args)
    
def multi_abstract(*args):
    return multi_abstract_base(LambdaAbstraction, *args)
    
def concatenate(lst1, lst2):
    """
    Returns the concatenation of the two lists.
    Uses existing instances passed in, so make sure they're copies 
    if you don't want your original objects modified.
    
    """
    cat = Semantics(ListCat([lst1.lf, lst2.lf]))
    cat.beta_reduce()
    return cat
    
################ Utilities #############
def make_absolute_lf_from_relative(sems, root_coord):
    if isinstance(sems, Semantics):
        make_absolute_lf_from_relative(sems.lf, root_coord)
    elif isinstance(sems, LexicalCoordinate):
        # This is the only thing that actually changes
        # Replace all lexical coordinates with actual coordinates, 
        #  now we know what they're relative to
        abs_coord = sems.resolve(root_coord)
        sems.replace_in_parent(abs_coord)
    else:
        # Otherwise just recurse to children
        children = [c for c in sems.get_children()]
        for child in children:
            make_absolute_lf_from_relative(child, root_coord)

def list_lf_to_coordinates(lst, start_block=(0,0)):
    """
    Produces a list of (x,y) coordinates in the tonal space, given 
    a L{List} or L{CoordinateList}.
    
    @type lst: L{List}
    @param lst: list from the semantics representing constraints on a TS path
    @type start_block: pair of ints
    @param start_block: enharmonic block to start in (if other than 
        the default (0,0))
    @return: 2D coordinates of the path through the tonal space and the 
        times at which they were reached.
    
    """
    if isinstance(lst, CoordinateList):
        path = [p.harmonic_coord for p in lst]
        times = [p.time for p in lst]
        return zip(path, times)
        
    def _remove_nows(el):
        if isinstance(el, FunctionApplication) and isinstance(el.functor, Now):
            # Remove this: recurse to argument
            return _remove_nows(el.argument)
        else:
            for child in el.get_children():
                el.replace_immediate_constituent(child, _remove_nows(child))
            return el
    
    def _to_coords(el):
        if isinstance(el, EnharmonicCoordinate):
            # Coordinate just becomes a single-element path
            return [(EnharmonicCoordinate((el.x,el.y)), el.time)]
        elif isinstance(el, GhostCoordinate):
            # Treat the same as a coordinate at this stage
            return [(EnharmonicCoordinate((el.coordinate.x,el.coordinate.y)), el.coordinate.time)]
        elif isinstance(el, FunctionApplication):
            # If we're applying to a ghost, remove it once we're done
            remove_last = isinstance(el.argument, GhostCoordinate)
            # Recursively get a path for the argument
            argpath = _to_coords(el.argument)
            # Add something to the path depending on the functor
            if isinstance(el.functor, Leftonto):
                fullpath = [((argpath[0][0]+(1,0)), el.functor.time)] + argpath
            elif isinstance(el.functor, Rightonto):
                fullpath = [((argpath[0][0]+(-1,0)), el.functor.time)] + argpath
            elif isinstance(el.functor, Coordination):
                # Apply each coordinated cadence to the resolution
                resolution = Semantics(GhostCoordinate(argpath[0][0]))
                cadpaths = []
                for cad in el.functor:
                    # Apply the cadence to its resolution
                    # This will beta-reduce
                    cadsem = apply(Semantics(cad), resolution.copy())
                    cadpath = _to_coords(cadsem.lf)
                    # String together the paths from each coordinated cadence
                    cadpaths.extend(cadpath)
                # Follow up the cadences with their joint resolution
                fullpath = cadpaths + argpath
            else:
                raise SemanticsPostProcessError, "unknown functor %s" % \
                    el.functor
            
            # Remove the ghost coordinate
            if remove_last:
                fullpath = fullpath[:-1]
            return fullpath
        elif isinstance(el, Coordination):
            raise SemanticsPostProcessError, "can't get a path for a "\
                "coordination that's not applied to anything: %s" % el
        else:
            raise SemanticsPostProcessError, "don't know how to get a path "\
                "for the lf %s" % el
    
    start_point = None
    path = []
    # Get a path for each element in the list
    for lf in lst:
        # There may be Now predicates in the lf
        # Remove them before continuing
        lf = _remove_nows(lf)
        
        coords,times = zip(*_to_coords(lf))
        # Shift this fragment to be as close as possible to the end of the previous
        if len(path) == 0:
            # Nothing on the path yet: start in the chosen start block
            new_block = start_block
            after_block = coords[0].block_coord
        else:
            # Translate the second path so that they make the nearest join possible
            before = path[-1][0].harmonic_coord
            before_block = path[-1][0].block_coord
            after = coords[0].harmonic_coord
            after_block = coords[0].block_coord
            
            # Get the start point (2nd path) relative to the end point (1st path)
            diff = (after[0]-before[0], after[1]-before[1])
            # Project this onto ET
            rel_pitch = coordinate_to_et_2d(diff)
            """
            Each ET pitch has a closest instance to the start point: choose 
            the one for this pitch.
            They're in a costellation around the base point (before) like this:
                 VI  III VII
            bVII IV   I   V   II
             bV  bII bVI bIII
            
            """
            rel_coord = {
                0 : (0,0),
                1 : (-1,-1),
                2 : (2,0),
                3 : (1,-1),
                4 : (0,1),
                5 : (-1,0),
                6 : (-2,-1), # This is an arbitrary choice: (2,1) is the same distance
                7 : (1,0),
                8 : (0,-1),
                9 : (-1,1),
                10 : (-2,0),
                11 : (1,1),
            }[rel_pitch]
            # Decide what coordinate the 2nd path should start on
            new_start = (before[0]+rel_coord[0], before[1]+rel_coord[1])
            # Work out how many blocks we must shift the 2nd path by to do this
            new_start_coord = EnharmonicCoordinate.from_harmonic_coord(new_start)
            assert coords[0].zero_coord == new_start_coord.zero_coord
            new_block = new_start_coord.block_coord
        block_shift = (new_block[0]-after_block[0], new_block[1]-after_block[1])
        
        # Shift happens
        for coord in coords:
            coord.X += block_shift[0]
            coord.Y += block_shift[1]
        path.extend(zip(coords,times))
    return [(coord.harmonic_coord, time) for (coord, time) in path]

def list_lf_to_functions(lst):
    """
    Like L{list_lf_to_coordinates}, but produces a list of (function,time) 
    pairs instead of (coordinate,time).
    
    @type lst: L{List}
    @param lst: list from the semantics representing constraints on a TS path
    @return: function strings of points on the path through the tonal space 
        and the times at which they were reached.
    
    """
    if isinstance(lst, CoordinateList):
        funs = [p.function for p in lst]
        times = [p.time for p in lst]
        return zip(funs, times)
    
    def _to_funs(el):
        if isinstance(el, EnharmonicCoordinate):
            # Coordinate just becomes a single-element path
            return [("T", EnharmonicCoordinate((el.x,el.y)), el.time)]
        elif isinstance(el, GhostCoordinate):
            # This should get removed, so don't put in a real function: we 
            #  want the error to be clear if it gets included
            return [("GHOST", 
                     EnharmonicCoordinate((el.coordinate.x,el.coordinate.y)), 
                     el.coordinate.time)]
        elif isinstance(el, FunctionApplication):
            # If we're applying to a ghost, remove it once we're done
            remove_last = isinstance(el.argument, GhostCoordinate)
            # Recursively get a function list for the argument
            argpath = _to_funs(el.argument)
            # Add something to the path depending on the functor
            if isinstance(el.functor, Leftonto):
                fullpath = [("D", (argpath[0][1]+(1,0)), el.functor.time)] + argpath
            elif isinstance(el.functor, Rightonto):
                fullpath = [("S", (argpath[0][1]+(-1,0)), el.functor.time)] + argpath
            elif isinstance(el.functor, Coordination):
                # Apply each coordinated cadence to the resolution
                resolution = Semantics(GhostCoordinate(argpath[0][1]))
                cadpaths = []
                for cad in el.functor:
                    # Apply the cadence to its resolution
                    # This will beta-reduce
                    cadsem = apply(Semantics(cad), resolution.copy())
                    cadpath = _to_funs(cadsem.lf)
                    # String together the paths from each coordinated cadence
                    cadpaths.extend(cadpath)
                # Add folow up the cadences with their joint resolution
                fullpath = cadpaths + argpath
            else:
                raise SemanticsPostProcessError, "unknown functor %s" % \
                    el.functor
            
            # Remove the ghost coordinate
            if remove_last:
                fullpath = fullpath[:-1]
            return fullpath
        elif isinstance(el, Coordination):
            raise SemanticsPostProcessError, "can't get a path for a "\
                "coordination that's not applied to anything: %s" % el
        else:
            raise SemanticsPostProcessError, "don't know how to get a path "\
                "for the lf %s" % el
    
    start_point = None
    path = []
    # Get a path for each element in the list
    # When getting the coordinates we do shifting stuff here, but for functions
    #  we can just concatenate
    path = sum((_to_funs(lf) for lf in lst), [])
    # Get rid of the coordinates
    funs,coords,times = zip(*path)
    path = zip(funs,times)
    return path

def sign_to_coordinates(sign):
    return semantics_to_coordinates(sign.semantics)

def semantics_to_coordinates(sems):
    """
    Generates a list of (coordinates,time) tuples given a parse result.
    
    @raise ValueError: if the result can't produce a list of coordinates.
    
    """
    if not isinstance(sems.lf, (List, CoordinateList)):
        # This result isn't a list, so we can't generate coordinates from it
        raise ValueError, "can't generate coordinates from a %s" % \
                type(sems.lf).__name__
    return list_lf_to_coordinates(sems.lf)
    
def semantics_to_functions(sems):
    """
    Generates a list of (function,time) tuples given a parse result.
    
    @raise ValueError: if the result can't produce a list of coordinates.
    
    """
    if not isinstance(sems.lf, (List, CoordinateList)):
        # This result isn't a list, so we can't generate functions from it
        raise ValueError, "can't generate a function list from a %s" % \
                type(sems.lf).__name__
    return list_lf_to_functions(sems.lf)
    

def backoff_states_to_lf(states):
    """
    Builds a logical form given a list of states and the 
    chords they were assigned to. Accepts a list of labels,time
    and return a logical form for the formalism (a L{Semantics} in this 
    case).
    
    This uses the special logical form classes L{CoordinateList} and 
    L{PathCoordinate}.
    
    """
    from jazzparser.data import Chord, Fraction
    
    points = []
    
    # Special case for the first point
    ((first_point,first_fun), first_time) = states[0]
    first = PathCoordinate.from_enharmonic_coord(
                EnharmonicCoordinate((first_point[2],first_point[3])))
    first.fun = first_fun
    first.time = first_time
    
    points = [first]
    for ((point,fun),time) in states[1:]:
        # Reconstruct a path point from each label
        dX,dY,x,y = point
        # Get the nearest (x,y) to the previous point
        nearest = points[-1].nearest((x,y))
        # Now shift it by the requested amount
        nearest.X += dX
        nearest.Y += dY
        
        coord = PathCoordinate.from_enharmonic_coord(nearest)
        coord.function = fun
        coord.time = time
        points.append(coord)
        
    if len(points):
        # Get rid of any points that just repeat the previous one
        previous = points[0]
        remove = []
        for point in points[1:]:
            if point.harmonic_coord == previous.harmonic_coord and \
                    point.function == previous.function:
                remove.append(id(point))
            previous = point
        points = [p for p in points if id(p) not in remove]
        
    # Create a path out of these points
    path = CoordinateList(items=points)
    
    return Semantics(path)


def semantics_to_keys(sems):
    """
    Gets a list of keys implied by a logical form.
    
    """
    from jazzparser.utils.tonalspace import coordinate_to_et_2d
    
    def _get_key(lf):
        if isinstance(lf, EnharmonicCoordinate):
            # TS point: return the key root
            return coordinate_to_et_2d(lf.zero_coord)
        elif isinstance(lf, FunctionApplication):
            # It so happens that every function application's key comes from 
            #  the right branch - its argument
            return _get_key(lf.argument)
        else:
            raise KeyInferenceError, "got unexpected LF in key inference: %s" \
                    % lf
    
    # Recurse over the cadences
    keys = []
    last_key = None
    for lf in sems.lf:
        # Work out the key of this cadence
        key = _get_key(lf)
        # Only include this key if it's changed since the last cadence
        if key != last_key:
            keys.append((key, lf.get_start_time()))
            last_key = key
    return keys


def semantics_from_string(string):
    """
    Builds a L{Semantics} instance from a string representation of the logical 
    form. This is mainly for testing and debugging and shouldn't be used in 
    the wild (in the parser, for example). This is not how we construct 
    logical forms out of the lexicon: they're specified in XML, which is a 
    safer way to build LFs, though more laborious to write.
    
    The strings may be constructed as follows.
    
    B{Tonic semantics}: "<x,y>". This will build an L{EnharmonicCoordinate}.
    
    B{List}: "[ITEM0, ITEM1, ...]". This will build a L{List}.
    
    B{List concatenation}: "LIST0+LIST1", that is with infix notation.
    This will build a L{ListCat}.
    
    B{Variable}: "$x0". Begin every variable with a $, as if you're writing PHP 
    or Bash, or something. Use any variable name and, optionally, a number. 
    If no number is given, 0 will be used by default.
    
    B{Predicates} - leftonto, rightonto: "leftonto(...)", etc. Builds a 
    L{FunctionApplication} with the predicate as its functor.
    
    B{Now}: "now@x(...)". Works like the other predicates, but has the special 
    "@x" value to give it a time.
    
    B{Lambda abstraction}: "\\$x.EXPR". Use a backslash to represent a lambda.
    You can have multiple abstracted variables, which will result in multiple 
    nested abstractions. EXPR can be any expression.
    
    B{Function application}: "(FUNCTOR ARGUMENT)". Always enclose a function 
    application in brackets, even if you wouldn't write them.
    
    Note that the output is not beta-reduced.
    
    """
    def _find_matching(s, opener="[", closer="]"):
        opened = 0
        for i,char in enumerate(s):
            if char == closer:
                if opened == 0:
                    return i
                else:
                    opened -= 1
            elif char == opener:
                opened += 1
        # Matching brace not found
        raise SemanticsStringBuildError, "%s was not matched by a %s in %s" % \
            (opener, closer, s)
    
    # Recursive function to build the LF from a string
    def _build_lf(text):
        text = text.strip()
        if text.startswith("<"):
            # Enharmonic coordinate
            end = text.find(">")
            if end == -1:
                raise SemanticsStringBuildError, "unclosed enharmonic "\
                    "coordinate: %s" % text
            coord = text[1:end].split(",")
            if len(coord) != 2:
                raise SemanticsStringBuildError, "enharmonic coordinate must "\
                    "be a pair of values: %s" % text
            coord = int(coord[0]), int(coord[1])
            lf = EnharmonicCoordinate.from_harmonic_coord(coord)
            leftover = text[end+1:]
        elif text.startswith("["):
            # List
            # Find where it ends
            end = _find_matching(text[1:]) + 1
            # Build each list item recursively
            remainder = text[1:end]
            items = []
            # Keep processing each item until we've done them all
            while len(remainder):
                item, remainder = _build_lf(remainder)
                remainder = remainder.strip()
                if len(remainder):
                    if not remainder.startswith(","):
                        raise SemanticsStringBuildError, "could not parse %s in "\
                            "logical form %s" % (remainder, string)
                    else:
                        remainder = remainder[1:]
                items.append(item)
            lf = List(items=items)
            leftover = text[end+1:]
        elif text.startswith("$"):
            # Variable name
            # Ends at next non-alphanumeric character
            non_alph = re.compile(r'[^a-zA-Z0-9]')
            match = non_alph.search(text[1:])
            if match is None:
                # or end of string
                end = len(text)
            else:
                end = match.start() + 1
            
            # Split the number off the variable number
            var_splitter = re.compile(r'^(?P<name>.+?)(?P<number>\d*)$')
            match = var_splitter.match(text[1:end])
            if match is None:
                raise SemanticsStringBuildError, "invalid variable name '%s'" % \
                    text[:end]
            matchgd = match.groupdict()
            var_name,var_num = matchgd['name'], matchgd['number']
            if var_num == "":
                var_num = 0
            else:
                var_num = int(var_num)
            lf = Variable(var_name, var_num)
            leftover = text[end+1:]
        elif text.startswith("leftonto(") or text.startswith("rightonto(") or \
                text.startswith("now@"):
            # Predicate
            if text.startswith("leftonto("):
                predicate = "leftonto"
                pred_obj = Leftonto()
                pred_len = len(predicate)
            elif text.startswith("rightonto("):
                predicate = "rightonto"
                pred_obj = Rightonto()
                pred_len = len(predicate)
            else:
                predicate = "now"
                pred_obj = Now()
                # Get the time value
                pred_len = text.find("(")
                time = int(text[4:pred_len])
                pred_obj.time = time
            # Recursively process the argument of the predicate application
            # Find the closing bracket
            end = _find_matching(text[pred_len+1:], 
                                 opener="(", closer=")") + pred_len + 1
            arg,rest = _build_lf(text[pred_len+1:end])
            
            # Check we used the whole 
            if len(rest.strip()):
                raise SemanticsStringBuildError, "could not parse '%s' in "\
                    "argument to %s in '%s'" % (rest,predicate,string)
            
            # Build the logical form
            lf = FunctionApplication(
                        pred_obj,
                        arg)
            leftover = text[end+1:]
        elif text.startswith("\\"):
            # Lambda abstraction
            # Look for a . that marks the end of the variable name
            dot = text.find(".")
            if dot == -1:
                raise SemanticsStringBuildError, "lambda abstraction needs a "\
                    "dot: %s (in %s)" % (text,string)
            # Build the LF for the variable(s)
            var_text = text[1:dot]
            variables = []
            # Keep getting variables, separated by commas
            while len(var_text.strip()):
                var_text.lstrip(",")
                variable,var_text = _build_lf(var_text)
                if not isinstance(variable, Variable):
                    raise SemanticsStringBuildError, "bad variable %s in "\
                        "lambda abstraction (%s)" % (variable,string)
                variables.append(variable)
            
            # Continue to build the LF for the abstracted expression
            expr, leftover = _build_lf(text[dot+1:])
            
            args = variables + [expr]
            lf = multi_abstract(*args)
        elif text.startswith("("):
            # Function application or just brackets
            # Look for a matching bracket
            end = _find_matching(text[1:], opener="(", closer=")") + 1
            # Now parse the stuff between the brackets
            lf,rest = _build_lf(text[1:end])
            # See whether there's a second expression
            if len(rest.strip()):
                # Must be a fun app
                second_lf,rest = _build_lf(rest)
                # There shouldn't be any more
                if len(rest.strip()):
                    raise SemanticsStringBuildError, "don't know what to do "\
                        "with '%s' in '%s'" % (rest, string)
                lf = FunctionApplication(lf, second_lf)
            # Otherwise we just return the stuff between the brackets
            leftover = text[end+1:]
        else:
            raise SemanticsStringBuildError, "could not parse '%s' in '%s'" % \
                (text,string)
        
        # Check for infix operators
        leftover = leftover.strip()
        if leftover.startswith("+"):
            # List concatenation
            # Process the rest of the string
            second_lf, leftover = _build_lf(leftover[1:])
            lf = ListCat([lf, second_lf])
        elif leftover.startswith("&"):
            # Coordination
            second_lf, leftover = _build_lf(leftover[1:])
            lf = Coordination([lf, second_lf])
        
        return lf, leftover
    
    # Build a logical form for the whole string
    lf,leftover = _build_lf(string.strip())
    if len(leftover.strip()):
        raise SemanticsStringBuildError, "could not parse the rest of the "\
            "string '%s' in '%s'" % (leftover,string)
    
    # Wrap it up in a Semantics
    return Semantics(lf)

class SemanticsStringBuildError(Exception):
    pass
    
class SemanticsPostProcessError(Exception):
    pass

class KeyInferenceError(Exception):
    pass
