from django.db import models
import simplejson as json

from apps.sequences.utils import get_chord_list_from_sequence

from jazzparser.utils.chords import int_to_chord_numeral
from jazzparser.utils.base import ExecutionTimer

class ChordType(models.Model):
    """ These should all be set up in a fixture. M7, m7, etc. """
    symbol = models.CharField(max_length=10, blank=True, null=True)
    order = models.IntegerField()
    
    def __unicode__(self):
        return unicode(self.symbol)

class Source(models.Model):
    """ Where a chord sequence comes from. """
    name = models.CharField(max_length=30)
    
    def __unicode__(self):
        return unicode(self.name)
    
class Chord(models.Model):
    """ An individual chord in a sequence. """
    root = models.IntegerField()
    type = models.ForeignKey(ChordType)
    additions = models.CharField(max_length=15, blank=True, null=True)
    bass = models.IntegerField(blank=True, null=True)
    next = models.ForeignKey('Chord', blank=True, null=True)
    duration = models.IntegerField()
    category = models.CharField(max_length=20, blank=True, null=True)
    sequence = models.ForeignKey('ChordSequence', blank=True, null=True)
    
    def to_list(self):
        if self.next is None:
            tail = []
        else:
            tail = self.next.to_list()
        tail.append({
            'id': self.id,
            'root': self.root,
            'type': self.type.id,
            'duration': self.duration,
            'category': self.category,
            'additions': self.additions,
            'bass': self.bass,
            'coord_unresolved' : self.treeinfo.coord_unresolved,
            'coord_resolved' : self.treeinfo.coord_resolved,
        })
        return tail
        
    def __unicode__(self):
        return unicode('%s%s' % (int_to_chord_numeral(self.root), self.type))
        
    def __str__(self):
        return str(unicode(self))
        
    def _get_jp_input(self):
        """ A string format suitable for input to the Jazz Parser. """
        return "%s%s" % (int_to_chord_numeral(self.root), self.type.symbol)
    jazz_parser_input = property(_get_jp_input)
    
    def get_chord_mirror(self, sequence=None):
        """
        Produces a mirror of just this chord (no successors).
        The sequence argument should be a mirror of the sequence (we 
        don't want to create a new mirror for every chord).
        """
        from jazzparser.data.db_mirrors import Chord as ChordMirror
        ti = self.treeinfo.get_mirror()
        return ChordMirror(
            root=self.root, type=self.type.symbol, additions=self.additions,
            bass=self.bass, next=None, duration=self.duration, 
            category=self.category, sequence=sequence, treeinfo=ti)
    
    def get_mirror(self, sequence=None):
        """
        Produces a mirror of this chord and all its successors.
        The sequence argument should be a mirror of the sequence (we 
        don't want to create a new mirror for every chord).
        """
        chord = self.get_chord_mirror(sequence)
        if self.next is not None:
            chord.next = self.next.get_mirror(sequence)
        return chord
        
    def _get_treeinfo(self):
        try:
            return self._treeinfo
        except TreeInfo.DoesNotExist:
            new_info = TreeInfo()
            new_info.chord = self
            return new_info
    treeinfo = property(_get_treeinfo)
    
    @property
    def index(self):
        """
        The index of the chord within its sequence.
        """
        if not hasattr(self, "__index"):
            self.__index = list(self.sequence.iterator()).index(self)
        return self.__index
    
class Song(models.Model):
    """
    Represents a single song. Note that a song may have more than 
    one chord sequence associated with it.
    
    """
    name = models.CharField(max_length=50)
    key = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True, help_text="General notes about the song")
    
    def __unicode__(self):
        return self.name
        
    def _get_string_name(self):
        return self.name.encode('ascii', 'replace')
    string_name = property(_get_string_name)

