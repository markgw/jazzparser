#!/usr/bin/env ../../jazzshell
"""
Add parse times onto the results from beam_suite.py. This is really a hack 
because I forgot to output the timings from the same script.

"""
from subprocess import PIPE, Popen, STDOUT, call
from optparse import OptionParser
import os, csv, datetime

from jazzparser.utils.config import ConfigFile

def main():
    usage = "%prog [options]"
    description = "Add timings onto the output from beam_suite.py"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    cmd_dir = os.path.abspath(os.path.join("..", ".."))
    result_eval = os.path.join(cmd_dir, "analysis", "result_eval.py")
    result_eval_dir = os.path.join(cmd_dir, "analysis")
    output_dir = os.path.join(cmd_dir, "..", "etc", "output", "pcfg", "beam")
    
    # Try all combinations of threshold and maxarc settings
    settings = [(threshold,maxarc) for threshold in [0.5, 0.1, 0.01, 0.001] \
                                   for maxarc in [5, 10, 15, 20]]
    # Don't try different thresholds for maxarc=1: they're all the same
    settings.append((0.1, 1))
    
    with open("test_suite.csv", "r") as result_file:
        result_reader = csv.reader(result_file)
        rows = list(result_reader)
    
    # Add extra column headings
    new_rows = [rows[0][:3]+["Ave time", "Std dev time"]]
    # Put in timings for each case
    for row in rows[1:]:
        threshold = row[0]
        maxarc = row[1]
        # Get the output directory for this row
        row_output_files = os.path.join(output_dir, 
                                        "%s-%s" % (threshold,maxarc),
                                        "*.res")
    
        # Get the timings from the result files
        time_proc = Popen([result_eval, row_output_files, "-tq"], 
                            cwd=result_eval_dir, stdout=PIPE)
        time_out = time_proc.stdout.read()
        ave_time, std_time = time_out.strip().split("\n")[-1].split(",")
        #~ # Parse the timings and put them in the file as seconds
        #~ # This is nasty, but has to be done because of a bug in Gnuplot
        #~ ave_time = datetime.datetime.strptime(ave_time, "%H:%M:%S.%f")
        #~ ave_time = "%d.%d" % (
                #~ (ave_time.hour*3600 + ave_time.minute*60 + ave_time.second),
                #~ ave_time.microsecond)
        #~ std_time = datetime.datetime.strptime(std_time, "%H:%M:%S.%f")
        #~ std_time = "%d.%d" % (
                #~ (std_time.hour*3600 + std_time.minute*60 + std_time.second),
                #~ std_time.microsecond)
        # Add these columns onto the row
        new_rows.append(row[:3]+[ave_time,std_time])
    
    # Open a CSV file to write the results to
    with open("test_suite.csv", "w") as result_file:
        results = csv.writer(result_file)
        results.writerows(new_rows)

if __name__ == "__main__":
    main()
