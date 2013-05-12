from django.forms import ModelForm
import django.forms as forms

from apps.sequences.models import ChordSequence, Chord, ChordType, \
                    SkippedSequence, Song
from apps.sequences import category_pairs

_root_choices = {
    0: "I",
    1: "bII",
    2: "II",
    3: "bIII",
    4: "III",
    5: "IV",
    6: "bV",
    7: "V",
    8: "bVI",
    9: "VI",
    10: "bVII",
    11: "VII",
}.items()

class SongForm(ModelForm):
    class Meta:
        model = Song

class ChordSequenceForm(ModelForm):
    song = forms.ModelChoiceField(queryset=Song.objects.all(), required=False)
    
    class Meta:
        model = ChordSequence
        
    def __init__(self, *args, **kwargs):
        super(ChordSequenceForm, self).__init__(*args, **kwargs)
        self.fields['first_chord'].widget = forms.widgets.HiddenInput()

class ChordForm(ModelForm):
    root = forms.ChoiceField(choices=_root_choices)
    type = forms.ModelChoiceField(queryset=ChordType.objects.all().order_by('order'), empty_label=None)
    bass = forms.ChoiceField(choices=[('','')]+_root_choices)
    coord_resolved = forms.BooleanField()
    coord_unresolved = forms.BooleanField()
    
    class Meta:
        model = Chord
        
    def __init__(self, *args, **kwargs):
        readonly = kwargs.pop("readonly", False)
        super(ChordForm, self).__init__(*args, **kwargs)
        self.fields['category'] = forms.ChoiceField(choices=[('','')]+category_pairs, required=False)
        
        # Make the fields read only
        if readonly:
            for field in ['root', 'type', 'bass', 'duration', 'additions']:
                self.fields[field].widget.attrs['readonly'] = True

class ChordAnnotationForm(forms.Form):
    MIN_LAYOUT_WIDTH = 100
    PIXELS_PER_BEAT = 70
    
    category = forms.ChoiceField()
    
    def __init__(self, chord, auto_tag, suggestion_initial=True, *args, **kwargs):
        self.chord = chord
        self.auto_tag = auto_tag
        if not suggestion_initial or auto_tag == chord.category:
            # If the suggestion is the same as the old tag, make 'previous' the default choice - it feels better
            initial = {'category':'previous'}
        else:
            initial = {'category':'auto'}
        super(ChordAnnotationForm, self).__init__(*args, initial=initial, **kwargs)
        self.fields['category'] = forms.ChoiceField(choices=[('auto','Suggested tag'),('previous','Old tag (%s)'%chord.category),('','')]+sorted(category_pairs), required=False)
        
    def save(self, *args, **kwargs):
        tag = self.cleaned_data['category']
        # If they selected previous, don't change the tag
        if tag != 'previous':
            if tag == 'auto':
                # They want the automatically annotated tag
                tag = self.auto_tag
            self.chord.category = tag
            # Save the chord with this category
            self.chord.save()
            
    def _get_layout_width(self):
        """
        The number of pixels to use for the layout of this chord form.
        """
        return max(ChordAnnotationForm.MIN_LAYOUT_WIDTH, self.chord.duration * ChordAnnotationForm.PIXELS_PER_BEAT)
    layout_width = property(_get_layout_width)
    
class SkippedSequenceForm(forms.ModelForm):
    class Meta:
        model = SkippedSequence
