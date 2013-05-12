"""Framework for specifying multiple options to a module on the command line.

For modules like taggers and parsers, the options available will vary 
depending on what component is selected. This framework allows a 
specific component to list its available options and how they should 
be interpreted.

This is one of my greater works of genius to be found in this codebase.
It's incredibly useful so often.

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


class UnprocessedOptionValue(object):
    """
    Simple wrapper for strings to mark that they haven't yet been 
    processed as option values.
    """
    def __init__(self, val):
        self.value = val
        
    def __str__(self): return self.value

class ModuleOption(object):
    """
    An option that can be specified on the command line and that is 
    specific to a certain modular component (e.g. parser, tagger).
    
    Example use of a ModuleOption::
     ModuleOption('test',
                  lambda x: int(x), 
                  help_text="A test option", 
                  default=2,
                  usage="test=X, where X is an int")
    
    This will accept integer values for the option called "test". If no 
    value is given, it will default to 2.
    
    A filter function may be given which will be applied to the value during 
    option processing. If the filter raises an exception, the value will be 
    reported as invalid.
    
    You may also specify multiple filters as a tuple of functions. Each will 
    be applied in order and the first value successfully returned will be 
    used.
    
    """
    def __init__(self, name, filter=None, 
                    help_text="No help text available", default=None,
                    usage=None, required=False):
        self.name = name
        if filter is not None:
            self.filter = filter
        else:
            self.filter = None
        self.help_text = help_text
        self.default = default
        self._usage = usage
        self.required = required
        
    def _get_usage(self):
        if self._usage is not None:
            return self._usage
        else:
            return "%s=X" % self.name
    usage = property(_get_usage)
            
    def get_value(self, options):
        """
        Pulls the appropriate value out of a dictionary of options and 
        return it.
        """
        if self.name not in options:
            if self.required:
                raise ModuleOptionError, "option '%s' is required, but was not specified" % self.name
            # Not in the options: return the default value
            return self.default
        if type(options[self.name]) == UnprocessedOptionValue:
            # The values have come from a string and not been processed
            if self.filter is None:
                # No processing to do
                return options[self.name].value
            elif type(self.filter) == tuple:
                # Got a tuple of filters: try each in turn
                errs = []
                for filt in self.filter:
                    try:
                        return filt(options[self.name].value)
                    except Exception, err:
                        errs.append(err)
                # All filters failed
                raise ModuleOptionError, "invalid value for option '%s': "\
                    "%s" % (self.name, "; ".join([str(err) for err in errs]))
            else:
                try:
                    return self.filter(options[self.name].value)
                except Exception, err:
                    raise ModuleOptionError, "invalid value for option "\
                        "'%s': %s" % (self.name, err)
        else:
            # No preprocessing to do, just return it as it is
            return options[self.name]
            
    @staticmethod
    def process_option_string(optstr):
        """
        Takes an option string in the format in which options should 
        be specified on the command line and returns a dictionary 
        ready to pass to the options themselves.
        
        Module options must be in the format opt1=val1:opt2=val2:etc. 
        Later options override earlier ones.
        
        C{optstr} may also be a list of strings. In this case, the 
        options in each string will be concatenated. This allows you 
        to take options from multiple CL options using optparse's 
        C{append} action.
        
        If the optstr is None, or an empty list, returns an empty dict. 
        This allows you to pass in a value directly from an optparse 
        parser.
        
        """
        if type(optstr) == list:
            optstr = ":".join(optstr)
        options = {}
        if optstr is not None and len(optstr.strip()):
            for optval in optstr.split(":"):
                opt, __, val = optval.partition("=")
                if len(val) == 0:
                    raise ModuleOptionError, "Module options must be in the "\
                        "format opt1=val1:opt2=val2:etc. Got: %s" % optval
                # We don't know how to process this string yet, so we 
                #  mark it unprocessed and leave it to the option.
                options[opt] = UnprocessedOptionValue(val)
        return options
    
    @staticmethod
    def process_option_dict(optdict, available_opts):
        """
        Takes a dictionary of options, which may be from command-line 
        strings (via process_option_string) or internal, and a list 
        of allowed options and returns a dictionary of all the option 
        values.
        """
        used_opts = []
        options = {}
        for option in available_opts:
            # Try getting a value from the dict for this option
            options[option.name] = option.get_value(optdict)
            used_opts.append(option.name)
        # Check whether there were any more options we didn't use
        for key in optdict.keys():
            if key not in used_opts:
                raise ModuleOptionError, "'%s' is not a valid option." \
                    % key
        return options

def options_help_text(options, intro=None):
    """
    Produces a load of help text to output to the command line to 
    display the usage of all of the options in the list.
    """
    if len(options) == 0:
        return "This module has no options"
    from jazzparser.utils.tableprint import pprint_table
    from StringIO import StringIO
    rows = []
    # Put required options first
    for opt in [o for o in options if o.required]:
        rows.append([opt.name, "%s (REQUIRED)" % opt.usage, opt.help_text])
    for opt in [o for o in options if not o.required]:
        rows.append([opt.name, opt.usage, opt.help_text])
    output = StringIO()
    # Print the options in a nice table
    pprint_table(output, rows, separator="", 
                 justs=[True,True,True], 
                 widths=[None,35,40],
                 blank_row=True)
    strout = output.getvalue()
    output.close()
    if intro is not None:
        strout = "%s\n%s\n%s" % (intro, "="*len(intro), strout)
    return strout

class ModuleOptionError(Exception):
    pass

########### Filters
# These are functions that can be used as filters for option types.
def file_option(value):
    """
    A filter function for filenames of existing files.
    Errors if the file doesn't exist.
    
    """
    if value is None:
        return None
    import os
    filename = os.path.abspath(value)
    if not os.path.exists(filename):
        raise ModuleOptionError, "the file %s does not exist" % filename
    else:
        return filename
        
def new_file_option(value):
    """
    A filter function for a new filename.
    Doesn't require the file to exist, but errors if the directory 
    doesn't exist.
    
    """
    if value is None:
        return None
    import os
    filename = os.path.abspath(value)
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        raise ModuleOptionError, "the directory %s does not exist" % dirname
    else:
        return filename

def zero_to_one_float(value):
    """
    A filter function for floats that should lie between 0.0 and 1.0.
    
    Accepts the range ends (0.0 and 1.0). Raises an errror for any incorrectly 
    formatted numbers or numbers outside this range.
    
    This is useful for probabilities or ratios.
    
    """
    if value is None:
        return None
    try:
        value = float(value)
    except ValueError:
        raise ModuleOptionError, "not a float: %s" % value
    if value < 0.0 or value > 1.0:
        raise ModuleOptionError, "float not in range 0.0 - 1.0: %s" % value
    return value

def choose_from_dict(dic):
    """
    Filter function constructor. Returns a filter function that will verify 
    that the filtered value is among the C{dic}'s keys and return the 
    corresponding value if it is.
    
    """
    def _filter(value):
        if value not in dic:
            raise ModuleOptionError, "invalid option value: %s. Possible values "\
                "are: %s" % (value, ", ".join(dic.keys()))
        return dic[value]
    return _filter
    
def choose_from_list(lst):
    """
    Filter function constructor.
    
    Returns a filter function that will verify that the value is one of those 
    in the list and then just return that value if it is.
    
    """
    def _filter(value):
        if value not in lst:
            raise ModuleOptionError, "invalid option value: %s. Possible values "\
                "are: %s" % (value, ", ".join(lst))
        return value
    return _filter
