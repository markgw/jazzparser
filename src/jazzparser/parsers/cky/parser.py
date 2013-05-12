"""CKY parser implementation.

This is the basic parser component of the jazz chord interpretation system.
This does all of the basic CKY parsing routine, but is unaware of the 
formalism, rule set, etc.

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

from jazzparser.grammar import Grammar
from chart import Chart
from jazzparser.utils.base import filter_latex, ExecutionTimer
from jazzparser.utils.options import ModuleOption, new_file_option
from jazzparser.utils.strings import str_to_bool
from jazzparser.parsers.base.parser import Parser
from .tools import ChartTool, InteractiveChartTool

import sys, re

from jazzparser import settings

class CkyParser(Parser):
    """
    CkyParser is the central class for the jazz chord sequence 
    recogniser parsing mechanism. 
    It constitutes the "algorithm" module of the system.
    It begins with a set of signs assigned to the input by the 
    tagger and parses to produce a chart, from which the resultant 
    signs can be extracted.
    
    """
    shell_tools = [ 
            ChartTool(), 
            InteractiveChartTool(),
    ]
    PARSER_OPTIONS = Parser.PARSER_OPTIONS + [
        ModuleOption('max_iter', filter=int,
            help_text="Maximum number of parser iterations to perform "\
                "before giving up. If 0 or unspecified, continues "\
                "until parse is complete.",
            usage="max_iter=X, where X is an integer.",
            default=0,
        ),
        ModuleOption('min_iter', filter=int,
            help_text="Usually, the parser will stop as soon as it finds a "\
                "full parse. Use min_iter to make it continue parsing until "\
                "it has done min_iter iterations or the tagger has ceased to "\
                "return any categories. Use -1 to keep going until the tagger "\
                "gives no more categories.",
            usage="min_iter=X, where X is an integer.",
            default=0,
        ),
        ModuleOption('parses', filter=int,
            help_text="Number of parses to require before we terminate. "\
                "Default is 1: the parser will terminate as soon as it finds "\
                "at least one full parse (unless another option, like "\
                "min_iter, prevents it",
            usage="parses=X, where X is an integer",
            default=1,
        ),
        ModuleOption('timeout', filter=int,
            help_text="Maximum time allowed for the main parse loop, in "\
                "minutes. If this is exceded, the backoff will kick "\
                "in, if one is specified. Otherwise, no results will be "\
                "returned. The parser will not stop as soon as the timeout "\
                "expires, but after finishing processing the current input "\
                "word. 0 (default) imposes no timeout.",
            usage="timeout=X, where X is an integer number of seconds.",
            default=0,
        ),
        ModuleOption('inspect', filter=str_to_bool,
            help_text="If true, the graphical chart inspector will be "\
                "displayed during parsing.",
            usage="inspect=X, where X is a boolean value.",
            default=False
        ),
        ModuleOption('inspect_persist', filter=str_to_bool,
            help_text="Makes the chart inspector window persist after parsing "\
                "is completed. By default, it will be killed",
            usage="inspect_persist=X, where X is a boolean value.",
            default=False
        ),
        ModuleOption('dump_chart', filter=new_file_option,
            help_text="A file to dump the chart state to during parsing. "\
                "The first dump will be when the chart is created and "\
                "new dumps will be made throughout the parse.",
            usage="dump_chart=X, where X is a filename."
        ),
        ModuleOption('derivations', filter=str_to_bool,
            help_text="Store derivation traces along with the results",
            usage="derivations=X, where X is a boolean value",
            default=None,
        ),
    ]
    
    def _create_chart(self, *args, **kwargs):
        self.chart = Chart(self.grammar, *args, **kwargs)
        return self.chart
        
    def _add_signs(self, offset=0, prob_adder=None):
        """
        Adds new signs to the chart from the supertagger, using the given 
        offset when requesting them from the tagger.
        
        @rtype: list of tuples
        @return: all the signs that were actually added. Each is represented 
            by a tuple (start_node, end_node, sign)
        
        """
        signs = self.tagger.get_signs(offset)
        words = self.tagger.get_string_input()
        if signs is None or len(signs) == 0:
            return []
        # Add each new sign to the chart
        added = []
        for (start,end,signtup) in signs:
            word_list = words[start:end]
            word = " ".join(w for w in word_list)
            # Add the probabilities as an attribute to the signs
            cat,tag,prob = signtup
            if prob_adder is not None:
                prob_adder(start, end, signtup, word_list)
            # Add the signs to the chart
            newadd = self.chart.add_word_signs([signtup[0]], start, word, end_node=end)
            # Keep a record of those that got added
            if newadd:
                added.append((start,end,signtup))
        return added
        
    def parse(self, derivations=False, summaries=False, inspect=False):
        """
        Run the parser on the input, using the specified tagger. Runs 
        the CKY parsing algorithm to do chart parsing. For details of 
        chart parsing, see Chart class.
        
        If the parser was given a maximum number of iterations, the 
        routine will return as usual after this number is completed, 
        even if no parses have been found.
        
        @type derivations: bool
        @param derivations: store derivation traces, which 
            can subsequently be used to trace all the derivations that 
            led to any given sign in the chart. Overridden by the module 
            option if it's given
        @type summaries: int/bool
        @param summaries: output chart summary information to stderr during 
            parsing to track progress. Set to 2 to output some info, 
            but not the full chart.
        @type inspect: bool
        @param inspect: launch a graphical chart inspector during the 
            parse to display interactive chart information.
            
        @return: a list of signs that span the full input.
        """
        if 'derivations' in self.options and self.options['derivations'] is not None:
            derivations = self.options['derivations']
            
        # Time excecution if we're showing any summaries
        time = bool(summaries)
        # Find out from the tagger how long the input it read in was
        input_length = self.tagger.input_length
        # Create and initialise a chart for parsing
        # Don't initialise the chart with signs - we'll add signs gradually instead
        chart = self._create_chart(
                                [[]]*input_length,
                                derivations=derivations)
        
        # Launch a chart inspector if requested
        if self.options['inspect'] or inspect:
            # Get a string form of the input to display
            input_strs = self.tagger.get_string_input()
            chart.launch_inspector(input=input_strs)
        # Start dumping the chart if requested
        if self.options['dump_chart']:
            # Make the first dump of the empty chart
            from .chart import dump_chart
            dump_chart(chart, self.options['dump_chart'])
        # Stop after a given number of iterations
        if self.options['max_iter'] == 0:
            max_iter = None
        else:
            max_iter = self.options['max_iter']
            
        if self.options['min_iter'] == -1:
            # Special case: never stop until we've got all the categories
            min_iter = None
        else:
            min_iter = self.options['min_iter']
            
        required_parses = self.options['parses']
        
        timeout = 60*self.options['timeout']
        check_timeout = timeout>0
        # Make sure the timed out flag is unset to start with
        self.timed_out = False
        
        # This is where progress output will go
        # Note that it's not the same as logger, which is the main system logger
        prog_logger = self.logger
        
        if check_timeout:
            prog_logger.info("Due to timeout after %d mins" % self.options['timeout'])
        
        ##################################################
        ### Here is the parser itself.
        # Keep track of how long since we started for timing out
        timeout_timer = ExecutionTimer(clock=True)
        
        signs_taken = [0]*input_length
            
        offset = 0
        last_lexicals = [0]*(input_length)
        try:
            # Keep adding signs until none left, or we get a full parse, 
            #  or we complete the maximum iterations allowed
            # Keep going if min_iter is None (special value meaning don't stop 
            #  when we get a parse
            while (min_iter is None or (offset < min_iter) \
                                        or len(chart.parses) < required_parses):
                if max_iter is not None and offset >= max_iter:
                    # Exceded maximum number of iterations: give up
                    prog_logger.info("Reached maximum number of iterations: "\
                                        "continuing to backoff/fail")
                    break
                prog_logger.info(">>> Parsing iteration: %d" % (offset+1))
                # Get new signs from the tagger
                added = self._add_signs(offset=offset)
                # Note whether we added anything new
                if added:
                    # Apply unary rules to these new signs
                    added_spans = set([(start,end) for (start,end,sign) in added])
                    for (start,end) in added_spans:
                        chart.apply_unary_rules(start,end)
                else:
                    # No new signs added by the tagger: no point in continuing 
                    prog_logger.info("No new signs added: ending parse")
                    break
                 
                ##### Main parser loop: produce all possible results
                # Set end point to each node
                for end in range(1,input_length+1):
                    if time:
                        # Start a timer
                        timer = ExecutionTimer()
                    chart.apply_unary_rules(end-1, end)
                    
                    # Set start point to each node before the end, in reverse order
                    for start in range(end-2,-1,-1):
                        for middle in range(start+1,end):
                            chart.apply_binary_rules(start, middle, end)
                            
                            # Check whether the timeout has expired and don't process 
                            #  any more if it has
                            if check_timeout:
                                # Check whether the timeout has passed
                                if int(timeout_timer.get_time()) > timeout:
                                    # Move on to post-parse stuff
                                    raise ParserTimeout
                        
                        # Check for new unary rule applications
                        chart.apply_unary_rules(start, end)
                
                    if summaries:
                        prog_logger.info("Completed parsing up to node %d / %d (%.2f secs)" % (end,input_length, timer.get_time()))
                        if summaries != 2:
                            prog_logger.info(chart.summary)
                    if self.options['dump_chart']:
                        # Dump an update of the chart to the file
                        dump_chart(chart, self.options['dump_chart'])
                    
                if summaries:
                    prog_logger.info("Completed parsing to end of sequence")
                    if summaries != 2:
                        prog_logger.info(chart.summary)
                
                offset += 1
        except ParserTimeout:
            # The given timeout elapsed: just continue with no parses
            prog_logger.info("Parse timeout (%d mins) expired: continuing "\
                            "to backoff/fail" % self.options['timeout'])
            # Set the timed_out flag so we can check later whether we timed out
            self.timed_out = True
        except KeyboardInterrupt:
            # We pass the interrupt on to a higher level, but first kill 
            #  the inspector window, so it doesn't hang around and mess up
            self.chart.kill_inspector()
            raise
        
        parses = chart.parses
        if len(parses) == 0 and self.backoff is not None:
            prog_logger.info("Using backoff model")
            backoff_results = self.run_backoff()
            if len(backoff_results) > 0:
                for res in backoff_results:
                    # Put the semantics result into a sign, with a dummy 
                    #  syntactic category
                    sign = self.grammar.formalism.Syntax.Sign(
                                self.grammar.formalism.Syntax.DummyCategory(),
                                res)
                    # If the semantics has a probability, put this on the sign
                    if hasattr(res, "probability"):
                        sign.probability = res.probability
                    parses.append(sign)
        elif len(parses):
            prog_logger.info("Parse finished with %d results" % len(parses))
        else:
            prog_logger.info("Parse finished with no results")
        
        # Close the inspector window if one was opened
        if not self.options['inspect_persist']:
            self.chart.kill_inspector()
        
        return parses

class DirectedCkyParser(Parser):
    """
    DirectedCkyParser is a special version of the CKY parser that tries 
    to produce a parse according to a pre-built derivation tree.
    
    Why?
    Canonical trees are stored implicitly in the Jazz corpus. We can 
    build the explicit structure of the trees, in accordance with the 
    implicit manual annotations, but this will not contain any signs 
    on internal nodes. The structure does not produce a parse in itself 
    or even verify that the sequence can be parsed with that structure.
    
    The purpose of the DirectedCkyParser is to take a description of 
    this annotated structure and actually perform the parse, packing 
    the chart with only those signs that the derivation structure 
    produces.
    
    The parser should be used with a tagger that assigns only those 
    signs that were annotated. Use the PretaggedTagger to do this.
    
    """
    PARSER_OPTIONS = Parser.PARSER_OPTIONS + [
        ModuleOption('derivations', filter=bool,
            help_text="Store derivation traces along with the results",
            usage="derivations=X, where X is 'True' or 'False'.",
            default=None,
        ),
    ]
    
    def __init__(self, grammar, tagger, derivation_tree=None, *args, **kwargs):
        if derivation_tree is None:
            raise ValueError, "DirectedCkyParser must be instantiated "\
                "with a derivation tree in kwarg 'derivation_tree'."
        self.derivation_tree = derivation_tree
        super(DirectedCkyParser, self).__init__(grammar,tagger,*args,**kwargs)
    
    def _create_chart(self, *args, **kwargs):
        self.chart = Chart(self.grammar, *args, **kwargs)
        return self.chart
        
    def parse(self, derivations=False, summaries=False):
        """
        Run the parser on the input, using the specified tagger. Runs 
        the CKY parsing algorithm to do chart parsing. For details of 
        chart parsing, see Chart class.
        """
        if 'derivations' in self.options and self.options['derivations'] is not None:
            derivations = self.options['derivations']
            
        # Find out from the tagger how long the input it read in was
        input_length = self.tagger.input_length
        # Create and initialise a chart for parsing
        # Don't initialise the chart with signs - we'll add signs gradually instead
        chart = self._create_chart(
                                signs=[[]]*input_length,
                                derivations=derivations)
        
        ##################################################
        ### Here is the parser itself
            
        # Only get signs from the tagger once: we expect to get them all first time
        # Add all the lexical signs to the chart
        for word in range(input_length):
            new_cat_pairs = self.tagger.get_signs_for_word(word)
            new_cats = [cat for (cat, tag, prob) in new_cat_pairs]
            chart.add_word_signs(new_cats, word, self.tagger.get_word(word))
        
        ##### Main parser loop: produce only the signs that we're directed to produce
        # Get a mapping from the tree's short rule names to the rule instances
        rule_mapping = self.grammar.formalism.PcfgParser.rule_short_names
        # Perform the parse bottom up by a depth-first left-to-right 
        #  recursion on the derivation tree. Recursively parse children
        #  of each node, before applying rules for the node itself.
        def _fill_chart(start, tree_node):
            """
            Recursively fills the chart using the subtree rooted by 
            tree_node, using start as the leftmost node of the chart.
            Returns the resulting rightmost node covered by this 
            span.
            """
            if hasattr(tree_node, 'children') and len(tree_node.children) > 0:
                if len(tree_node.children) > 2:
                    raise DirectedParseError, "invalid derivation tree. "\
                        "Nodes may have up to 2 children. This node has "\
                        "%d: %s" % (len(tree_node.children), tree_node)
                ### An internal node
                # First recurse to the sub-parses
                sub_end = start
                middle = None
                for child in tree_node.children:
                    sub_end = _fill_chart(sub_end, child)
                    if middle is None:
                        # Store the first node after the start as the middle node
                        middle = sub_end
                # We now know where this span ends.
                end = sub_end
                # Apply the rule associated with the node
                try:
                    rule_details = rule_mapping[tree_node.rule]
                except KeyError:
                    raise DirectedParseError, "tree node %s specifies a "\
                        "rule '%s' which is not defined for this "\
                        "formalism. Are you using the right formalism "\
                        "for your data?" % (tree_node, tree_node.rule)
                rule_cls = self.grammar.formalism.rules[rule_details[0]]
                # Instantiate the rule
                rule_kwargs = {
                    'grammar' : self.grammar,
                    'modalities' : self.grammar.modality_tree,
                }
                rule_kwargs.update(rule_details[1])
                rule = rule_cls(**rule_kwargs)
                # Try applying the rule to the arguments we've generated
                # Check we have the right number of children
                if len(tree_node.children) != rule.arity:
                    raise DirectedParseError, "a node was encountered "\
                        "that does not have the right number of children "\
                        "for its rule. %s must have %d children." % \
                        (tree_node.rule, rule.arity)
                # Apply the rule to its one or two arguments
                if rule.arity == 1:
                    added = chart.apply_unary_rule(rule, start, end)
                    debug_inputs = "%s, [%s]" % (rule,
                        ", ".join(["%s" % s for s in chart.get_signs(start, end)])
                    )
                elif rule.arity == 2:
                    added = chart.apply_binary_rule(rule, start, middle, end)
                    debug_inputs = "%s, [%s] and [%s]" % (rule,
                        ", ".join(["%s" % s for s in chart.get_signs(start, middle)]),
                        ", ".join(["%s" % s for s in chart.get_signs(middle, end)])
                    )
                # If nothing was added to the chart, the rule must have failed
                if not added:
                    # No point in continuing, since stuff further up the 
                    #  tree will inevitably fail
                    raise DirectedParseError, "failed to apply rule %s. "\
                        "Giving up on parse. "\
                        "Tree: %s. Inputs: %s." % \
                        (tree_node.rule, tree_node, debug_inputs)
            elif hasattr(tree_node, 'chord'):
                ### Leaf node
                # We assume this lines up with the correct position in 
                #  the tags that the tagger has given us.
                # This arc is a leaf, so only has a span of 1.
                end = start + 1
            else:
                # Tree does not conform to correct interface
                raise DirectedParseError, "derivation tree for directed "\
                    "parse should be made up of internal trees with "\
                    "children and leaves with a chord attribute. This "\
                    "node is neither: %s" % tree_node
            return end
        rightmost = _fill_chart(0, self.derivation_tree)
            
        return chart.parses

class DirectedParseError(Exception):
    pass

class ParserTimeout(Exception):
    pass
