#!/bin/bash
# Script to render a midi file using Timidity and convert the result to 
#  ogg and mp3.
# You probably don't want to use this directly. It's used by the makefile 
#  in this directory. Use make to build audio from a particular harm file.
#
# First arg is filename (without extension) of the midi file.
basename=$1

# Use Timiditiy to synthesize the midi file
echo "Rendering $basename.mid"
timidity -Ow -o $basename.wav $basename.mid
# Convert to ogg using oggenc and mp3 using lame
echo "Converting to Ogg"
oggenc $basename.wav
echo "Converting to Mp3"
lame $basename.wav $basename.mp3
# Get rid of the wav file now that we've encoded it
rm $basename.wav
echo "Output in $basename.ogg and $basename.mp3"
