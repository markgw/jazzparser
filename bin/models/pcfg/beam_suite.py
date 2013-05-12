#!/usr/bin/env ../../jazzshell
"""
A suite of parsing experiments on a subset of the corpus exploring different 
beam settings.

"""
from subprocess import PIPE, Popen, STDOUT, call
from optparse import OptionParser
import os, csv

from jazzparser.utils.config import ConfigFile

BASE_CONFIG = """
%% INCLUDE %{PROJECT_ROOT}/input/config/pcfg/eval/base/beam.conf
"""


def main():
    usage = "%prog [options]"
    description = "Runs a suite of small parsing experiments to try different beam settings"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    cmd_dir = os.path.abspath(os.path.join("..", ".."))
    parser = os.path.join(cmd_dir, "jazzparser")
    result_eval = os.path.join(cmd_dir, "analysis", "result_eval.py")
    result_eval_dir = os.path.join(cmd_dir, "analysis")
    
    # Try all combinations of threshold and maxarc settings
    settings = [(threshold,maxarc) for threshold in [0.5, 0.1, 0.01, 0.001] \
                                   for maxarc in [5, 10, 15, 20]]
    # Don't try different thresholds for maxarc=1: they're all the same
    settings.append((0.1, 1))
    
    # Open a CSV file to write the results to
    with open("test_suite.csv", "w") as result_file:
        results = csv.writer(result_file)
        results.writerow(["Threshold", "Maxarc", "Dep rec"])
        
        for threshold,maxarc in settings:
            print "\n#####################################################"
            print "### Threshold %s, maxarc %d ###" % (threshold, maxarc)
            
            # Build a config file string for these settings
            options = "%%%% DEF threshold %s\n" % threshold
            options += "%%%% DEF maxarc %d\n" % maxarc
            conf = ConfigFile.from_string(options+BASE_CONFIG)
            # Run the parser
            retcode = call([parser]+conf.get_strings(), 
                                 cwd=cmd_dir, stderr=STDOUT)
            if retcode:
                print "Parse failed"
                # Don't bother continuing with the others
                return 1
            
            # Find out where the output was being put
            output_dir = dict(conf.options)['output']
            files = os.path.join(output_dir, "*.res")
            # Evaluate all the results files in that directory
            eval_proc = Popen([result_eval, files, "--mopt output=f", 
                                    "-m deprec", "-q"], 
                                cwd=result_eval_dir, stdout=PIPE)
            eval_out = eval_proc.stdout.read()
            f_score = eval_out.rstrip().rstrip("%")
            
            # Write the result out to the summary file
            results.writerow(["%s" % threshold, 
                              "%d" % maxarc,
                              f_score])
            # Flush the file object so each result appears immediately
            result_file.flush()


if __name__ == "__main__":
    main()
