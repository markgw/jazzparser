"""
Script for replacing annotations on the chords in the database.
Read notes below before using.

#######################################################################
First important note
====================

This tool is dangerous! Don't use it unless the database is 
*definitely* backed up.

#######################################################################
Important note on reannotation tool
===================================

I've not properly documented the reannotation tool. It was really only 
created for a one-off use. The thing is, it's pretty useful. The other 
thing is that I'm not going to use it much, since it is, by its nature,
not intended for repeated use.

If I develop it into a more reusable tool, I'll document it better, but 
at the moment, unless you understand what it's doing in an incredible 
amount of detail, you shouldn't use it anyway, since it is quite 
dangerous!
#######################################################################

Mark Wilding
24/3/2010

"""

import sys
from optparse import OptionParser

from apps.sequences.models import Chord
from count_category_use import count_categories

def _get_condition(cond):
    return lambda chord : chord.category == cond 

def reannotate(opts, args):
    # Process the commands to work out what to do
    if opts.file is None:
        # Take command line input
        if len(args) == 0:
            print "No input file or command line input was given. Nothing to do"
            return 1
        commands = " ".join(args)
    else:
        # Try to load the file
        try:
            file = open(opts.file, 'r')
            commands = file.read()
            file.close()
        except IOError, err:
            print "Could not read file %s: %s" % (opts.file, err)
            return 1
    # Split up the input into individual commands
    command_list = [line.strip("; ") for line in sum([cmd.split(";") for cmd in commands.splitlines()], [])]
    # Remove empty lines and comments
    command_list = [cmd for cmd in command_list if cmd != '' and not cmd.startswith('#')]
    
    # Interpret each command and prepare to apply it.
    # Each replacement is a tuple (chord, before_conditions,after_conditions,replacement)
    replacements = []
    for cmd in command_list:
        # Split up this replacement command
        parts = cmd.split(":")
        if len(parts) != 2:
            print "Invalid replacement: %s. Must be of the form '<condition> : <replacement>'" % cmd
            return 1
        condition = parts[0].strip()
        original_condition = condition
        replacement = parts[1].strip()
        # Split off all the before conditions
        before_conds = condition.split("<")
        condition = before_conds[-1]
        before_conds = before_conds[:-1]
        # Split off the after conditions
        after_conds = condition.split(">")
        condition = after_conds[0]
        after_conds = after_conds[1:]
        # Make a conditional test out of each part
        befores = list(reversed([_get_condition(c) for c in before_conds]))
        afters = [_get_condition(c) for c in after_conds]
        # Chord itself must be just a fixed string, no wildcards, etc
        chord = condition
        
        if replacement.startswith("$$"):
            def _get_callback(rpl, org_cnd):
                def _callback(crd, unique_in=None):
                    # Do this instead of making a replacement
                    crds = []
                    bcrd = crd
                    for i in range(rpl.count("<")):
                        # Go back the right number of characters
                        try:
                            bcrd = Chord.objects.get(next=bcrd)
                        except Chord.DoesNotExist:
                            break
                        crds.append(bcrd)
                    crds.reverse()
                    # Add the chord itself
                    crds.append(crd)
                    acrd = crd
                    for i in range(rpl.count(">")):
                        if acrd.next is None:
                            break
                        else:
                            acrd = acrd.next
                        crds.append(acrd)
                    sequence = tuple([c.category for c in crds])
                    if unique_in is not None:
                        # Check whether we've shown this sequence before
                        if sequence in unique_in:
                            # Seen before
                            return
                        unique_in.add(sequence)
                    print "Sequence %s matched %s (%s)" % (
                        " ".join(["%s(%s)" % (c,c.category) for c in crds]),
                        org_cnd,c.sequence.name.encode('ascii','replace'))
                return _callback
            repl = _get_callback(replacement, original_condition)
            repl_befores = []
            repl_afters = []
        else:
            # Split the replacement up if it specifies parts for surrounding chords
            repl_befores = replacement.split("<")
            replacement = repl_befores[-1]
            repl_befores = list(reversed(repl_befores[:-1]))
            # And the afterwards bit
            repl_afters = replacement.split(">")
            repl = repl_afters[0]
            repl_afters = repl_afters[1:]
        replacements.append((chord, befores, afters, repl, 
                                repl_befores, repl_afters, original_condition))
    
    # Check whether we're running in real mode and warn if we are
    if opts.real:
        print "This will edit the data in the database to make the replacement."
        print "Are you sure? [y/N] ",
        sys.stdout.flush()
        check = raw_input("")
        if check.lower() != 'y':
            print "Exiting"
            return 0
    else:
        print "Running in dry-run mode. Use -r to make actual replacements.\n"
    
    # Make each of the replacements in the database
    replaced = {}
    # Build an assignment up to make once we've worked out what 
    #  to assign to everything. This means everything is 
    #  searched in its original context and later rules take 
    #  priority
    assignment = {}
    for category,befores,afters,replacement,repl_befores,repl_afters,original_condition in replacements:
        if opts.unique:
            # Build a set of sequences we've shown so we only show each once
            shown_sequences = set()
        else:
            shown_sequences = None
        matches = []
        chords = Chord.objects.filter(category=category)
        for chord in chords:
            matched = True
            bchord = chord
            for cond in befores:
                try:
                    # Get the previous chord
                    bchord = Chord.objects.get(next=bchord)
                except Chord.DoesNotExist:
                    matched = False
                    break
                # Check that the condition holds for this chord
                if not cond(bchord):
                    matched = False
                    break
            # Continue if we found a failed condition
            if not matched: continue
            
            achord = chord
            for cond in afters:
                achord = chord.next
                if achord is None:
                    matched = False
                    break
                # Check the condition on this chord
                if not cond(achord):
                    matched = False
                    break
            # Continue if there was a failed condition
            if not matched: continue
            
            if callable(replacement):
                replacement(chord, unique_in=shown_sequences)
            else:            
                # Chord matches all conditions: make replacement
                def _replace(crd, new_val):
                    # Log the replacement
                    if crd.sequence not in replaced:
                        replaced[crd.sequence] = 1
                    else:
                        replaced[crd.sequence] += 1
                    if opts.real:
                        assignment[crd] = new_val
                    else:
                        print "%s: replace category %s on %s (%d) with %s" % (
                            crd.sequence.name.encode('ascii','ignore'), crd.category, crd, 
                            crd.id, new_val)
                # The chord itself
                _replace(chord, replacement)
                # Any chords before it
                bchord = chord
                for repl in repl_befores:
                    # Get the preceding chord
                    try:
                        bchord = Chord.objects.get(next=bchord)
                    except Chord.DoesNotExist:
                        # Don't try going back any further
                        break
                    _replace(bchord, repl)
                # And the chord after it
                achord = chord
                for repl in repl_afters:
                    # Get the next chord
                    achord = achord.next
                    if achord is None:
                        # Don't try going on any further
                        break
                    _replace(achord, repl)
    
    if opts.real:
        # Make the actual assignments
        for crd,val in assignment.items():
            crd.category = val
            crd.save()
        print "Replacements made:"
        for seq,num in replaced.items():
            print "%s: %d" % (seq.name.encode('ascii','replace'), num)
        # This doesn't work any more, but no real need for it anyway
        #if not opts.nocounts:
        #    # Output a table of the new category distribution
        #    count_categories()
    return 0
    
def main():
    parser = OptionParser(usage="%prog [options] [commands]")
    parser.add_option('-r', '--real', dest="real", action="store_true", \
        help="actually make the replacements. By default, just prints out what it would do")
    parser.add_option('-c', '--no-counts', dest="nocounts", action="store_true", \
        help="turn off category distribution count after replacements. On by default")
    parser.add_option('-f', '--file', dest="file", action="store", \
        help="specifies a file to take input from. Otherwise just "\
            "accepts input from the command line")
    parser.add_option('-u', '--unique', dest="unique", action="store_true", \
        help="just show the first unique category sequence that matches each "\
            "replacement, hiding subsequent duplicates")
    options, arguments = parser.parse_args()
    
    # Don't allow unique to be used in real mode
    if options.real and options.unique:
        print "We don't allow unique to be used in real mode: running in "\
            "dry-run mode instead."
        options.real = False
    sys.exit(reannotate(options, arguments))
    
if __name__ == "__main__":
    main()
