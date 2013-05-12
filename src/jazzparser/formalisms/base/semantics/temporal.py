"""Temporal additions to basic lambda calculus semantics.

Many formalisms will store temporal information along with their 
logical forms. This module provides the basic stuff that's needed 
to add temporal information to a semantics.

Note that this is completely separate from the lambda calculus base 
classes, so they may be used without temporal information.

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

from jazzparser.data import Fraction
import copy, logging

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class Temporal(object):
    """
    Adds temporal information to a logical form.
    Logical form classes that want to store temporal information should 
    inherit from the approriate base logical form class and this.
    
    Note that you must inherit from the logical form class as well: 
    just subclassing this may result in horrible things happening.
    You should also call Temporal's init when initializing subclasses.
    """
    timed_object = False
    
    def __init__(self, duration=None, time=None):
        # Only store these values on timed objects
        if self.timed_object:
            self._duration = duration
            self._time = time
    
    def get_literal_time_list(self):
        """
        Return a list of the time values of only predicates and tonal 
        denotations. The list is strictly in the sequential order
        of the harmonic movements.
        
        May be overridden by subclasses.
        
        @note: this used to be an abstract method, which subclasses 
        were required to override. Since it is not used much (or at 
        all) in recent formalisms, it is no longer abstract and will 
        default to returning an empty list if not overridden.
        
        """
        return []
    
    def get_time_list(self):
        """
        Returns a list of the time values of the constituents of the 
        logical form, including non-literal elements if they have times 
        (e.g. variables).
        
        """
        time_list = []
        if self.timed_object:
            # First find our own time
            time_list.append(self.time)
            
        for child in self.get_children():
            # Get a similar list from each child and join them all together
            time_list.extend(child.get_time_list())
        return time_list
    
    def get_path_times(self):
        """
        Returns a list of times at which each point on the path occurs,
        I{only} if the semantics represents a list of points, or 
        something that could be converted into one trivially.
        
        @raise TemporalError: if the LF does not represent a 
        tonal space path.
        
        """
        raise TemporalError, "%s cannot provide tonal space path timings" % type(self).__name__
    
    def set_all_times(self, time):
        """
        Recursively sets the time property on this and all children 
        that can accept a time value.
         
        """
        self.time = time
        for child in self.get_children():
            child.set_all_times(time)
    
    def __get_duration(self):
        return self._duration if self.timed_object else None
    def __set_duration(self,dur):
        self._duration = dur if self.timed_object else None
    duration = property(__get_duration, __set_duration)
    """The duration of this phrase. Always None for types with timed_object=False."""
    
    def __get_time(self):
        return self._time if self.timed_object else None
    def __set_time(self, time):
        self._time = time if self.timed_object else None
    time = property(__get_time, __set_time)
    """The onset time of this phrase. Always None for types with timed_object=False."""
    
    def set_time(self, time):
        """
        Should be overridden by subclasses.
        
        Sets the start time of this logical form. This is different to 
        just setting the time property: using set_time() may pass the 
        time property down to its children if that is appropriate for 
        the semantic type.
        
        It is also distinct from set_all_times(), 
        which recursively sets the time on all children.
        
        This must be provided by all subclasses.
        
        """
        raise NotImplementedError, "%s does not provide a set_time()" % type(self).__name__

    def simultaneous(self, other):
        """
        Checks recursively that two logical forms, assumed equal, 
        have the same timings.
        Note that it is important that this is only called when 
        self == other, or else bad things might happen.
        
        """
        return self.time != other.time and \
            all(child1.simultaneous(child2) for (child1, child2) in zip(self.get_children(), other.get_children()))

class TemporalSemantics(object):
    """
    Adds temporal semantics to the Semantics root class.
    """
    def _get_duration(self):
        return self.lf.duration
    def _set_duration(self, value):
        self.lf.duration = value
    duration = property(_get_duration, _set_duration)
    
    def get_time_list(self):
        return self.lf.get_time_list()
    
    def set_all_times(self, time):
        """@see: L{Temporal.set_all_times}"""
        self.lf.set_all_times(time)
    
    def set_time(self, time):
        """@see: L{Temporal.set_time}"""
        self.lf.set_time(time)
        
    def get_path_times(self):
        """
        @see: L{Temporal.get_path_times}
        """
        return self.lf.get_path_times()

def temporal_rule_apply(semantics_only=False):
    """
    A generic decorator to wrap any rule application to perform the 
    time assignment manipulation of the semantics.
    
    @type semantics_only: bool
    @param semantics_only: if True, assumes this is an apply_rule_semantics(), 
        so the results will be logical forms only (not signs)
    
    """
    def wrap(main_fun):
        def apply_rule(self, cat_list, *args, **kwargs):
            # Now hand over to the main apply_rule function
            res = main_fun(self, cat_list, *args, **kwargs)
            if res is not None:
                # Combine the durations of the inputs, if they exist
                if all(cat.semantics.duration is not None for cat in cat_list):
                    duration = sum(cat.semantics.duration for cat in cat_list)
                    # Set the duration on the result(s)
                    for r in res:
                        if semantics_only:
                            r.duration = duration
                        else:
                            r.semantics.duration = duration
            return res
        return apply_rule
    return wrap
    
# These old specific rule type decorators have now been replaced by a 
#  generic decorator
temporal_comp_apply = temporal_rule_apply
""" @deprecated: use temporal_rule_apply """
temporal_app_apply = temporal_rule_apply
""" @deprecated: use temporal_rule_apply """

class TempralError(Exception):
    pass

def earliest_time(times):
    """
    Simple utility to pick the earliest of a list of times (which 
    may include Nones).
    
    Will return None if there are no times that aren't None.
    
    """
    notnones = [t for t in times if t is not None]
    if len(notnones) == 0:
        return None
    return min(notnones)
