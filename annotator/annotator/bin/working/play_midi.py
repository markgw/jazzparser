from apps.sequences.models import ChordSequence
import os.path, sys

while True:
    seqs = ChordSequence.objects.all()
    for i,seq in enumerate(seqs):
        print "%d> %s" % (i,seq.string_name)
        
    print "\nChoose a chord sequence"
    try:
        selection = raw_input(">> ")
        print
    except EOFError:
        print "Bye"
        sys.exit(0)
    
    seq_num = int(selection)
    seq = seqs[seq_num]
    
    midis = seq.mididata_set.all()
    
    def _play(midi):
        try:
            sequencer = midi.play()
        except Exception, err:
            print "Error playing midi file: ",err
            return
            
        print "Playing... (%d)" % midi.id
        try:
            raw_input("Press enter to stop")
        except:
            pass
        sequencer.stop()
    
    if len(midis) == 0:
        print "No midi files for %s" % seq.string_name
    elif len(midis) == 1:
        _play(midis[0])
    else:
        try:
            while True:
                print "Choose a midi file (0-%d)" % (len(midis)-1)
                selection = raw_input(">> ")
                
                if selection == "\n":
                    break
                try:
                    midi_num = int(selection)
                except ValueError:
                    print "Enter a number\n"
                    continue
                try:
                    _play(midis[int(selection)])
                except IndexError:
                    print "Not a valid midi file number\n"
                    continue
        except EOFError:
            print "\nReturning to song selection"
            pass
            
    try:
        raw_input("Press enter to continue")
    except:
        pass
