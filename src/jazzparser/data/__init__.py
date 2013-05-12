"""Data structures for the Jazz Parser.

Basic data types for the Jazz Parser.

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

import copy, re
import logging

from jazzparser.utils.base import filter_latex
from jazzparser.utils.chords import int_to_chord_numeral, chord_numeral_to_int, \
                        int_to_ly_note, ChordError, int_to_pitch_class, \
                        pitch_class_to_int
from jazzparser.data.db_mirrors import Chord as MirrorChord

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

ROMAN_REGEX = re.compile(r"""
    ^                                       # Start at the very beginning
    (?P<root>
      (?P<accidental>b|\#)?                 # Flat or sharp, or neither
      (?P<numeral>I{1,3}|I?V|VI{0,2}|X|Y|Z) # Chord numeral: I-III or IV-V or V-VII; or variable: X, Y, Z
    )
    (?P<type>m(7|,b5|,M7)?|aug(7|,M7)?
        |o7|%7|sus4(,7)?|b5(,7|,M7)?
        |M7|7|\#5,m7)?                       # All the chord types (triad+1) we allow
    (\((?P<additions>6|9|b9|b10
        |13|\+9|\+11)\))?                   # Extra additions must come after the chord type in brackets
    $                                       # Match the whole string
""", re.VERBOSE)

PITCH_REGEX = re.compile(r"""
    ^
    (?P<root>
      (?P<pitch>[A-G])                  # Chord numeral: I-III or IV-V or V-VII; or variable: X, Y, Z
      (?P<accidental>b|\#)?             # Flat or sharp, or neither
    )
    (?P<type>m(7|,b5|,M7)?|aug(7|,M7)?
        |o7|%7|sus4(,7)?|b5(,7|,M7)?
        |M7|7|\#5,m7)?                  # All the chord types (triad+1) we allow
    (\((?P<additions>6|9|b9|b10
        |13|\+9|\+11)\))?               # Extra additions must come after the chord type in brackets
    $
""", re.VERBOSE)


class Chord(object):
    """
    A Chord object represents a single chord in an input
    sequence to the parser.
    
    This was the original way of processing input to the parser and still 
    lurks around. However, a better representation is provided by 
    L{jazzparser.data.db_mirrors.Chord}, which is specifically designed 
    to replicate the data structure in the corpus database.
    Instances of this class can be converted to a db-mirror chord using 
    L{to_db_mirror}. This class is now used mainly for processing textual input.
    
    """
    # These mirror the table sequences_chordtype in the annotator db
    TYPE_SYMBOLS = {
        1 : "",
        2 : "m", 
        3 : "M7", 
        4 : "o7",
        5 : "%7", 
        6 : "aug",
        7 : "m,b5",
        8 : "b5",
        9 : "m,M7",
        10 : "7",
        11 : "m7",
        12 : "aug7",
        13 : "b5,7",
        14 : "sus4",
        15 : "sus4,7",
        16 : "aug,M7",
        17 : "b5,M7",
        18 : "#5,m7",
    }
    # The types that can function as 7 chords
    SEVEN_TYPES = [ 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 18 ]
    # Any chord with additions == one of these has an implied 7 in it
    SEVEN_IMPLIED_ADDITIONS = [ "9", "b9", "b10", "13", "+9", "+11" ]
    # Certain chord types should be mapping to other types to realise an 
    #  implied 7 if one exists in the additions
    IMPLIED_SEVEN_MAPPINGS = {
        1 : 10,
        2 : 11,
        6 : 12,
        7 : 5,
        8 : 13,
        14: 15
    }
    
    def _get_root(self):
        return self._root
    def _set_root(self, value):
        if value is not None:
            value = value % 12
        self._root = value
    
    def _get_root_numeral(self):
        if self.roman:
            return int_to_chord_numeral(self._root)
        else:
            return int_to_pitch_class(self._root)
    def _set_root_numeral(self, value):
        if self.roman:
            self._root = chord_numeral_to_int(value)
        else:
            self._root = pitch_class_to_int(value)
    
    def _get_type(self):
        return Chord.TYPE_SYMBOLS[self._type]
    def _set_type(self, value):
        if value is None:
            value = ""
        if value not in Chord.TYPE_SYMBOLS.values():
            raise ValueError, "%s is not a valid chord type: must be one of [%s]" \
                % (value, 
                    ",".join(Chord.TYPE_SYMBOLS.values()))
        else:
            self._type = [key for key,val in Chord.TYPE_SYMBOLS.items() if val==value][0]
            
            
    root = property(_get_root, _set_root)
    root_numeral = property(_get_root_numeral, _set_root_numeral)
    type = property(_get_type, _set_type)
    
    def __init__(self, root_numeral="C", type="", additions=None, roman=False):
        self.roman = roman
        self.root_numeral = root_numeral
        self.type = type
        if additions is None:
            additions = ""
        self.additions = additions
        
    def __hash__(self):
        if self.root is None:
            return 13
        return self.root
    
    def __ne__(self, other):
        return not (self == other)
    
    def __eq__(self, other):
        return self.equal_bar_additions(other) and \
               self.additions == other.additions
    
    def equal_bar_additions(self, other):
        return (type(self) == type(other)) and \
               (self.root == other.root) and \
               (self.type == other.type)
               
    def _get_tetrad_type(self):
        """
        Returns the implicit or explicit tetrad type of the chord. This 
        is the chord type, but mapped so that any 7 implicit in the 
        additions is explicit in the type.
        """
        if self.additions in Chord.SEVEN_IMPLIED_ADDITIONS and self._type in Chord.IMPLIED_SEVEN_MAPPINGS:
            # There is an implied seven.
            # The seven is not explicit in the chord type, so the 
            #  type should be mapped
            return Chord.TYPE_SYMBOLS[Chord.IMPLIED_SEVEN_MAPPINGS[self._type]]
        return self.type
    tetrad_type = property(_get_tetrad_type)
    
    def __str__(self):
        # Base name is the chord name, e.g. "C#"
        # Follow this by the chord type, e.g. "m" in "C#m"
        name = "%s%s" % (self.root_numeral, self.type)
        # If there are any additions, add them on the end
        if self.additions:
            name += "(%s)" % self.additions
        return name
        
    def __repr__(self):
        return str(self)
    
    def to_latex(self):
        return filter_latex(str(self))
        
    @staticmethod
    def interval(chord1, chord2):
        """ Returns the interval from chord1 to chord2. """
        return (chord2.root - chord1.root) % 12
        
    @staticmethod
    def from_name(chord_name, roman=False, permissive=False):
        """
        Given a string chord name, returns the Chord object corresponding
        to that name.
        
        C{permissive} allows the label to be interpreted as a roman numeral 
        or a pitch label.
        
        """
        # Use a clever regular expression to split up the chord name
        if permissive:
            # Try both regexes
            parse = ROMAN_REGEX.match(chord_name.strip())
            if parse is None:
                parse = PITCH_REGEX.match(chord_name.strip())
                roman = False
            else:
                roman = True
        elif roman:
            parse = ROMAN_REGEX.match(chord_name.strip())
        else:
            parse = PITCH_REGEX.match(chord_name.strip())
        
        if parse is None:
            raise ChordError, "invalid chord symbol (%s mode): %s" % \
                (permissive and "either" or (roman and "roman" or "pitch"), 
                 chord_name)
        result = parse.groupdict()
        root = result['root']
        chord_type_name = result['type']
        additions = result['additions']
        
        # Build the Chord object using these results
        return Chord(root_numeral=root, type=chord_type_name, 
                        additions=additions, roman=roman)
    
    def to_db_mirror(self):
        """
        Produce a db mirror Chord instance (see L{jazzparser.data.db_mirrors} 
        that represents the same chord as this.
        
        """
        mirror = MirrorChord(root=self.root,
                             type=self.type,
                             additions=self.additions)
        return mirror


class DerivationTrace(object):
    """
    Stores a trace of the derivation of a particular CCGCategory node
    and is associated with that category. For parse results, these structures 
    will often be so large that there's no hope of being able to print the 
    thing (even recursing to count the size can be prohibitively slow!).
    
    """
    def __init__(self, result, rule=None, args=[], word=None):
        """
        rule and args may be specified to give the derivation node an 
        initial pointer to a rule that was applied and a list of the 
        arguments for that rule.
        Add more rules using add_rule().
        
        All rule applications stored should have resulted in result.
        """
        # Store a list of the rule applications and their arguments
        self.rules = []
        self.result = result
        self.word = word
        if rule is not None:
            self.rules.append((rule,args))
            
    def add_rule(self, rule, args=[]):
        """
        Add a rule application to the derivation node (that resulted in the 
        same category as other rule applications stored here).
        The rule is a pointer to the rule object that was applied.
        The args is a list of the arguments to which the rule was applied.
        """
        self.rules.append((rule,args))
        
    def add_rules_from_trace(self, other_trace):
        self.rules.extend(other_trace.rules)
        
    def __str__(self):
        return self.str_indent("")
        
    def str_indent(self, indent="", signfmt=str):
        output = ""
        output += indent + signfmt(self.result) + "\n"
        if self.word is not None:
            output += "%s | \"%s\"\n" % (indent, self.word)
        else:
            for rule in self.rules:
                (ruleobj, arglist) = rule
                output += indent + " | from %s (%s) applied to\n" % \
                                    (ruleobj.readable_rule, ruleobj.name)
                for arg in arglist:
                    output += arg.str_indent(indent+" |  ", signfmt=signfmt)
        
        return output
    
    def get_size(self):
        if self.word is not None:
            return 1
        else:
            size = 0
            for rule in self.rules:
                size += 1
                for arg in rule[1]:
                    size += arg.get_size()
            return size
    

class Fraction(object):
    """
    Stores a rational fraction as a numerator and denominator.
    Fractions can be output as strings and also read in from strings
    (use Fraction(string=<string>), or just Fraction(<string>)). 
    
    The format used is "i", where i
    is an integer if the fraction is an exact integer, or "i n/d", where
    i is the integer part, n the numerator and d the denominator.
    
    """
    def __init__(self, numerator=0, denominator=1, string=None):
        self._denominator = 1
        
        self.numerator = numerator
        self.denominator = denominator
        if isinstance(numerator, str):
            string = numerator
        if string is not None:
            whole_string = string
            # Get rid of extra spaces
            string = string.strip()
            # Check for negation at the beginning: has to negate whole fraction
            # If we don't split this off now, it only negates the integer part
            if string.startswith("-"):
                neg = True
                string = string.lstrip("-").strip()
            else:
                neg = False
            # Split the integer part from the fractional part
            string_parts = string.split(" ")
            try:
                if len(string_parts) == 1:
                    # Try splitting into a/b
                    fract_parts = [p.strip() for p in string.split("/")]
                    if len(fract_parts) == 1:
                        # Just an integer
                        self.numerator = int(string)
                        self.denominator = 1
                    elif len(fract_parts) == 2:
                        # a/b
                        self.numerator = int(fract_parts[0])
                        self.denominator = int(fract_parts[1])
                    else:
                        raise Fraction.ValueError, "Too many slashes in "\
                            "fraction '%s'." % whole_string
                else:
                    integer = int(string_parts[0])
                    fract_parts = string_parts[1].split("/")
                    if len(fract_parts) == 2:
                        numerator = int(fract_parts[0])
                        denominator = int(fract_parts[1])
                    else:
                        raise Fraction.ValueError, "Too many slashes in "\
                            "fraction '%s'." % whole_string
                    self.numerator = numerator + integer * denominator
                    self.denominator = denominator
            except ValueError:
                raise Fraction.ValueError, "Error parsing fraction "\
                    "string '%s'." % string
            if neg:
                # There was a - at the beginning, so negate the whole thing
                self.numerator = -self.numerator
    
    def _get_denominator(self):
        return self._denominator
    def _set_denominator(self, val):
        if val == 0:
            raise ZeroDivisionError, "tried to set a Fraction's denominator "\
                "to zero"
        self._denominator = val
    denominator = property(_get_denominator, _set_denominator)
        
    def simplify(self):
        # Find the highest common factor of the num and denom
        hcf = euclid(self.numerator, self.denominator)
        if hcf != 0:
            self.numerator /= hcf
            self.denominator /= hcf
    
    def simplified(self):
        """
        Returns a simplified version of this fraction without modifying 
        the instance.
        
        """
        # Find the highest common factor of the num and denom
        hcf = euclid(self.numerator, self.denominator)
        if hcf == 0:
            numerator = self.numerator
            denominator = self.denominator
        else:
            numerator = self.numerator / hcf
            denominator = self.denominator / hcf
        return Fraction(numerator, denominator)
    
    def reciprocal(self):
        if self.numerator == 0:
            raise ZeroDivisionError, "tried to take reciprocal of 0"
        return Fraction(self.denominator, self.numerator)
    
    def __str__(self):
        if self.denominator == 1:
            return "%d" % self.numerator
        elif self.numerator/self.denominator == 0:
            return "%d/%d" % (self.numerator, self.denominator)
        else:
            return "%d %d/%d" % (self.numerator/self.denominator, \
                                 self.numerator % self.denominator, \
                                 self.denominator)
                                 
    __repr__ = __str__
    
    def to_latex(self):
        if self.denominator == 1:
            return "%d" % self.numerator
        else:
            return "%d \\frac{%d}{%d}" % (self.numerator/self.denominator, \
                                 self.numerator % self.denominator, \
                                 self.denominator)
    
    ####### Operator overloading #######
    
    def __add__(self, other):
        if type(other) == int or type(other) == long:
            result = Fraction(self.numerator + other*self.denominator, self.denominator)
        elif type(other) == Fraction:
            new_denom = self.denominator * other.denominator
            result = Fraction((self.numerator*other.denominator \
                               + other.numerator*self.denominator), new_denom)
        elif type(other) == float:
            return float(self) + other
        else:
            raise TypeError, "unsupported operand type for - with Fraction: %s" % type(other)
        result.simplify()
        return result
    
    # For backwards compatibility...
    plus = __add__
    
    def __radd__(self, other):
        # Addition works the same both ways
        return self + other
    
    def __neg__(self):
        return Fraction(-self.numerator, self.denominator)
        
    def __sub__(self, other):
        return self + (-other)
    
    def __rsub__(self, other):
        return (-self) + other
        
    def __mul__(self, other):
        if type(other) == int or type(other) == long:
            result = Fraction(self.numerator*other, self.denominator)
        elif type(other) == Fraction:
            result = Fraction(self.numerator*other.numerator, self.denominator*other.denominator)
        elif type(other) == float:
            return float(self) * other
        else:
            raise TypeError, "unsupported operand type for * with Fraction: %s" % type(other)
        result.simplify()
        return result
    
    def __rmul__(self, other):
        # Multiplication works the same both ways
        return self * other
        
    def __div__(self, other):
        if type(other) == int or type(other) == long:
            result = Fraction(self.numerator, self.denominator*other)
        elif type(other) == Fraction:
            result = Fraction(self.numerator*other.denominator, self.denominator*other.numerator)
        elif type(other) == float:
            return float(self) / other
        else:
            raise TypeError, "unsupported operand type for / with Fraction: %s" % type(other)
        result.simplify()
        return result
    
    def __rdiv__(self, other):
        return self.reciprocal() * other
        
    def __float__(self):
        return float(self.numerator) / self.denominator
        
    def __int__(self):
        return self.numerator / self.denominator
        
    def __long__(self):
        return long(self.numerator) / long(self.denominator)
        
    #####################################
    
    def __cmp__(self, other):
        if other is None:
            return 1
        
        if type(other) == int:
            other = Fraction(other)
            
        if type(other) == float:
            return cmp(float(self), other)
        
        if other.__class__ != self.__class__:
            raise TypeError, "Fraction.__cmp__(self,other) requires other to "\
                "be of type Fraction or int. Type was %s." % other.__class__
        # Cmp should not have any lasting effect on the objects
        selfnum = self.numerator
        othernum = other.numerator
        selfnum *= other.denominator
        othernum *= self.denominator
        if selfnum == othernum:
            return 0
        elif selfnum > othernum:
            return 1
        else:
            return -1
        
    def __hash__(self):
        return self.numerator + self.denominator
        
    class ValueError(Exception):
        pass

def euclid(num1, num2):
    while num2 != 0:
        remainder = num1 % num2
        num1 = num2
        num2 = remainder
    return num1


class HashSet(object):
    """
    A simple implementation of a hash table using a dictionary.
    The table is a set, since it does not store duplicate entries.
    
    Stores pointers both in a hash table (dictionary) and a list, 
    so that the values can be retreived quickly.
    
    By default, behaves as a set. Setting C{check_existing=False} will 
    cause it not to perform the check on whether the same value already 
    exists, so the table will end up storing duplicates.
    
    """    
    def __init__(self, check_existing=True):
        self.table = {}
        self.list = []
        
    def _add_existing_value(self, existing_value, new_value):
        """
        When a value already exists in the table, this is called 
        instead of adding the value. By default, it does nothing 
        (i.e. drops the new value), but you can override it if you 
        want to do something else to combine the values.
        
        Note that your custom methods must only modify the sign 
        that's already in the set (C{existing_value}), not add a 
        new sign and not modify C{new_value}.
        
        """
        pass
        
    def append(self, new_entry):
        """
        Appends the new entry to the set if it's not already there.
        Returns true if the entry is added, false otherwise.
        """
        # Look up its hash value
        key = hash(new_entry)
        if key not in self.table:
            # The hash doesn't already exist: add a new list
            self.table[key] = []
        elif new_entry in self.table[key]:
            # It's already there. Don't add it again.
            index = self.table[key].index(new_entry)
            existing_sign = self.table[key][index]
            self._add_existing_value(existing_sign, new_entry)
            return False
        # Add the entry to the correct list if it's not there
        self.table[key].append(new_entry)
        # Also store a pointer in the list
        self.list.append(new_entry)
        return True
        
    def extend(self, entries):
        """
        Appends each of the given entries to the set.
        Returns true if any of them is added, false otherwise.
        """
        added = False
        for entry in entries:
            app = self.append(entry)
            if app:
                added = True
        return added
    
    def __contains__(self, value):
        # Look up the hash value
        key = hash(value)
        # Check whether the value's in the table
        return value in self.table[key]
    
    def values(self):
        return self.list
    
    def remove(self, entry):
        key = hash(entry)
        if entry not in self.table[key]:
            raise ValueError, "Tried to remove an entry that's not in the hash set."
        # Remove from the hash table
        self.table[key].remove(entry)
        # Also remove from the list
        self.list.remove(entry)
        return
    
    def __len__(self):
        return len(self.values())
