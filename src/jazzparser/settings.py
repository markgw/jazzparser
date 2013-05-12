"""Global settings for the Jazz Parser.

This module is imported by other modules to access global settings.
"""

import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# Where all the source code lives (absolute path)
SOURCE_DIR = os.path.join(PROJECT_ROOT, "src")
# Where the statistical model data lives
MODEL_DATA_DIR = os.path.join(PROJECT_ROOT, "etc", "data")
# Model data for PCFG models
PCFG_MODEL_DATA_DIR = os.path.join(MODEL_DATA_DIR, "pcfg")
# A slightly different location for backoff model data
BACKOFF_MODEL_DATA_DIR = os.path.join(PROJECT_ROOT, "etc", "backoff_data")
# Where the XML grammar definitions live
GRAMMAR_DATA_DIR = os.path.join(PROJECT_ROOT, "grammars")
# Where config files and local data are stored
LOCAL_DATA_DIR = os.path.join(PROJECT_ROOT, "etc", "local")
# Generic temporary directory for any purpose
TEMP_DIR = os.path.join(PROJECT_ROOT, "etc", "tmp")
# Where external corpora are stored within the project
CORPORA_DIR = os.path.join(PROJECT_ROOT, "input", "corpora")
# Where tonal space analysis sets live
ANALYSIS_DATA_DIR = os.path.join(PROJECT_ROOT, "etc", "analyses")
# Where data for unit tests is stored
TEST_DATA_DIR = os.path.join(PROJECT_ROOT, "etc", "test")
# Where shell states should be stored
SHELL_STATE_DIR = os.path.join(PROJECT_ROOT, "etc", "shell_state")
# Where releases are built
RELEASE_BUILD_DIR = os.path.join(TEMP_DIR, "release")

# The version ID of the software currently
from . import __version__
CURRENT_VERSION = __version__

# Sets the name of the default grammar that will be used if none other is
#  specified on the command line.
DEFAULT_GRAMMAR = "jazz3.0"

# The type of supertagger that should be used by default
DEFAULT_SUPERTAGGER = 'full'

# The grammar infrastructure to use by default
# This doesn't usually make a difference, since it's specified by the grammar (in the XML)
# If it's omitted from the XML this will be used, and some tools will assume 
#  the default formalism if no other information is available
DEFAULT_FORMALISM = 'music_halfspan'

# The parser algorithm module to use by default
DEFAULT_PARSER = 'cky'

# Substrings that are stripped from input sequences given in plain text format
IGNORED_INPUT_STRINGS = [ "|", ]

# Output warnings during derivation if there are free variables in the semantics
WARN_ABOUT_FREE_VARS = False

# File to save the interactive shell's history to
SHELL_HISTORY_FILE = os.path.join(LOCAL_DATA_DIR, "shell-history")
# File to save the input prompt's history to
INPUT_PROMPT_HISTORY_FILE = os.path.join(LOCAL_DATA_DIR, "input-history")
# File to save the tagger test input loop's history to
TAG_PROMPT_HISTORY_FILE = os.path.join(LOCAL_DATA_DIR, "tag-history")
# Ngram query script history
NGRAM_QUERY_HISTORY_FILE = os.path.join(LOCAL_DATA_DIR, "ngram-history")

class OPTIONS:
    ## These are defaults that may be overridden by cmd line opts
    # Global flag to decide whether to output times on all semantic objects or just TDs
    OUTPUT_ALL_TIMES = False
    # Global flag to toggle between Latex and text output
    OUTPUT_LATEX = False
    # Output options that each formalism defines, indexed by formalism name
    OUTPUT = {}

class CANDC:
    BASE_PATH = os.path.join(PROJECT_ROOT, "lib", "candc")
    MODELS_PATH = os.path.join(PROJECT_ROOT, "etc", "candc_data")
    DEFAULT_TRAINING_PARAMS = {
        'super-category_cutoff' : '0',
        'super-cutoff_default' : '0',
        'super-cutoff_words' : '0',
        #'super-rare_cutoff' : '20', # This makes no difference
        'super-tagdict_min' : '0',
        'super-tagdict_ratio' : '10000',
        'super-beam_width' : '20',
        'super-beam_ratio' : '0.0',
        #'super-model_sigma' : '0.9',
        'sigma' : '0.85',
    }
    LOG_DIRECTORY = os.path.join(PROJECT_ROOT, "etc", "log", "candc")
    
class PCFG_PARSER:
    ### Default settings ###
    # These can be overridden by module options
    ########################
    # Module option: threshold
    # Maximum ratio between the highest probability in a cell and the lowest
    #  before the lower end gets chucked out
    DEFAULT_THRESHOLD = 0.01
    # Module option: maxarc
    # Maximum number of signs in a cell before the lower probability ones 
    #  get chucked out
    DEFAULT_MAX_ARC_SIZE = 20
    ### Default training options ###
    # These too can be overridden by module options
    ########################
    # Module option: cat_bins
    # Number of possible categories to reserve mass for when smoothing
    # This number is the number of theoretically possible categories in halfspan
    # TODO: This is an overestimate, it should be 1296
    # TODO: Try the model with 1296 instead
    DEFAULT_CAT_BINS = 4752

class TEST:
    """
    Settings and common constants for unit tests (see L{jptests}).
    
    """
    SEQUENCE_DATA = os.path.join(PROJECT_ROOT, "input", "fullseqs")
