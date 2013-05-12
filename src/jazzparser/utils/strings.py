"""String processing utilities.

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

def strs(list, sep=", "):
    """
    I'm fed up of typing this every time I want to print a list!
    
    This is nothing more than::
      return sep.join(["%s" % item for item in list])
    
    """
    return sep.join(["%s" % item for item in list])

def fmt_prob(prob, prec=4):
    """
    Format a float as a string in a style suitable for displaying 
    probabilities.
    This is not a particularly quick procedure. If you need to format 
    lots of probabilities, it's probably best to do something cruder.
    
    """
    from decimal import Decimal
    # Quantize the value to the correct precision
    prob = Decimal(str(prob))#.as_tuple()
    quant = Decimal((0, [1,], prob.adjusted()-prec+1))
    prob = prob.quantize(quant)
    # Format it yourself, because Decimal's to_sci_string is crap
    tup = prob.as_tuple()
    sci_str = "%s%d.%se%d" % ("-" if prob.is_signed() else "", tup.digits[0], "".join(["%d" % dig for dig in tup.digits[1:]]), prob.adjusted())
    # Add more spacing for higher precisions
    #fmt_str = " >%ds" % (prec+3)
    return sci_str #format(sci_str, fmt_str)

def group_numerical_suffixes(inlist, open_brace="{", close_brace="}"):
    """
    Handy utility for concise readable output of a list of name that 
    includes many that differ only by a numerical suffix.
    For example, ['model0','model1','model2'] is better represented 
    as 'model{0-2}'.
    
    Given a list of items, return a potentially smaller list, with all 
    names differing only by a numerical suffix condensed into a single 
    item, using {} to denote the suffix and using ranges where possible,
    otherwise comma-separated lists.
    
    """
    import re
    name_nums = {}
    outlist = []
    # Look for everything that ends in pure numbers
    num_end = re.compile('^(?P<name>.*?)(?P<number>\d+)$')
    
    for full_name in inlist:
        found = num_end.match(full_name)
        if found is not None:
            vals = found.groupdict()
            # This name ends in a number
            name_nums.setdefault(vals['name'], []).append(int(vals['number']))
        else:
            # Can't group this in any way
            outlist.append(full_name)
    
    for name,nums in name_nums.items():
        if len(nums) == 1:
            # Nothing to group with - don't group
            outlist.append("%s%s" % (name, nums[0]))
        else:
            # Perform the grouping
            nums.sort()
            ranges = []
            range_start = range_end = nums[0]
            
            for num in nums[1:]+[None]:
                # This None makes the loop continue once more after the 
                #  last item to add the last range
                if num is not None and num == range_end+1:
                    # Increment in the current range
                    range_end = num
                else:
                    # End of range
                    if range_start == range_end:
                        # Lonely number: no range
                        ranges.append("%s" % range_start)
                    else:
                        # Generate a range
                        ranges.append("%s-%s" % (range_start, range_end))
                    range_start = range_end = num
            # Grouped the name into ranges
            outlist.append("%s%s%s%s" % (name, open_brace, ",".join(ranges), close_brace))
    return outlist

def make_unique(strings, separator=""):
    """
    Ensures that there are no duplicate strings in a list of strings. Wherever 
    a duplicate is found, it is distinguished by appending an integer.
    
    """
    seen = {}
    unique = []
    for string in strings:
        if string in seen:
            unique.append("%s%s%d" % (string, separator, seen[string]))
            seen[string] += 1
        else:
            unique.append(string)
            seen[string] = 0
    return unique
    
def strip_accents(string):
    """
    Given a unicode string, which may contain accented characters, 
    returns a string with no accented characters.
    
    """
    import unicodedata
    return ''.join((c for c in unicodedata.normalize('NFD', unicode(string)) \
                        if unicodedata.category(c) != 'Mn'))


TRUE_STRINGS = ["true", "t", "1", "yes", "on", "hellyeah"]
def str_to_bool(string):
    """
    Interprets the string as a boolean. Normal Python behaviour for converting 
    a str to a bool is to return False for the empty string and True for 
    everything else. This function interprets a load of sensible true values 
    as True and everything else as False.
    
    Strings considered true (case insensitive): %s.
    
    """ % ", ".join(TRUE_STRINGS)
    return string.strip().lower() in TRUE_STRINGS

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    
    Lifted straight from Django's slugify function.
    
    """
    import re
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    value = re.sub('[\s]+', '_', value)
    return value
