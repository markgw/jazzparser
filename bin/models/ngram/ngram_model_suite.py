#!/usr/bin/env ../../jazzshell
from subprocess import PIPE, Popen, STDOUT
from optparse import OptionParser
import os, csv

from jazzparser.utils.config import ConfigFile

BASE_TRAINING_OPTIONS = """
# Model type
%% ARG 0 ngram-multi
# Input data
%% ARG 2 %{PROJECT_ROOT}/input/fullseqs

# Input type specification
filetype = bulk-db-annotated

# Train for cross-evaluation
partitions = 10

# Don't use a cutoff on any backoff models
opts = backoff_cutoff=0

"""
BASE_TEST_OPTIONS = """
%% ARG 0 ngram-multi
%% ARG 2 %{PROJECT_ROOT}/input/fullseqs
partitions = 10
"""
BASE_ENTROPY_OPTIONS = BASE_TEST_OPTIONS + "+entropy\n"
BASE_ACCURACY_OPTIONS = BASE_TEST_OPTIONS + "+agreement\n"

def output_proc(proc):
    output = ""
    line = proc.stdout.readline()
    while line:
        output += line
        print line.strip("\n")
        line = proc.stdout.readline()
    return output

def main():
    usage = "%prog [options]"
    description = "Trains a suite of ngram models and tests them all"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option('-n', '--no-train', dest="no_train", action="store_true", help="don't train the models. Only do this if you've previously used this script to train all the models")
    parser.add_option('--train', '--only-train', dest="only_train", action="store_true", help="only train the models, don't do the experiments")
    parser.add_option('--bt', '--bigram-trigram', dest="bigram_trigram", action="store_true", help="only include bigram and trigram models")
    parser.add_option('-t', '--trigram', dest="trigram", action="store_true", help="only include trigram models")
    parser.add_option('--wb', '--witten-bell', dest="witten_bell", action="store_true", help="only use witten-bell smoothing (skip laplace)")
    parser.add_option('--lap', '--laplace', dest="laplace", action="store_true", help="only use laplace smoothing (skip witten-bell)")
    parser.add_option('-v', '--viterbi', dest="viterbi", action="store_true", help="use Viterbi decoding")
    parser.add_option('-4', '--4grams', dest="fourgrams", action="store_true", help="run experiments for 4-gram models")
    parser.add_option('-c', '--cutoff', dest="cutoff", action="store", type="int", help="custom cutoff to use, instead of trying several")
    parser.add_option('--gt', '--good-turing', dest="good_turing", action="store_true", help="only use Good-Turing smoothing (not usually included)")
    options, arguments = parser.parse_args()

    cmd_dir = os.path.abspath("..")
    train_cmd = "./train.py"
    tageval_cmd = "./tageval.py"
    
    if options.bigram_trigram:
        orders = [2, 3]
    elif options.trigram:
        orders = [3]
    elif options.fourgrams:
        orders = [4]
    else:
        orders = [1, 2, 3]
    
    if options.witten_bell:
        smoothings = [("witten-bell", "wb")]
    elif options.laplace:
        smoothings = [("laplace", "lap")]
    elif options.good_turing:
        smoothings = [("simple-good-turing", "gt")]
    else:
        smoothings = [("witten-bell", "wb"), ("laplace", "lap")]
    
    if options.cutoff is None:
        cutoffs = [0, 2, 5]
    else:
        cutoffs = [options.cutoff]
    
    # Open a CSV file to write the results to
    with open("test_suite.csv", "w") as result_file:
        results = csv.writer(result_file)
        results.writerow(["Order", "Cutoff", "Smoothing", "Entropy", "Agreement"])

        for model_order in orders:
            for cutoff in cutoffs:
                for smoothing,smoothing_short in smoothings:
                    #for chord_map in ["none", "small", "big"]:
                    print "\n#####################################################"
                    print "### Order %d, cutoff %d, smoothing %s ###" % (model_order, cutoff, smoothing)
                    # Build a unique name for the model
                    model_name = "suite_n%d_c%d_%s" % (model_order, cutoff, smoothing_short)
                    
                    # Train the model
                    if not options.no_train:
                        # Prepare options to train the model
                        model_options = "n=%d:cutoff=%d:backoff=%d:estimator=%s" % \
                            (model_order, cutoff, model_order-1, smoothing)
                        training_opts = BASE_TRAINING_OPTIONS + \
                            "opts = %s\n%%%% ARG 1 %s" % (model_options, model_name)
                        # Turn these nice option specifications into command-line args
                        conf = ConfigFile.from_string(training_opts)
                        # Train this model
                        #train_output = check_output([train_cmd]+conf.get_strings(), cwd=cmd_dir)
                        train_proc = Popen([train_cmd]+conf.get_strings(), 
                                           cwd=cmd_dir, stdout=PIPE, stderr=STDOUT)
                        output_proc(train_proc)
                    
                    if not options.only_train:
                        # Entropy doesn't tell us much for Viterbi decoding
                        if not options.viterbi:
                            # Test the model's entropy
                            print "### Entropy ###"
                            entropy_opts = BASE_ENTROPY_OPTIONS + "%%%% ARG 1 %s" % model_name
                            conf = ConfigFile.from_string(entropy_opts)
                            entropy_proc = Popen([tageval_cmd]+conf.get_strings(), 
                                                 cwd=cmd_dir, stdout=PIPE, stderr=STDOUT)
                            # Output as we go
                            output = output_proc(entropy_proc)
                            # Get the last line and pull out the entropy value
                            last_line = output.strip("\n").rpartition("\n")[2]
                            entropy = float(last_line.split()[0])
                        else:
                            entropy = 0.0
                        
                        # Test the model's top tag accuracy
                        print "\n### Agreement ###"
                        accuracy_opts = BASE_ACCURACY_OPTIONS + "%%%% ARG 1 %s" % model_name
                        if options.viterbi:
                            accuracy_opts += "\ntopt = decode=viterbi"
                        conf = ConfigFile.from_string(accuracy_opts)
                        accuracy_proc = Popen([tageval_cmd]+conf.get_strings(), 
                                             cwd=cmd_dir, stdout=PIPE, stderr=STDOUT)
                        # Output as we go
                        output = output_proc(accuracy_proc)
                        # Get the last line and pull out the agreement value
                        last_line = output.strip("\n").rpartition("\n")[2]
                        agreement = float(last_line.split()[-1].strip("()%"))
                        
                        results.writerow(["%d" % model_order, 
                                          "%d" % cutoff,
                                          "%s" % smoothing,
                                          "%f" % entropy,
                                          "%f" % agreement])
                        # Flush the file object so each result appears in the 
                        #  file immediately
                        result_file.flush()


if __name__ == "__main__":
    main()
