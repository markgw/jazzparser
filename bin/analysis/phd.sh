#!/bin/bash
# Output all the results that are going in my PhD thesis
# This doesn't run the experiments, just computes the evaluation results 
#  using different metrics from the parse results files

echo "###################################"
echo "# PhD thesis experimental results #"
echo "###################################"
echo
echo ">>>>>>>>> Chord parsing <<<<<<<<<<<"
echo "*** HmmPath (TSED) ***"
./result_eval.py -m tsed -f ../../etc/output/backoff/ngram/bigram/*.res
echo 
echo
echo "*** PCCG (TSED) ***"
./result_eval.py -m tsed -f ../../etc/output/pcfg/chords/no_st/*.res
echo 
echo "Stratified shuffling for significance of difference between PCCG and HmmPath"
./stratshuff.py -m tsed ../../etc/output/backoff/ngram/bigram/ ../../etc/output/pcfg/chords/no_st/ -i 100000
echo
echo
echo "*** St+PCCG (TSED) ***"
./result_eval.py -m tsed -f ../../etc/output/pcfg/chords/bigram/*.res
echo 
echo "Stratified shuffling for significance of difference between St+PCCG and HmmPath"
./stratshuff.py -m tsed ../../etc/output/backoff/ngram/bigram/ ../../etc/output/pcfg/chords/bigram/ -i 100000
echo 
echo
echo "Stratified shuffling for significance of difference between St+PCCG and PCCG"
./stratshuff.py -m tsed ../../etc/output/pcfg/chords/no_st/ ../../etc/output/pcfg/chords/bigram/ -i 100000
echo
echo
echo "*** PCCG (DR) ***"
./result_eval.py -m deprec -f ../../etc/output/pcfg/chords/no_st/*.res
echo 
echo
echo "*** St+PCCG (DR) ***"
./result_eval.py -m deprec -f ../../etc/output/pcfg/chords/bigram/*.res
echo 
echo
echo "Stratified shuffling for significance of difference between St+PCCG and PCCG"
./stratshuff.py -m deprec ../../etc/output/pcfg/chords/no_st/ ../../etc/output/pcfg/chords/bigram/ -i 100000
echo

echo "Evaluate chord parsing results with ODR? [y/N]"
read item
case "$item" in
 y|Y)     
    echo "*** PCCG (ODR, for comparison) ***"
    ./result_eval.py -m optdeprec -f ../../etc/output/pcfg/chords/no_st/*.res
    echo
    echo "*** St+PCCG (ODR, for comparison) ***"
    ./result_eval.py -m optdeprec -f ../../etc/output/pcfg/chords/bigram/*.res
    echo
    ;;
esac

echo
echo ">>>>>>>>> MIDI parsing <<<<<<<<<<<"
echo "*** HmmPath, pipeline (TSED) ***"
./result_eval.py -m tsed -f ../../etc/output/backoff/midingram/triad/bigram/pipeline/*.res
echo 
echo "*** HmmPath, lattice (TSED) ***"
./result_eval.py -m tsed -f ../../etc/output/backoff/midingram/triad/bigram/lattice/*.res
echo
echo "*** Cr+St+PCCG, pipeline (TSED) ***"
./result_eval.py -m tsed -f ../../etc/output/chordlabel/heads/triad/pipeline/*.res
echo 
echo "Stratified shuffling for significance of difference between Cr+St+PCCG (pipeline) and HmmPath (pipeline)"
./stratshuff.py -m tsed ../../etc/output/backoff/midingram/triad/bigram/pipeline/ ../../etc/output/chordlabel/heads/triad/pipeline/ -i 100000
echo 
echo
echo "*** Cr+St+PCCG, lattice (TSED) ***"
./result_eval.py -m tsed -f ../../etc/output/chordlabel/heads/triad/lattice/*.res
echo 
echo "Stratified shuffling for significance of difference between Cr+St+PCCG (lattice) and HmmPath (pipeline)"
./stratshuff.py -m tsed ../../etc/output/backoff/midingram/triad/bigram/pipeline/ ../../etc/output/chordlabel/heads/triad/lattice/ -i 100000
echo 
echo "Stratified shuffling for significance of difference between Cr+St+PCCG (lattice) and Cr+St+PCCG (pipeline)"
./stratshuff.py -m tsed ../../etc/output/chordlabel/heads/triad/pipeline/ ../../etc/output/chordlabel/heads/triad/lattice/ -i 100000
echo 
echo

echo "Evaluate midi parsing results with ODR? [y/N]"
read item
case "$item" in
 y|Y)     
    echo "*** Cr+St+PCCG, pipeline (ODR) ***"
    ./result_eval.py -m optdeprec -f ../../etc/output/chordlabel/heads/triad/pipeline/*.res
    echo 
    echo "*** Cr+St+PCCG, lattice (ODR) ***"
    ./result_eval.py -m optdeprec -f ../../etc/output/chordlabel/heads/triad/lattice/*.res
    echo 
    echo "Stratified shuffling for significance of difference between Cr+St+PCCG (lattice) and Cr+St+PCCG (pipeline) by ODR"
    ./stratshuff.py -m optdeprec ../../etc/output/chordlabel/heads/triad/pipeline/ ../../etc/output/chordlabel/heads/triad/lattice/ -i 100000
    echo 
    ;;
esac
