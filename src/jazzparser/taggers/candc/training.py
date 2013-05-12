"""Training interface to the C&C supertagger.

This automates the process of training the C&C supertagger on data 
from the database. The data should first be generated using the 
script in the annotator bin.

Training data should be in the Jazz Parser format, which differs 
slightly from the C&C format. Instead of <obs>|<pos>|<tag>, each chord 
should have be represented as <chord>|<obs>|<pos>|<tag>. Use 
generate_model_data to generate this from the database.

"""
import os, shutil
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE

from jazzparser import settings
from jazzparser.utils.data import holdout_partition
from jazzparser.utils.output import remove_ansi_colors
from .utils import training_data_to_candc, sequence_index_to_training_file, \
                    sequence_list_to_training_file, generate_tag_list
from jazzparser.data.db_mirrors import SequenceIndex

def train_model(model, data_filename, holdout_partitions=0, train_params={}, 
                    chordmap=None):
    """
    Train a C&C model by calling the C&C supertagger training routine.
    
    model should be a model name to train/retrain.
    data_filename should be the path to a training data file in the 
    hybrid C&C format.
    params is an optional dict of (string) parameter values to feed 
    to the C&C trainer. Only certain parameter values will be allowed. 
    These will override the default parameters in settings.CANDC. Set
    a parameter to None or an empty string to use C&C's default.
    
    """
    command = os.path.join(settings.CANDC.BASE_PATH, "bin", "train_super")
    
    # Process parameters that we'll use for training
    params = settings.CANDC.DEFAULT_TRAINING_PARAMS.copy()
    params.update(train_params)
    extra_args = []
    # Prepare the args for the training command with these parameters
    for key,val in params.items():
        if val is not None and val != "":
            extra_args.append('--%s' % key)
            extra_args.append(str(val))
    
    def _train(dest_model, filename):
        """ Train a model using the train_super command. """
        model_path = os.path.join(settings.CANDC.MODELS_PATH, *(dest_model))
        if not os.path.exists(model_path):
            os.makedirs(model_path)
        # Store a list of possible tags so we can smooth over unseen ones
        generate_tag_list(os.path.join(model_path, "tags"))
        # Run the training
        command_args = [command, "--model", model_path, "--comment", 
                        "\"Model trained automatically on chord data in file %s\"" % data_filename,
                        "--input", filename,
                        # Tell C&C to put the tagdict in the model dir
                        # Doc says this is the default, but it isn't...
                        "--super-tagdict", "//tagdict"] + extra_args
        print "Running: %s" % " ".join(command_args)
        trainer = Popen(command_args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        trainer.wait()
        if trainer.returncode != 0:
            raise CandcTrainingError, "There was an error training a "\
                    "supertagger model from the file %s: \n%s" % (data_filename, trainer.stderr.read())
        else:
            print "Trained model %s:\n%s" % (model_path, remove_ansi_colors(trainer.stderr.read()).strip("\n"))
    
    # Read the data in from the given filename
    in_file = open(data_filename, 'r')
    lines = in_file.readlines()
    # Convert into the C&C training format
    lines = training_data_to_candc(lines)
    
    model = model.split(".")
    
    if holdout_partitions:
        # Split up the data into n partitions and train on every 
        #  n-1 subset of them.
        
        # Build the lists with each partition held out
        partitions = holdout_partition(lines, holdout_partitions)
        # Train on each partitioned set
        for i,partition in enumerate(partitions):
            print "Training partition %d" % i
            temp_file = NamedTemporaryFile()
            temp_file.write("\n".join(partition))
            temp_file.flush()
            # Train the model on this part of the data
            _train(model+["partition-%s" % i], temp_file.name)
            temp_file.close()
    else:
        temp_file = NamedTemporaryFile()
        temp_file.write("\n".join(lines))
        temp_file.flush()
        # Just train on the whole data
        _train(model, temp_file.name)
        temp_file.close()
        
def train_model_on_sequence_data(model, data_filename, *args, **kwargs):
    """
    Same as train_model, but takes a db_mirrors sequence data file as 
    input, rather than a C&C training data file.
    
    """
    # Read in the training data
    si = SequenceIndex.from_file(data_filename)
    # Generate a temporary file with C&C training data in it
    file = sequence_index_to_training_file(si)
    train_model(model, file.name, *args, **kwargs)

def train_model_on_sequence_index(model, sequenceindex, *args, **kwargs):
    """
    Same as L{train_model_on_sequence_data}, but doesn't read the sequences 
    from a file.
    
    """
    # Generate a temporary file with C&C training data in it
    file = sequence_index_to_training_file(sequenceindex)
    train_model(model, file.name, *args, **kwargs)

def train_model_on_sequence_list(model, sequences, *args, **kwargs):
    """
    Same as L{train_model_on_sequence_data}, but doesn't read the sequences 
    from a file.
    
    """
    # Generate a temporary file with C&C training data in it
    file = sequence_list_to_training_file(sequences)
    train_model(model, file.name, *args, **kwargs)

class CandcTrainingError(Exception):
    pass
