"""Chart representation for CKY chart parsing.

Classes and utility methods for CKY chart parsing for the Jazz Parser.
This provides most of the main functionality of the CKY parser, 
apart from the main parse loop and the tagger interface.

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


from jazzparser.data import DerivationTrace, Fraction, HashSet
import logging

# Get the logger from the logging system
logger = logging.getLogger("main_logger")


class SignHashSet(HashSet):
    """
    Based on the basic hash set implementation. Provides special 
    behaviour for adding already existing signs, so that, e.g., the 
    derivation traces get added when a new sign is an alternative 
    derivation of an already existing one.
    
    SignHashSet additionally stores and maintains an index of the signs 
    by category. It is useful during parsing to get just the distinct 
    categories, since all the signs with the same category will be 
    subject to the same rule applications.
    
    """
    def __init__(self, formalism, derivation_traces=False, *args, **kwargs):
        super(SignHashSet, self).__init__(*args, **kwargs)
        self.formalism = formalism
        self._signs_by_category = {}
        self.derivation_traces = derivation_traces
        
    def append(self, new_entry):
        """
        Overrides append() to maintain the index of signs grouped 
        by category.
        
        See L{jazzparser.data.HashSet} for main doc.
        
        """
        added = super(SignHashSet, self).append(new_entry)
        if added:
            # The new entry was added to the set: index it by category
            if new_entry.category in self._signs_by_category:
                self._signs_by_category[new_entry.category].append(new_entry)
            else:
                self._signs_by_category[new_entry.category] = [new_entry]
        return added
        
    def remove(self, entry):
        """
        Overrides remove() to maintain the index of signs grouped 
        by category.
        
        See L{jazzparser.data.HashSet} for main doc.
        
        """
        super(SignHashSet, self).remove(entry)
        # Also remove it from the category index if it's there
        if entry.category in self._signs_by_category and \
                entry in self._signs_by_category[entry.category]:
            self._signs_by_category[entry.category].remove(entry)
            # Remove the key as well if the list is now empty
            if len(self._signs_by_category[entry.category]) == 0:
                del self._signs_by_category[entry.category]
    
    def _add_existing_value(self, existing_value, new_value):
        # Add the new derivation trace if necessary
        if self.derivation_traces:
            existing_value.\
                derivation_trace.add_rules_from_trace(new_value.derivation_trace)
        # Hand this over to the formalism-specific routine for merging 
        #  equal signs
        self.formalism.Syntax.merge_equal_signs(existing_value, new_value)
        
    def get_distinct_categories(self):
        """
        @return: a list containing one of each of the distinct syntactic 
        categories found among the signs in this set.
        
        """
        return self._signs_by_category.keys()
        
    def get_signs_grouped_by_category(self):
        """
        @rtype: list of lists of L{Sign<jazzparser.formalisms.base.SignBase>}s
        @return: all the signs in the set, grouped into lists of 
            signs sharing the same syntactic category.
            
        """
        return self._signs_by_category.values()
        
    def get_signs_by_category(self, category):
        """
        @rtype: list of L{Sign<jazzparser.formalisms.base.SignBase>}s
        @return: all the signs in the set that have a category equal 
            to that given.
            
        """
        if category in self._signs_by_category:
            return self._signs_by_category[category]
        else:
            return []

class Chart(object):
    """
    Represents a chart for use in CKY chart parsing.
    A Chart stores a table of signs between node pairs.
    It keeps a list of all the rules that can be applied.
    
    There are no edges (i,i) and all edges are directed forward
    (i.e. (i,j) where j>i). Internally, the table only 
    stores edges from each i to each j>i.
    
    In the interface, however, edges are always referred to 
    by the nodes they go from and to.
    
    Functions are contained in Chart for applying unary and binary rules.
    
    You may instantiate a chart with no signs. You must still provide a 
    signs list, which will define the size of the chart, so you should 
    fill it with empty lists.
    
    By default, chart.parses will only return atomic results, since 
    only these represent full parses. If you want all signs that span 
    the whole input, use chart.get_signs(0, end). If you decide that 
    complex results represent real parses, instantiate the chart with 
    allow_complex=True.
    
    """
    HASH_SET_IMPL = SignHashSet
    
    def __init__(self, grammar, signs, derivations=False, hash_set_kwargs={}, allow_complex=False):
        self.derivations = derivations
        self.grammar = grammar
        self.allow_complex = allow_complex
        # For efficiency
        self._all_brules_applied = {}
        
        self.inspector = None
        
        # Prepare the chart
        self._table = []
        for x in range(len(signs)):
            # Row for each node
            self._table.append([])
            for y in range(x,len(signs)):
                # Cell (column) for each node
                # Cells are currently empty hash tables: will later put categories in here
                self._table[x].append(
                        self.HASH_SET_IMPL(grammar.formalism, 
                                           derivation_traces=derivations,
                                           **hash_set_kwargs))
        for i,sign_list in enumerate(signs):
            if len(sign_list):
                self.add_word_signs(sign_list,i)
            
    def __len__(self):
        return len(self._table)
        
    size = property(__len__)
    
    def _get_parses(self):
        results = self._table[0][self.size-1].values()
        if not self.allow_complex:
            # Only return atomic categories: complex categories do not 
            #  represent a full parse
            def _is_atomic(sign):
                return self.grammar.formalism.Syntax.is_atomic_category(sign.category)
            results = filter(_is_atomic, results)
        return results
    parses = property(_get_parses)
    
    def get_signs(self, start, end):
        """
        Gets a list of the signs in the chart between nodes start
        and end.
        """
        if end <= start:
            logger.warning("Tried to get signs from %d to %d" % (start,end))
            return None
        return self._table[start][end-start-1].values()
        
    def get_grouped_signs(self, start, end):
        """
        Like L{get_signs}, but return a list of lists of signs, such 
        that every sign in a sublist has the same syntactic category.
        
        """
        if end <= start:
            logger.warning("Tried to get signs from %d to %d" % (start,end))
            return None
        return self._table[start][end-start-1].get_signs_grouped_by_category()
        
    def get_sign(self, start, end, index):
        """
        Returns the sign between start and end with the given index.
        """
        signs = self.get_signs(start, end)
        if signs is None or index >= len(signs):
            return None
        else:
            return signs[index]
    
    def get_sign_pairs(self, start, middle, end):
        """
        Gets a list of pairs (first,second) such that 
        first starts at start and ends at middle and second 
        starts at middle and ends at end.
        """
        pairs = []
        firsts = self.get_signs(start, middle)
        seconds = self.get_signs(middle, end)
        for first in firsts:
            for second in seconds:
                pairs.append((first,second))
        return pairs
        
    def get_grouped_sign_pairs(self, start, middle, end):
        """
        Like L{get_sign_pairs}, but instead of returning pairs of signs, 
        returns pairs of sign groups, where all the signs in the group 
        have the same syntactic category.
        
        """
        firsts = self.get_grouped_signs(start, middle)
        seconds = self.get_grouped_signs(middle, end)
        return [(first,second) for first in firsts for second in seconds]
    
    def add_word_signs(self, signs, start_node, word, end_node=None):
        """
        Adds a single-word categories in list "signs" to the chart for the word
        starting at node C{start_node}. This may span more than one node, in 
        which case C{end_node} should be given as well. By default, C{end_node} 
        will be assumed to be C{start_node}+1.
        
        """
        # Span is stored in the table internally as 
        #  (start_node, end_node-start_node-1)
        if end_node is None:
            span_end = 0
        else:
            span_end = end_node-start_node-1
            assert span_end >= 0
        
        if self.derivations:
            for sign in signs:
                sign.derivation_trace = DerivationTrace(sign, word=word)
        return self._table[start_node][span_end].extend(signs)
    
    def apply_unary_rules(self, start, end, *args, **kwargs):
        """
        Adds to the chart all signs resulting from possible  
        applications of unary rules to existing signs between
        nodes start and end.
        
        Additional args/kwargs get passed on to L{apply_unary_rule}.
        
        @return: True if signs were added as a result of rule application,
         False otherwise
        """
        signs_added = False
        
        unary_rules = self.grammar.unary_rules
        # Try applying each rule in turn
        for rule in unary_rules:
            added = self.apply_unary_rule(rule, start, end, *args, **kwargs)
            if added:
                signs_added = True
        return signs_added
        
    def apply_unary_rule(self, rule, start, end, result_modifier=None):
        """
        Applies a given unary rule to particular arcs and adds the 
        results to the chart.
        
        @type result_modifier: 2-arg function
        @param result_modifier: function to be applied to each result, 
            taking the result sign as the first argument and the input 
            sign as the second.
        
        """
        signs_added = False
        input_signs = self.get_signs(start, end)
        # Apply to each existing sign
        for sign in input_signs:
            # Don't try applying unary rules more than once (they'll have the same results)
            if not sign.check_rule_applied(rule):
                # Get the possible results of applying the rule
                results = rule.apply_rule([sign])
                # Check the rule was able to apply
                if results is not None:
                    # If storing derivation traces, add them now
                    if self.derivations:
                        for result in results:
                            result.derivation_trace = DerivationTrace(result, rule, [sign.derivation_trace])
                    # Apply a result modifier if one was given
                    if result_modifier is not None:
                        result_modifier(result, sign)
                    # Store the results in the table
                    added = self._table[start][end-start-1].extend(results)
                    # If that added anything, return True at the end
                    if added:
                        signs_added = True
                # Note that the rule has now been applied
                sign.note_rule_applied(rule)
        return signs_added
        
    def _apply_binary_rule(self, rule, sign_pair):
        """
        Internal method to apply a given binary rule to a given pair 
        of signs. Note that the supported interface method is 
        apply_binary_rule(), which applies a single rule to all sign 
        pairs between given nodes.
        
        This is used internally by L{apply_binary_rule} and 
        L{apply_binary_rules}.
        
        """
        if sign_pair[0].check_rule_applied(rule, sign_pair[1]):
            # This sign pair has been combined by this binary rule with this input before.
            # No need to do it again. If the application is possible, the 
            #  result will be in the chart
            return []
        # Get the possible results of applying the rule
        results = rule.apply_rule(sign_pair)
        # Note for future attempts that we've already done this
        sign_pair[0].note_rule_applied(rule, sign_pair[1])
        if results is not None:
            # If storing derivation traces, add them now
            if self.derivations:
                for result in results:
                    result.derivation_trace = DerivationTrace(result, rule, [sign.derivation_trace for sign in sign_pair])
            return results
        else:
            return []
    
    def _apply_binary_rule_semantics(self, rule, sign_pair, category):
        """
        Like _apply_binary_rule, but uses the C{apply_rule_semantics()}
        of the rule instead of C{apply_rule()} and returns a list of signs 
        built by copying the category and combining it in a sign with the 
        semantics of the result.
        
        """
        # Get the possible results of applying the rule
        results = rule.apply_rule_semantics(sign_pair)
        if results is not None:
            # Build signs from these and the category given
            signs = [self.grammar.formalism.Syntax.Sign(
                                                category.copy(), result)
                                                    for result in results]
            # If storing derivation traces, add them now
            if self.derivations:
                for sign in signs:
                    sign.derivation_trace = DerivationTrace(sign, rule, [s.derivation_trace for s in sign_pair])
            return signs
        else:
            return []
    
    def apply_binary_rules(self, start, middle, end):
        """
        Add to the chart all signs resulting from possible
        applications of binary rules to pairs of signs between
        node pairs (start,middle) and (middle,end),
        producing entries in (start,end).
        
        @return: True if signs were added as a result of rule application,
         False otherwise
        """
        signs_added = False
        
        all_pair_results = []
        binary_rules = self.grammar.binary_rules
        input_pairs = self.get_grouped_sign_pairs(start, middle, end)
        # Apply to each pair of existing signs
        for first_set,second_set in input_pairs:
            # Apply each binary rule
            for rule in binary_rules:
                # Try applying the rule to the first sign in each of 
                #  the groups. If this doesn't work, we can skip all the 
                #  rest of the signs in the groups, since they all have 
                #  the same syntactic category.
                results = rule.apply_rule((first_set[0], second_set[0]))
                if results is not None:
                    if len(results) == 1:
                        # There's only one syntactic result (this is the most 
                        #  common thing to happen).
                        # We only need to do the semantic part of all the other 
                        #  rule applications, because the category will be the 
                        #  same as this.
                        result_cat = results[0].category
                        for first_sign in first_set:
                            for second_sign in second_set:
                                # Apply the rule
                                pair_results = self._apply_binary_rule_semantics(
                                                        rule, 
                                                        (first_sign,second_sign),
                                                        result_cat)
                                all_pair_results.extend(pair_results)
                    else:
                        # Rule application succeeded, so we need to do it for 
                        #  all the signs in the groups to get all the 
                        #  different semantics.
                        for first_sign in first_set:
                            for second_sign in second_set:
                                # Apply the rule
                                pair_results = self._apply_binary_rule(rule, (first_sign,second_sign))
                                all_pair_results.extend(pair_results)
        if len(all_pair_results) > 0:
            # Add the resulting signs to the chart
            added = self._table[start][end-start-1].extend(all_pair_results)
            if added:
                signs_added = True
        return signs_added
    
    def apply_binary_rule(self, rule, start, middle, end):
        """
        Apply a given binary rule to particular arcs in the chart.
        
        Note that this method is not used by apply_binary_rules for 
        efficiency reasons, but apply_binary_rules simply does the same 
        thing for all possible binary rules.
        
        """
        all_pair_results = []
        input_pairs = self.get_grouped_sign_pairs(start, middle, end)
        signs_added = False
        for first_set,second_set in input_pairs:
            # Try applying the rule to the first of each set. If this 
            #  fails, it will also fail for the rest.
            results = rule.apply_rule((first_set[0], second_set[0]))
            if results is not None:
                # Apply the rule to all the pairs in the cross product
                for first_sign in first_set:
                    for second_sign in second_set:
                        pair_results = self._apply_binary_rule(rule, (first_sign,second_sign))
                        all_pair_results.extend(pair_results)
        if len(all_pair_results) > 0:
            # Store the results in the table
            added = self._table[start][end-start-1].extend(all_pair_results)
            if added:
                signs_added = True
        return signs_added
    
    def __str__(self):
        return self.to_string()
            
    def to_string(self, rows=None, cols=None):
        output = ""
        table_size = len(self)
        # Allow individual rows to be selected by the list rows
        if rows is None:
            rows = range(table_size)
        # Allow individual cols to be selected by the list cols
        if cols is None:
            cols = range(1,table_size+1)
        # Go through each row
        for x in rows:
            # Print a grid for each
            output += "\nEdges starting at %d\n" % x
            
            for y in cols:
                # Check the row has a cell in column y
                if y > x and y <= table_size:
                    col = y - x - 1
                    output += " (%d,%d): %s\n" % \
                        (x,y,", ".join(["<%d> %s" % (i,self._sign_string(sign)) for i,sign in enumerate(self._table[x][col].values())]))
        return output
        
    def _sign_string(self, sign):
        return "%s" % sign
    
    def _get_summary(self):
        """
        Returns a multi-line string that presents a brief summary of the chart
        as it currently stands. This does not show all of the signs in the 
        chart, but just a summary of how many signs there are in each cell.
        """
        summary = "\nF\\T"
        for col in range(1,len(self)+1):
            summary += "\t%d" % col
        summary += "\n\n"
        for row in range(len(self)):
            summary += "%d\t" % row + \
                       "-\t"*row + \
                       "\t".join(["%s" % len(cell) for cell in self._table[row]]) + \
                       "\n"
        return summary
    summary = property(_get_summary)
    
    def launch_inspector(self, input=None, block=False):
        """
        Starts up a graphical  chart inspector to inspect this chart.
        The inspector will run in a separate thread.
        Subclasses of Chart should override this if they have their own 
        version of the chart inspector and instantiate that instead.
        
        @type input: list of strings
        @param input: a string representation of the input to pass to 
            the inspector so it can display it.
        
        """
        # Get rid of any existing inspector for this chart
        self.kill_inspector()
        from .inspector import ChartInspectorThread
        inspector = ChartInspectorThread(self, input_strs=input)
        self.inspector = inspector
        if block:
            inspector.run()
        else:
            inspector.start()
        
    def kill_inspector(self):
        """
        Kills a currently-running inspector for this chart if one exists.
        
        """
        if self.inspector is not None:
            self.inspector.window.hide()
            self.inspector.window.destroy()
            self.inspector = None


def list_union(main_list, new_entries, derivations=False):
    """
    Adds all the entries in the list new_entries to the list 
    main_list, checking first that each entry does not already
    exist in main_list and only adding it if it doesn't.
    
    @return: True if members were added to the main list, False if main_list is
      unchanged.
    """
    added = False
    for new_entry in new_entries:
        if not new_entry in main_list:
            main_list.append(new_entry)
            added = True
        elif derivations:
            main_list[main_list.index(new_entry)].\
                derivation_trace.add_rules_from_trace(new_entry.derivation_trace)
                
    return added
    
class ChartError(Exception):
    """
    Raised if something goes wrong while building or processing a chart.
    """
    pass

def dump_chart(chart, filename):
    """
    Dump a pickled representation of the chart to a file.
    
    """
    import cPickle as pickle
    data = pickle.dumps(chart)
    file = open(filename, 'w')
    file.write(data)
    file.close()

def load_chart(filename):
    """
    Read in a chart file that was dumped using L{dump_chart}.
    
    @rtype: L{Chart}
    @return: the chart instance
    
    """
    import cPickle as pickle
    cfile = open(filename, 'r')
    data = cfile.read()
    cfile.close()
    return pickle.loads(data)
