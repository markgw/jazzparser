#!/usr/bin/env ../jazzshell
import pygame
from midi import read_midifile, write_midifile
from midi.sequencer_pygame import RealtimeSequencer
from time import sleep

mid = read_midifile('../../input/midi/corpus/take_the_a_train-0.mid')

seq = RealtimeSequencer(2)
# Just play each event at regular intervals
for ev in sorted(mid.trackpool):
	seq.send_event(ev)
	sleep(0.1)

pygame.quit()