class ChordSequence(models.Model):
    """
    A chord sequence for a song.
    
    """
    song = models.ForeignKey(Song, null=True)
    description = models.CharField(max_length=256, blank=True, null=True, help_text="Descriptive text specific to this chord sequence, distinguishing it from others for the same song.")
    bar_length = models.IntegerField()
    first_chord = models.ForeignKey(Chord, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    analysis_omitted = models.BooleanField(help_text="The analysis has been left out entirely, because the sequence doesn't suit this kind of analysis or I have no idea how to do it.")
    omissions = models.TextField(blank=True, null=True, help_text="A simple list of the gaps in the analyis")
    source = models.ForeignKey(Source, null=True, help_text="Where the sequence came from")
    alternative = models.BooleanField(help_text="This is an alternative annotation of the chord sequence. It will not be included in the default exported data set, unless requested for consistency testing")
    
    def to_json(self):
        if self.first_chord is not None:
            chord_data = list(reversed(self.first_chord.to_list()))
        else:
            chord_data = {}
        return json.dumps(chord_data)
        
    def __unicode__(self):
        return unicode(self.name)
        
    @property
    def string_name(self):
        return self.song.string_name
        
    @property
    def sequence_distinguisher(self):
        """
        A string that can be used to distinguish this sequence from others
        for the same song, e.g. in interface lists.
        
        """
        if self.description:
            return str(self.description.encode('ascii','replace'))
        else:
            return "%s (%d)" % (self.string_name, self.id)
    
    def delete(self):
        # First delete all the chords
        chords = list(self.iterator())
        for chord in chords:
            chord.delete()
        super(ChordSequence, self).delete()
        
    def iterator(self):
        chord = self.first_chord
        while chord is not None:
            yield chord
            chord = chord.next
            
    def _get_number_annotated(self):
        total = 0
        annotated = 0
        for chord in self.iterator():
            if chord.category is not None and chord.category != "":
                annotated += 1
            total += 1
        return (annotated, total)
    number_annotated = property(_get_number_annotated)
    
    def _get_percentage_annotated(self):
        annotated, total = self.number_annotated
        return 100.0 * float(annotated) / float(total)
    percentage_annotated = property(_get_percentage_annotated)
    
    def _get_fully_annotated(self):
        """
        True if every chord in the sequence is annotated. This should 
        usually be a bit quicker than checking percentage_annotated.
        """
        for chord in self.iterator():
            if chord.category is None or chord.category == "":
                return False
        return True
    fully_annotated = property(_get_fully_annotated)
    
    def _get_length(self):
        return len(list(self.iterator()))
    length = property(_get_length)
    __len__ = _get_length
    
    def get_mirror(self):
        """
        Produces a non-database mirror of the chord sequence, including 
        all its chords.
        """
        from jazzparser.data.db_mirrors import ChordSequence as ChordSequenceMirror
        sequence = ChordSequenceMirror(
            name=self.name, key=self.key, bar_length=self.bar_length, 
            first_chord=None, notes=self.notes, 
            analysis_omitted=self.analysis_omitted, omissions=self.omissions,
            source=self.source.name, id=self.id)
        # Mirror all the chords too
        if self.first_chord is not None:
            chord = self.first_chord.get_mirror(sequence)
        sequence.first_chord = chord
        return sequence
    mirror = property(get_mirror)
    
    """
    The following properties provide direct access to the fields of 
    the related song and maintain backwards compatibility (for reading 
    only) from when these were stored on the ChordSequence model.
    """
    def _get_name(self):
        return self.song.name
    name = property(_get_name)
    
    def _get_key(self):
        return self.song.key
    key = property(_get_key)
    
class TreeInfo(models.Model):
    """
    Associates information with a chord that is relevant to building 
    syntactic trees. This stores all information that is not implicit
    in the lexical categories (e.g. where coordinations occur).
    
    """
    chord = models.OneToOneField(Chord, related_name="_treeinfo")
    coord_unresolved = models.BooleanField(help_text="Mark this as the "\
        "final chord of the first part of a coordinated cadence")
    coord_resolved = models.BooleanField(help_text="Marks this as the "\
        "final chord before the common resolution of a coordination")
        
    def get_mirror(self):
        from jazzparser.data.db_mirrors import TreeInfo as TreeInfoMirror
        return TreeInfoMirror(
                coord_resolved=self.coord_resolved,
                coord_unresolved=self.coord_unresolved)
    mirror = property(get_mirror)
            
class SkippedSequence(models.Model):
    """ Just a note of a sequence that I've not bothered to input 
    (usually because it's out of domain). """
    name = models.CharField(max_length=20)
    reason = models.TextField(null=True, blank=True, help_text="Reason for not annotating.", default="Out of domain")

class MidiData(models.Model):
    """
    Associates midi data with a chord sequence.
    
    This doesn't include any alignment information, just the midi 
    file itself.
    
    """
    midi_file = models.FileField(upload_to="midi")
    sequence = models.ForeignKey(ChordSequence, null=False)
    name = models.CharField(max_length=200, blank=True, help_text="Descriptive text to distinguish this midi file from others for the same sequence")
    
    @property
    def midi_stream(self):
        """
        A midi event stream containing the midi events stored 
        in this midi data.
        """
        if not hasattr(self, "__midi_stream"):
            from midi import read_midifile
            from cStringIO import StringIO
            f = self.midi_file.file
            f.seek(0)
            data = f.read()
            self.__midi_stream = read_midifile(StringIO(data))
        return self.__midi_stream
    
    def play(self):
        from jazzparser.utils.midi import play_stream
        return play_stream(self.midi_stream)

class MidiChordAlignment(models.Model):
    """
    Aligns a chord from a chord sequence with a particular segment of 
    a midi file.
    
    """
    midi = models.ForeignKey(MidiData, null=False)
    chord = models.ForeignKey(Chord, null=False)
    start = models.IntegerField(help_text="Start time in midi ticks")
    end = models.IntegerField(help_text="End time in midi ticks")
    
    def play(self):
        from midi.slice import EventStreamSlice
        from jazzparser.utils.midi import play_stream
        
        slc = EventStreamSlice(self.midi.midi_stream, self.start, self.end)
        strm = slc.to_event_stream()
        return play_stream(strm)
