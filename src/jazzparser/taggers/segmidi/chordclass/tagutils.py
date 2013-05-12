"""Misc utilities used by the chordclass tagger.

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

class CategoryProcessChart(object):
	"""
	CKY chart for the mini-parsing task we need to do to prepare the categories.
	"""
	def __init__(self, length):
		self.length = length
		# Prepare the chart representation
		chart = []
		for i in range(length):
			row = []
			for j in range(length):
				row.append([])
			chart.append(row)
		self._chart = chart
		
	def get_cell(self, start, end):
		return self._chart[start][end-1]
		
	def add_span(self, start, end, val):
		self._chart[start][end-1].append(val)
	
	def __str__(self):
		# Just for debugging, doesn't need to look good
		return str(self._chart)

def prepare_categories(timesteps):
	"""
	Processes the output from decoding the model in the form of a set of 
	top tags for each timestep. We need to find each possible sequence of 
	identical tags and combine then into a single span so that the 
	self-transition gets interpreted as a continuation of the category. 
	We also want to keep the smaller spans, right down to the single-timestep 
	categories, so that they can be considered by the parser in combination 
	with other spans that would otherwise overlap.
	
	We do this using a little CKY chart parser.
	
	"""
	T = len(timesteps)
	chart = CategoryProcessChart(T)
	# Label the tags with their priority
	timesteps = [list(enumerate(timestep)) for timestep in timesteps]
	
	# Initialize the chart
	for (time,tags) in enumerate(timesteps):
		for tag in tags:
			chart.add_span(time, time+1, tag)
	
	# CKY loops
	for end in range(2, T+1):
		for start in range(0, end-1):
			for middle in range(start+1, end):
				# Look for identical tags between these two cells
				first = chart.get_cell(start, middle)
				second = chart.get_cell(middle, end)
				for priority1,(prob1,tag1) in first:
					for priority2,(prob2,tag2) in second:
						if tag1 == tag2:
							# Found a repeated tag: add it as a span
							# Take the product of the probabilities as the 
							#  probability of the combined tag
							chart.add_span(start, end, \
								(max(priority1, priority2), (prob1+prob2, tag1)))
	
	# Get all the spans that result from the parse
	prioritized_spans = {}
	for start in range(0, T):
		for end in range(start+1, T+1):
			for (priority,(prob,tag)) in chart.get_cell(start,end):
				prioritized_spans.setdefault(priority, []).append((start, end, (prob,tag)))
	# Return them grouped by priority and in descending order of priority
	grouped_spans = [spans for (priority,spans) in sorted(prioritized_spans.items())]
		
	return grouped_spans
