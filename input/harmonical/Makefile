# Makefile to generate audio from the chord input files in this directory.
#
# The following targets are available:
#  cliche: Longuet-Higgins' tiny cadence tuning example
#  land: Land of Hope and Glory tuned and mistuned
#  min7: an example from CLH of a minor seventh
#  dom7: an example from CLH of a dominant seventh
#  clean: remove all generated files and temporary files
#
# Uses the harmonical's play.py script.
#
# Depends on:
#  timidity
#  oggenc (vorbis-tools)
#  lame

cliche: cliche.harm
	@echo "Generating midi"
	cd ../../bin/harmonical; ./play.py -m ../../input/harmonical/cliche.harm -o ../../input/harmonical/cliche.mid
	./render.sh cliche
	rm -f cliche.mid

land: land_of_hope.harm
	@echo "Generating midi"
	cd ../../bin/harmonical; ./play.py -m ../../input/harmonical/land_of_hope.harm -o ../../input/harmonical/land_of_hope.mid
	./render.sh land_of_hope
	rm -f land_of_hope.mid

min7: letters_sevenths1.harm
	@echo "Generating midi"
	cd ../../bin/harmonical; ./play.py -m ../../input/harmonical/letters_sevenths1.harm -o ../../input/harmonical/min7.mid
	./render.sh min7
	rm -f min7.mid

dom7: letters_sevenths2.harm
	@echo "Generating midi"
	cd ../../bin/harmonical; ./play.py -m ../../input/harmonical/letters_sevenths2.harm -o ../../input/harmonical/dom7.mid
	./render.sh dom7
	rm -f dom7.mid

clean:
	rm -f *.wav *.mp3 *.ogg
