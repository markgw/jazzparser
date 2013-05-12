"""Interface to external C&C supertagger tools.

Uses the C&C tagger out of the box.
The C&C tagger must have been installed in the candc directory for this 
to work. It must also have be trained on some data before it can be 
used.

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
__author__ = "Mark Wilding <mark.wilding@cantab.net>" 

import os, logging, shutil
from subprocess import Popen, PIPE

from jazzparser import settings
from jazzparser.utils.base import group_pairs
from jazzparser.utils.options import ModuleOption
from jazzparser.utils.chords import interval_observation_from_chord_string_pair
from jazzparser.utils.probabilities import batch_sizes
from jazzparser.utils.strings import str_to_bool
from jazzparser.utils.loggers import create_logger
from jazzparser.utils.output import remove_ansi_colors
from jazzparser.taggers import Tagger, process_chord_input
from jazzparser.taggers.models import ModelTagger, TaggerModel
from jazzparser.taggers.chordmap import get_chord_mapping, \
                                    get_chord_mapping_module_option
from jazzparser.data import Fraction
from .training import train_model_on_sequence_list
from .utils import read_tag_list

# Get the logger from the logging system
logger = logging.getLogger("main_logger")

class CandcTaggerModel(TaggerModel):
    """
    This is really a fake: it doesn't actually save models itself, since we hand 
    over to the C&C tagger to do that. It provides the public methods of 
    tagger models so that we can use all the usual tagger training and 
    evaluation scripts without any special hacks.
    
    """
    MODEL_TYPE = 'candc'
    # Set up possible options for training
    TRAINING_OPTIONS = [
        get_chord_mapping_module_option(),
        # There should be some training options for C&C made available here, 
        #  but at the moment it's just a standard set
    ] + TaggerModel.TRAINING_OPTIONS
    
    def train(self, input_data, grammar=None, logger=None):
        # Get the sequence list from the bulk input data
        sequences = input_data.sequences
        train_model_on_sequence_list(self.model_name, sequences, 
                                    chordmap=self.options['chord_mapping'])
        # Put any extra opts in a dict to put in a file
        extra_opts = {
            'chordmap' : self.options['chord_mapping'].name,
        }
        # Store extra tagging options that aren't part of the C&C model
        opts_filename = os.path.join(settings.CANDC.MODELS_PATH, 
                                     *(self.model_name.split(".")+["jpopts"]))
        with open(opts_filename, 'w') as opts_file:
            for (key,val) in extra_opts.items():
                print >>opts_file, "%s:%s" % (key,val)
        
    @staticmethod
    def load_model(model_name):
        """ Override to provide non-standard behaviour """
        return CandcTaggerModel(model_name)
    
    def save(self):
        return
    
    def _get_tags(self):
        # TODO
        raise NotImplementedError, "C&C tagger model can't report tags yet"
        return []
    tags = property(_get_tags)
    
    @staticmethod
    def list_models():
        model_dir = settings.CANDC.MODELS_PATH
        if not os.path.exists(model_dir):
            return []
        names = [name for name in os.listdir(model_dir) \
                        if not name.startswith(".")
                        and os.path.isdir(os.path.join(model_dir, name))]
        model_names = []
        # Allow sub-models to be in subdirectories
        for dirname in names:
            # Check whether there are subdirs
            subdirs = [name for name in os.listdir(os.path.join(model_dir, dirname)) \
                        if not name.startswith(".") \
                        and os.path.isdir(os.path.join(model_dir, dirname, name))]
            if len(subdirs) > 0:
                model_names.extend(["%s/%s" % (dirname,subdir) for subdir in subdirs])
            else:
                model_names.append(dirname)
        return model_names
    
    def delete(self):
        shutil.rmtree(os.path.join(settings.CANDC.MODELS_PATH, *(self.model_name.split("/"))))
    

class CandcTagger(ModelTagger):
    """
    Superclass of both kinds of C&C tagger. Don't use this: use one 
    of the subclasses below.
    """
    MODEL_CLASS = CandcTaggerModel
    COMPATIBLE_FORMALISMS = [
        'music_roman',
        'music_keyspan',
        'music_halfspan',
    ]
    INPUT_TYPES = ['db', 'chords']
    # Probability ratio between one tag and the next that allows the 
    #  second to be returned in the same batch as the first
    TAG_BATCH_RATIO = 0.8
    DEFAULT_UNSEEN_TAG_PROB = 0.001
    
    TAGGER_OPTIONS = [
        ModuleOption('batch', filter=float, 
            help_text="Probability ratio between one tag and the next "\
                "that allows the second to be returned in the same batch.",
            usage="batch=X, where X is a floating point value between 0 and 1",
            default=TAG_BATCH_RATIO),
        ModuleOption('model', 
            help_text="Name of the C&C trained model to use. Use the C&C "\
                "training scripts to produce this.",
            usage="model=X, where X is the model name. Split up multi-level models with dots.",
            required=True),
        ModuleOption('unseen_tag_prob', filter=float, 
            help_text="Probability mass reserved on each word so that some "\
                "probability is assigned to tags never seen in the training "\
                "set. This is a form of plus-n smoothing. "\
                "Substracted from the total probability of tags for "\
                "each word and distributed evenly across all tags.", 
            usage="unseen_tag_prob=X, where X is a floating point value between 0 and 1",
            default=DEFAULT_UNSEEN_TAG_PROB),
        ModuleOption('last_batch', filter=str_to_bool, 
            help_text="Use all possible tags, including the last, lowest "\
                "probability batch, which typically acts as a bin for "\
                "all remaining tags", 
            usage="last_batch=X, where X is 'true' or 'false'",
            default=True),
    ] + ModelTagger.TAGGER_OPTIONS
    
    def __init__(self, grammar, input, options={}, dict_cutoff=5, *args, **kwargs):
        super(CandcTagger, self).__init__(grammar, input, options, *args, **kwargs)
        process_chord_input(self)
        
        if type(self) == CandcTagger:
            raise NotImplementedError, "Tried to instantiate CandcTagger "\
                "directly. You should use one of its subclasses."
        self.tag_batch_ratio = self.options['batch']
        model = self.options['model'].split('.')
        
        # Check that candc is available for supertagging
        if not os.path.exists(settings.CANDC.BASE_PATH):
            raise CandcConfigurationError, "The C&C parser base "\
                "directory %s does not exist" % settings.CANDC.BASE_PATH
        if not os.path.exists(settings.CANDC.MODELS_PATH):
            raise CandcConfigurationError, "The C&C parser models "\
                "directory %s does not exist" % settings.CANDC.MODELS_PATH
        candc_cmd = os.path.join(settings.CANDC.BASE_PATH, "bin", self.command)
        if not os.path.exists(candc_cmd):
            raise CandcConfigurationError, "The C&C supertagger command "\
                "%s does not exist. Have you built it?" % candc_cmd
        # Check the model exists
        candc_model = os.path.join(settings.CANDC.MODELS_PATH, *(model))
        if not os.path.exists(candc_model):
            raise CandcConfigurationError, "The C&C model given (%s) "\
                "doesn't exist." % candc_model
        
        # Create a logger to dump the output to
        logfile = os.path.join(settings.CANDC.LOG_DIRECTORY, "-".join(model))
        candc_logger = create_logger(filename=logfile)
        self.logger.info("Logging C&C output to %s" % logfile)
        # Note in the log what we're trying to tag
        candc_logger.info("Tagging: %s" % " ".join([str(crd) for crd in self.input]))
        
        # Read in the list of tags to smooth over
        self.tag_list = read_tag_list(os.path.join(candc_model, "tags"))
        
        # Read in extra options
        opts_filename = os.path.join(candc_model, "jpopts")
        if not os.path.exists(opts_filename):
            self.extra_opts = {}
        else:
            with open(opts_filename, 'r') as opts_file:
                self.extra_opts = dict(
                    [line.strip("\n").split(":", 1) 
                        for line in opts_file.readlines()])
        # Pull the chord mapping out of the options
        self.chordmap = get_chord_mapping(self.extra_opts.get('chordmap', None))
        
        # Spawn a process to do the tagging
        candc_command = [candc_cmd, "--model", candc_model, 
                        "--dict_cutoff", "%d" % dict_cutoff]+self.extra_args
        self.tagger = Popen(candc_command, 
                            stdin=PIPE, stdout=PIPE, stderr=PIPE)
        candc_logger.info("C&C command: %s" % " ".join(candc_command))
            
        self.tokens = self.input
        # Build some observations from the tokens
        observations = [
            interval_observation_from_chord_string_pair(ch1,ch2,type_mapping=self.chordmap) 
                for ch1,ch2 in group_pairs(self.tokens+[None])
        ]
        # Add a dummy POS tag to each input item
        self.observations = ["%s|C" % t for t in observations]
        candc_logger.info("Input: %s" % " ".join(self.observations))
        
        # Run the tagger on this input
        try:
            tagger_out, tagger_err = self.tagger.communicate(" ".join(self.observations))
        except OSError, err:
            logger.error("Could not run the C&C supertagger (%s)" % err)
            candc_logger.error("Error: %s" % err)
            # Output the actual error that the command returned
            error = self.tagger.stderr.read()
            logger.error("C&C returned the error: %s" % error)
            candc_logger.error("C&C error: %s" % error)
            raise CandcTaggingError, "error running the C&C supertagger: %s" % error
        # C&C uses ANSI color commands in the output
        # Remove them
        tagger_out = remove_ansi_colors(tagger_out)
        tagger_err = remove_ansi_colors(tagger_err)
        # The tagger process should now be terminated. Check it didn't fall over
        return_code = self.tagger.returncode
        if return_code < 0:
            raise CandcTaggingError, "The C&C tagger terminated with return code %s. "\
                "Error output for the tagging: %s" % (return_code, tagger_err)
        
        # Format the string for slightly easier reading in the logfile
        log_output = tagger_out.replace("\t", ", ")
        output_lines = [line for line in log_output.split("\n") if line.strip()]
        log_output = "\n".join(["%d-%d: %s" % (i,i+1,outline) for (i,outline) in enumerate(output_lines)])
        candc_logger.info("Output: %s" % log_output)
        candc_logger.info("Stderr output: %s" % tagger_err)
        
        # Get the tags out of the tagger output.
        # We ignore the first two items (word and POS tag) and take the third (category)
        # The output format for the different taggers varies
        self.tags = self._tags_from_output(tagger_out)
        
        # Check for bogus tags
        # The tagger may return tags that can't actually be 
        #  instantiated with the word, since it doesn't know about 
        #  the lexicon: ignore them
        #print "\n".join(", ".join(tag for (sign,tag,prob) in taglist) for taglist in self.tags)
        self.tags = [
            [(sign,tag,prob) for (sign,tag,prob) in self.tags[time] \
                    if sign is not None] 
                for time in range(len(self.tags))]
        
    def _get_input_length(self):
        """ Returns the number of words (chords) in the input. """
        return len(self.tokens)
    input_length = property(_get_input_length)
        
    def get_signs_for_word(self, index, offset=0):
        batch_sizes = self.batch_sizes[index]
        
        if self.options['last_batch']:
            # This will return all batches
            end_of_tags = len(batch_sizes)
        else:
            # This will never return the final batch
            end_of_tags = len(batch_sizes) - 1
        
        if offset >= end_of_tags:
            # No more categories to return
            return []
        
        tags = self.tags[index]
        if offset == 0:
            returned_so_far = 0
        else:
            returned_so_far = sum(batch_sizes[:offset])
        range_end = returned_so_far + batch_sizes[offset]
        
        tag_probabilities = tags[returned_so_far:range_end]
        return tag_probabilities
        
    def get_word(self, index):
        return self.tokens[index]
        
        
class CandcBestTagger(CandcTagger):
    """
    Uses the C&C supertagger component to get the best tag for each 
    word. Returns only one tag per word.
    """
    command = "super"
    extra_args = []
    
    def __init__(self, *args, **kwargs):
        super(CandcBestTagger, self).__init__(*args, **kwargs)
        
    def _tags_from_output(self, output):
        tag_sequence = [out.split("|")[2] for out in output.split()]
        # Get a sign for this tag if possible
        results = [[(self.grammar.get_sign_for_word_by_tag(
                                self.tokens[i],
                                tag,
                                extra_features={
                                    'duration' : self.durations[i],
                                    'time' : self.times[i],
                                }),
                     tag,
                     1.0)]
                        for i,tag in enumerate(tag_sequence)]
        self.batch_sizes = [[1]]*self.input_length
        return results
        
class CandcMultiTagger(CandcTagger):
    """
    Uses the C&C supertagger component to get multiple tags for each 
    word.
    """
    command = "msuper"
    # Use a very low beta, so we get loads of tags, even improbable ones
    extra_args = ["--beta", "0.0"]
    
    TAGGER_OPTIONS = CandcTagger.TAGGER_OPTIONS + [
        ModuleOption('ignore-unknown', filter=str_to_bool,
            help_text="Ignore any tags that the tagger returns but which "\
                "are not found in the grammar. By default, an error will "\
                "be thrown.",
            usage="ignore-unknown=True (default False)",
            default=False),
    ]
    
    def __init__(self, *args, **kwargs):
        super(CandcMultiTagger, self).__init__(*args, **kwargs)
        
    def _tags_from_output(self, output):
        tags = []
        # Split up the output text to extract tags and probabilities
        for line in output.split("\n"):
            line = line.strip()
            if len(line):
                cols = line.split("\t")
                num_results = int(cols[2])
                results = []
                all_tags = []
                # Get the tags and probs from the output
                for result_num in range(num_results):
                    cat = cols[3+result_num*2]
                    prob = float(cols[4+result_num*2])
                    results.append((cat, prob))
                    all_tags.append(cat)
                
                # Check all the tags are covered and add them with 0 prob if not
                for tag in self.tag_list:
                    if tag not in all_tags:
                        results.append((tag, 0.0))
                
                tags.append(list(reversed(sorted(results, key=lambda x:x[1]))))
        
        if len(tags) != self.input_length:
            raise CandcTaggingError, "C&C output did not give a correct "\
                "set of tags: %s" % output
        
        # Redistribute the tag probability to account for unseen tags
        if self.options['unseen_tag_prob'] > 0.0:
            unseen_prob = self.options['unseen_tag_prob']
            # Scale down everything that has a probability
            prob_scale = 1.0 - unseen_prob
            for i in range(len(tags)):
                # Add reserved mass equally to every tag
                prob_add = unseen_prob / len(tags[i])
                tags[i] = [(tag,(prob*prob_scale+prob_add)) for \
                                    tag,prob in tags[i]]
        
        skip_tags = []
        # Work out what tags we're going to ignore altogether
        if self.options['ignore-unknown']:
            for tag_sequence in tags:
                for tag,prob in tag_sequence:
                    if tag not in self.grammar.families:
                        # This tag's not in the grammar: just ignore it
                        skip_tags.append(tag)
                        logger.warn("Ignoring tag '%s', which is not in "\
                            "the grammar." % tag)
        #~ #### I've already done this above
        #~ # Some tags get given zero probability by the model, either because 
        #~ #  it's not smoothing enough, or because of rounding errors
        #~ # We do a basic smoothing here, giving everything with 0 probability 
        #~ #  a probability smaller than the smallest the model assigned
        #~ smoothed_tags = []
        #~ for tag_probs in tags:
            #~ zeros = sum(prob == 0.0 for (tag,prob) in tag_probs)
            #~ # No need to smooth if everything got some prob
            #~ if zeros:
                #~ smallest = min(prob for (tag,prob) in tag_probs if prob > 0.0)
                #~ if smallest == 1.0:
                    #~ # This occasionally happens and messes things up
                    #~ # Just reserve a small amount for the zeros in this case
                    #~ smallest = 0.001
                #~ # Divide the smallest probability among the zero prob tags 
                #~ #  and discount the others
                #~ smooth_prob = smallest / zeros
                #~ discount = 1.0-(smallest)
                #~ tag_probs = [(tag, prob*discount if prob > 0.0 
                                                 #~ else smooth_prob) 
                                            #~ for (tag,prob) in tag_probs]
            #~ smoothed_tags.append(tag_probs)
        #~ print smoothed_tags
        
        signs = [[] for i in range(self.input_length)]
        # Get an actual sign for each word/tag combination
        for index,word in enumerate(self.tokens):
            for (tag,prob) in tags[index]:
                if tag not in skip_tags:
                    # Consult the grammar to get a suitable sign if we can
                    sign = self.grammar.get_sign_for_word_by_tag(
                                            word,
                                            tag,
                                            extra_features={
                                                'time' : self.times[index],
                                                'duration' : self.durations[index]
                                            })
                    signs[index].append((sign,tag, prob))
                
        self.batch_sizes = []
        for results in signs:
            # Work out the batches that these should be returned in
            self.batch_sizes.append(batch_sizes([p for __,__,p in results], self.tag_batch_ratio))
        return signs
        
class CandcTaggingError(Exception):
    pass
class CandcConfigurationError(Exception):
    pass

