"""Assignment utilities for the Jazz Parser.

These are generic tools for assignments. They can be used for different 
sorts of assignment and are useful for unification frameworks (e.g.
the music_roman unification procedure).

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

import logging
# Get the logger from the logging system
logger = logging.getLogger("main_logger")


class EquivalenceAssignment(dict):
	"""
	A special kind of dict that stores not only a mapping from keys to 
	values, but also equivalence classes of keys. Manages the equivalence 
	classes so that values get assigned to all the keys as soon as 
	one of them is given a value.
	"""
	def __init__(self, *args, **kwargs):
		super(EquivalenceAssignment, self).__init__(*args, **kwargs)
		self.classes = []
		self.inconsistent = False
		
	def _pop_class(self, key):
		"""
		Return the equivalence class including the key, if one 
		exists, removing from the list of classes.
		"""
		for i,cls in enumerate(self.classes):
			if key in cls:
				return self.classes.pop(i)
		return None
		
	def _get_class(self, key):
		for cls in self.classes:
			if key in cls:
				return cls
		return None
	
	def __setitem__(self, key, value):
		# Check the equivalence classes for other keys equivalent to this one
		cls = self._pop_class(key)
		if key in self and self[key] is not None:
			# We already have a value for this key.
			# Resolve the conflict in a way appropriate to the data type.
			value = self.resolve_conflict(self[key], value)
		super(EquivalenceAssignment, self).__setitem__(key, value)
		# Set all the other keys in the equiv class
		if cls is not None:
			for eq_key in cls:
				# This recursively call setitem, but will not find the eq 
				#  class again, because we popped it.
				self[eq_key] = value
				
	def add_equivalence(self, key1, key2):
		""" Asserts the equivalence of the two keys. """
		if key1 == key2:
			# They're equal: no need to assert equivalence
			return
		# Look for an existing class for each key
		key1_class = self._get_class(key1)
		key2_class = self._get_class(key2)
		if key1_class is not None and key2_class is not None:
			if key1_class is key2_class:
				# They're already equivalent
				return
			# Both keys are already in classes. Merge them
			self.classes.remove(key1_class)
			self.classes.remove(key2_class)
			self.classes.append(key1_class | key2_class)
		elif key1_class is not None:
			# key1 is already in a class. Add key2
			key1_class.add(key2)
		elif key2_class is not None:
			# key2 is already in a class. Add key1
			key2_class.add(key1)
		else:
			# Neither key was found. Add a new equivalence class
			self.classes.append(set([key1, key2]))
		# Added an equivalence: set any values again to make sure the 
		#  whole class gets the value
		if key1 in self:
			# setitem will take care of the equivalences
			self[key1] = self[key1]
		if key2 in self:
			self[key2] = self[key2]
		
	def resolve_conflict(self, old_value, new_value):
		"""
		When two values are fighting for the same key, this method 
		decides which to pick, or raises an exception if the conflict 
		cannot be resolved (i.e. incompatible values).
		By default this raises an exception if the values are not equal.
		Should be overridden by subclasses.
		"""
		if old_value != new_value:
			self.inconsistent = True
			raise EquivalenceAssignment.IncompatibleAssignmentError, \
				"%s and %s cannot be assigned to the same key" % (old_value, new_value)
		return old_value
		
	def update(self, ass):
		if isinstance(ass, EquivalenceAssignment):
			# Another eq assignment: update including the eq classes
			for cls in ass.classes:
				if len(cls) > 1:
					cls = list(cls)
					first = cls[0]
					for other in cls[1:]:
						self.add_equivalence(first, other)
		super(EquivalenceAssignment, self).update(ass)
		
	def __str__(self):
		return "<%s | [%s]>" % (", ".join(["%s=%s" % ass for ass in self.items()]),
								",".join(["(%s)" % ",".join(["%s" % key for key in cls]) for cls in self.classes]))
			
	class IncompatibleAssignmentError(Exception):
		pass
