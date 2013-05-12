"""Jazz Parser extensions to NLTK classes.

NLTK is optionally used by the Jazz Parser.
This module provides extensions to NLTK classes. You shouldn't load 
anything from this package unless you're willing to have errors 
raised in the case that NLTK isn't installed, alerting the user that 
they can't use this feature without NLTK.

NLTK is imported initially here so that it gets tested when the 
module is loaded.

Note: the way the codebase is currently setup, you'd never not have NLTK 
installed (it's an external). However, it's theoretically nice to keep 
stuff the depends directly on NLTK separate so that we can handle its 
absence graciously.

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


from jazzparser.utils.base import load_optional_package
# Check NLTK can be imported
load_optional_package('nltk', 'NLTK', "load the Jazz Parser NLTK extensions")

from .storage import FreqDistStorer, ConditionalProbDistStorer, MLEProbDistStorer, \
                ConditionalFreqDistStorer, LaplaceProbDistStorer, \
                WittenBellProbDistStorer, GoodTuringProbDistStorer, \
                DictionaryProbDistStorer, DictionaryConditionalProbDistStorer, \
                MutableProbDistStorer
from .hmm import HiddenMarkovModelTaggerStorer
from .probability import CutoffFreqDistStorer, CutoffConditionalFreqDistStorer

# Any storers defined should be listed here
# See the storage module for more info about these
STORERS = [
    HiddenMarkovModelTaggerStorer,
    FreqDistStorer,
    ConditionalProbDistStorer,
    MLEProbDistStorer,
    ConditionalFreqDistStorer,
    LaplaceProbDistStorer,
    WittenBellProbDistStorer,
    GoodTuringProbDistStorer,
    CutoffFreqDistStorer,
    CutoffConditionalFreqDistStorer,
    DictionaryProbDistStorer,
    DictionaryConditionalProbDistStorer,
    MutableProbDistStorer,
]
