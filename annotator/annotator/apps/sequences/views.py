from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
import simplejson as json
import itertools, random
from django.db.models import Count, Q

from apps.sequences.models import ChordSequence, Chord, ChordType, \
                            SkippedSequence, Song
from apps.sequences.forms import ChordSequenceForm, ChordForm, _root_choices, \
                            ChordAnnotationForm, SkippedSequenceForm, SongForm
from apps.sequences import category_pairs, pos_tags
from apps.sequences.utils import get_chord_list_from_sequence

from jazzparser.grammar import Grammar
from jazzparser import settings as jpsettings

def index(request):
    sequences = ChordSequence.objects.all().order_by('song__name')
    sequences_by_letter = [(key, list(data)) for key,data in itertools.groupby(sequences, lambda s: s.name[0])]
    context = {
        'sequences' : sequences,
        'sequences_by_letter' : sequences_by_letter,
    }
    return render_to_response('sequences/index.html', context, RequestContext(request))
    
def reannotated(request):
    sequences = ChordSequence.objects.filter(alternative=True).order_by('song__name')
    sequences_by_letter = [(key, list(data)) for key,data in itertools.groupby(sequences, lambda s: s.name[0])]
    context = {
        'heading' : 'Reannotated sequences',
        'sequences' : sequences,
        'sequences_by_letter' : sequences_by_letter,
        'hide_actions' : True,
    }
    return render_to_response('sequences/index.html', context, RequestContext(request))
    
def song_index(request):
    songs = Song.objects.all().order_by('name')
    songs_by_letter = [(key, list(data)) for key,data in itertools.groupby(songs, lambda s: s.name[0])]
    context = {
        'songs' : songs,
        'songs_by_letter' : songs_by_letter,
    }
    return render_to_response('sequences/song_index.html', context, RequestContext(request))
    
def index_with_stats(request):
    sequences = ChordSequence.objects.all().order_by('name')
    sequences_by_letter = [(key, list(data)) for key,data in itertools.groupby(sequences, lambda s: s.name[0])]
    # All sequences that haven't been annotated yet
    unannotated = ChordSequence.objects.filter(analysis_omitted=True)
    # Some helpful stats
    annotated = ChordSequence.objects.filter(analysis_omitted=False)
    num_annotated_greatly = len([s for s in annotated if s.percentage_annotated >= 80.0])
    num_annotated_little = annotated.count() - num_annotated_greatly
    context = {
        'sequences' : sequences,
        'sequences_by_letter' : sequences_by_letter,
        'unannotated' : unannotated,
        'num_annotated_greatly' : num_annotated_greatly,
        'num_annotated_little' : num_annotated_little,
    }
    return render_to_response('sequences/index_with_stats.html', context, RequestContext(request))
    
def category_use(request):
    """ Shows a summary of statistics about category use. """
    query = Chord.objects.exclude(sequence__analysis_omitted=True)
    categories = query.values('category').annotate(count=Count('id')).order_by('-count')
    total = query.count()
    
    table_data = [ {
                    'category' : data['category'] or "No category",
                    'count' : data['count'],
                    'percent' : "%.02f" % (float(data['count']) / float(total) * 100.0),
                   } for data in categories ]
    context = {
        'table_data' : table_data,
        'total' : total,
    }
    return render_to_response('sequences/category_use.html', context, RequestContext(request))
    
def notes_summary(request):
    """ Shows a summary of all the notes made against chord sequences """
    # Get all sequences that have notes stored against them
    sequences = ChordSequence.objects.exclude(notes="").order_by('name')
    context = {
        'sequences' : sequences,
    }
    return render_to_response('sequences/notes_summary.html', context, RequestContext(request))
    
def omissions_summary(request, table=False):
    """ Shows a summary of all the notes of omissions made against chord sequences """
    # Get all sequences that have notes stored against them
    sequences = ChordSequence.objects.exclude(analysis_omitted=True).exclude(omissions="").order_by('name')
    # Get separately the sequences with no analysis at all
    omitted_sequences = ChordSequence.objects.filter(analysis_omitted=True).order_by('name')
    context = {
        'omitted_sequences' : omitted_sequences,
        'sequences' : sequences,
    }
    if table:
        template = 'sequences/omissions_table.html'
    else:
        template = 'sequences/omissions_summary.html'
    return render_to_response(template, context, RequestContext(request))
    
def _save_chord_from_data(data, sequence):
    if 'id' not in data or data['id'] is None:
        chord = Chord()
    else:
        chord = Chord.objects.get(id=int(data['id']))
    chord.root = data['root']
    chord.type_id = data['type']
    if data['duration'] is None:
        duration = 4
    else:
        duration = int(data['duration'])
    chord.duration = duration
    chord.category = data['category']
    if 'additions' in data and data['additions'] is not None:
        chord.additions = data['additions']
    else:
        chord.additions = ""
    if 'bass' in data and data['bass'] is not None:
        chord.bass = data['bass']
    else:
        chord.bass = None
    chord.sequence = sequence
    chord.save()
    # And the treeinfo fields
    # These default to false
    # Only want to save them if they're true, or there's already a value
    tree = chord.treeinfo
    if 'coord_resolved' in data and data['coord_resolved']:
        tree.coord_resolved = True
        tree.save()
    elif tree.coord_resolved:
        tree.coord_resolved = False
        tree.save()
    if 'coord_unresolved' in data and data['coord_unresolved']:
        tree.coord_unresolved = True
        tree.save()
    elif tree.coord_unresolved:
        tree.coord_unresolved = False
        tree.save()
    return chord

def edit_sequence(request, id):
    if id is None:
        sequence = ChordSequence()
        song = Song()
        sequence.song = song
    else:
        sequence = get_object_or_404(ChordSequence, id=id)
        song = sequence.song
    
    if request.method == "POST":
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse(index))
        else:
            # Save the data
            form = ChordSequenceForm(instance=sequence, data=request.POST)
            song_form = SongForm(instance=song, prefix="song", data=request.POST)
            if form.is_valid():
                # See whether a song was selected
                if form.cleaned_data['song'] is not None and \
                        (sequence.song is None or
                         form.cleaned_data['song'].id != sequence.song.id):
                    # A song has been selected for a new sequence or 
                    #  the song has been changed
                    # Use the selected song
                    form.save()
                else:
                    if form.cleaned_data['song'] is None:
                        # The song was set to empty, so these details 
                        #  should be saved as a new song
                        song_form = SongForm(prefix="song", data=request.POST)
                    # We need to validate the song details
                    if song_form.is_valid():
                        saved_song = song_form.save()
                        saved_seq = form.save()
                        saved_seq.song = saved_song
                        saved_seq.save()
                # First, keep a list of all the chords that were in the sequence before
                old_chords = get_chord_list_from_sequence(sequence)
                # Handle the chord sequence data
                chord_dataset = json.loads(request.POST['chords'])
                chords = []
                for chord_data in chord_dataset:
                    chords.append(_save_chord_from_data(chord_data, sequence))
                # Now they're saved, chain the sequence together
                for i,chord in enumerate(chords):
                    if i < len(chords)-1:
                        chord.next = chords[i+1]
                    else:
                        chord.next = None
                    chord.save()
                if len(chords):
                    sequence.first_chord = chords[0]
                else:
                    sequence.first_chord = None
                sequence.save()
                # Clean up any chords that have been deleted
                new_chords = get_chord_list_from_sequence(sequence)
                for old_chord in old_chords:
                    if old_chord not in new_chords:
                        # Chord has been removed from the sequence - delete it
                        to_delete = Chord.objects.get(id=old_chord)
                        to_delete.delete()
                if 'save_and_exit' in request.POST:
                    return HttpResponseRedirect(reverse(index))
                else:
                    return HttpResponseRedirect(reverse(edit_sequence, kwargs={ 'id' : sequence.id }))
    else:
        form = ChordSequenceForm(instance=sequence)
        song_form = SongForm(prefix="song", instance=song)
        
    chord_form = ChordForm()
        
    chord_editor_options = json.dumps({
        'bars_across' : 4,
        'width' : 1000,
        'bar_length' : sequence.bar_length,
    })
    chord_data = sequence.to_json()
    
    chord_types = [( type.id, type.symbol ) for type in ChordType.objects.all()]
    
    context = {
        'sequence' : sequence,
        'form' : form,
        'song_form' : song_form,
        'chord_form' : chord_form,
        'chord_data' : chord_data,
        'chord_editor_options' : chord_editor_options,
        'chord_roots' : _root_choices,
        'chord_types' : chord_types,
        'categories' : category_pairs,
        'pos_tags' : pos_tags,
    }
    return render_to_response('sequences/edit_sequence.html', context, RequestContext(request))
    
def edit_song(request, id):
    """
    Edit song info. This is not editing a chord sequence, but only the 
    meta-info about a song. This info can also be edited while editing 
    a chord sequence.
    
    """
    if id is None:
        song = Song()
    else:
        song = get_object_or_404(Song, id=id)
        
    if request.method == "POST":
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse(song_index))
        else:
            form = SongForm(instance=song, data=request.POST)
            if form.is_valid():
                form.save()
    else:
        form = SongForm(instance=song)
        
    context = {
        'song' : song,
        'form' : form,
    }
    return render_to_response('sequences/edit_song.html', context, RequestContext(request))
    
def delete_song(request, id):
    song = get_object_or_404(Song, id=id)
    if request.method == "POST":
        if "delete" in request.POST:
            song.delete()
            return HttpResponseRedirect(reverse(index))
        else:
            return HttpResponseRedirect(reverse(edit_song, args=(id,)))
    else:
        context = {
            'song' : song,
        }
        return render_to_response('sequences/delete_song.html', context, RequestContext(request))

def view_sequences(request):
    """
    Like a sequence editor, but just displays the chord sequence. 
    Displays lots on one page. At the moment just displays all: better 
    to filter somehow.
    """
    if request.method == "GET" and 'show' in request.GET:
        show_all = True
        only_incomplete = False
        if 'incomplete_annotations' in request.GET:
            only_incomplete = True
            show_all = False
        
        # Decide which sequences to include
        sequences = ChordSequence.objects.all().order_by('name')
        if 'include_analysis_omitted' not in request.GET:
            sequences = sequences.filter(analysis_omitted=False)
        if not show_all:
            sequence_list = []
            # Check each sequence for whether we should include it
            for sequence in sequences:
                if only_incomplete:
                    # Check whether this sequence is fully annotated
                    show_sequence = False
                    for chord in sequence.iterator():
                        if chord.category == '':
                            show_sequence = True
                            break
                        if chord.category not in pos_tags:
                            show_sequence = True
                            break
                    if show_sequence:
                        sequence_list.append(sequence)
                else:
                    sequence_list.append(sequence)
            sequences = sequence_list
        
        sequence_data = []
        for sequence in sequences:
            chord_editor_options = json.dumps({
                'bars_across' : 4,
                'width' : 1000,
                'bar_length' : sequence.bar_length,
                'show_cat' : False,
                'highlight_unknown' : True,
            })
            chord_data = sequence.to_json()
            sequence_data.append((sequence, chord_data, chord_editor_options))
        
        chord_types = [( type.id, type.symbol ) for type in ChordType.objects.all()]
        
        context = {
            'sequences' : sequence_data,
            'chord_roots' : _root_choices,
            'chord_types' : chord_types,
            'categories' : category_pairs,
            'pos_tags' : pos_tags,
        }
        return render_to_response('sequences/view_sequences.html', context, RequestContext(request))
    else:
        return render_to_response('sequences/view_sequences_menu.html', {}, RequestContext(request))


def add_sequence(request):
    return edit_sequence(request, None)
    
def delete_sequence(request, id):
    sequence = get_object_or_404(ChordSequence, id=id)
    if request.method == "POST":
        if "delete" in request.POST:
            sequence.delete()
            return HttpResponseRedirect(reverse(index))
        else:
            return HttpResponseRedirect(reverse(edit_sequence, args=(id)))
    else:
        context = {
            'sequence' : sequence,
        }
        return render_to_response('sequences/delete_sequence.html', context, RequestContext(request))
        
def annotate_sequence(request, id):
    """
    Like edit_sequence, but only allows you to change the annotations,
    not the chord sequence. Supplies an automatic annotation that you 
    can choose to apply selectively to the sequence.
    """
    sequence = get_object_or_404(ChordSequence, id=id)
    raise NotImplementedError, "Don't use this for now: the JP has changed and this needs to be updated"
    #### Do the automatic tagging
    chords = list(sequence.iterator())
    # Get the default grammar
    grammar = Grammar(jpsettings.DEFAULT_GRAMMAR)
    tagger = TrigramAnnotatorChordTagger('alpha', grammar, chords)
    tagger_output = tagger.tag_input()
    
    if request.method == "POST":
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse(index))
        else:
            # Save the data
            form = ChordSequenceForm(instance=sequence, data=request.POST)
            chord_forms = [ChordAnnotationForm(chord, tag, prefix="chord%s"%chord.id, data=request.POST) for chord,tag in zip(chords,tagger_output)]
            
            # Check every chord form validates
            chords_valid = reduce(lambda so_far, chord: so_far and chord.is_valid(), chord_forms, True)
            if form.is_valid() and chords_valid:
                form.save()
                # This view can only change the annotations on a sequence
                for cf in chord_forms:
                    cf.save()
                
                if 'save_and_exit' in request.POST:
                    return HttpResponseRedirect(reverse(index))
                else:
                    return HttpResponseRedirect(reverse(annotate_sequence, kwargs={ 'id' : sequence.id }))
    else:
        form = ChordSequenceForm(instance=sequence)
        # Prepare a form for each chord
        chord_forms = [ChordAnnotationForm(chord, tag, prefix="chord%s"%chord.id) for chord,tag in zip(chords,tagger_output)]
        
    # Calculate the width the sequence needs to be
    annotator_width = sum([cf.layout_width+7 for cf in chord_forms])
    
    if len(chord_forms):
        first_field = chord_forms[0].prefix
    else:
        first_field = None
    
    context = {
        'sequence' : sequence,
        'form' : form,
        'chord_forms' : chord_forms,
        'categories' : category_pairs,
        'annotator_width' : annotator_width,
        'first_field' : first_field,
    }
    return render_to_response('sequences/annotate_sequence.html', context, RequestContext(request))
    

def skipped_sequences(request):
    sequences = SkippedSequence.objects.all().order_by('name')
    context = {
        'sequences' : sequences,
    }
    return render_to_response('sequences/skipped_index.html', context, RequestContext(request))
    
def edit_skipped_sequence(request, id):
    if id is None:
        sequence = SkippedSequence()
    else:
        sequence = get_object_or_404(SkippedSequence, id=id)
    
    if request.method == "POST":
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse(skipped_sequences))
        elif 'save_and_exit' in request.POST:
            form = SkippedSequenceForm(instance=sequence, data=request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(reverse(skipped_sequences))
    else:
        form = SkippedSequenceForm(instance=sequence)
    
    context = {
        'sequence' : sequence,
        'form' : form,
    }
    return render_to_response('sequences/skipped_sequence.html', context, RequestContext(request))

def add_skipped_sequence(request):
    return edit_skipped_sequence(request, None)
    
def delete_skipped_sequence(request, id):
    sequence = get_object_or_404(SkippedSequence, id=id)
    if request.method == "POST":
        if "delete" in request.POST:
            sequence.delete()
            return HttpResponseRedirect(reverse(skipped_sequences))
        else:
            return HttpResponseRedirect(reverse(edit_skipped_sequence, args=(id)))
    else:
        context = {
            'sequence' : sequence,
        }
        return render_to_response('sequences/delete_sequence.html', context, RequestContext(request))


def reannotate_sequence(request, id, new=False):
    """
    Takes the chords from an old sequence and allows a new version of it to 
    be created with alternative annotations.
    
    """
    sequence = get_object_or_404(ChordSequence, id=id)
    song = sequence.song
    
    if request.method == "POST":
        if 'cancel' in request.POST:
            return HttpResponseRedirect(reverse(index))
        else:
            # Check there's the same number of chords
            # We will ignore any changes to the chords themselves
            chord_dataset = json.loads(request.POST['chords'])
            if len(sequence) != len(chord_dataset):
                raise ValidationError, "You can't edit the chord sequence "\
                    "through this page"
            # Update the annotations from the form data
            chords = []
            for chord_data,chord in zip(chord_dataset, sequence.iterator()):
                chord.category = chord_data['category']
                chord.save()
                # And the treeinfo fields
                tree = chord.treeinfo
                if 'coord_resolved' in chord_data and chord_data['coord_resolved']:
                    tree.coord_resolved = True
                    tree.save()
                elif tree.coord_resolved:
                    tree.coord_resolved = False
                    tree.save()
                if 'coord_unresolved' in chord_data and chord_data['coord_unresolved']:
                    tree.coord_unresolved = True
                    tree.save()
                elif tree.coord_unresolved:
                    tree.coord_unresolved = False
                    tree.save()
                chords.append(chord)
            
            if 'save_and_exit' in request.POST:
                return HttpResponseRedirect(reverse(index))
            else:
                return HttpResponseRedirect(reverse('reannotate', 
                                            args=(sequence.id,)))
    else:
        form = ChordSequenceForm(instance=sequence)
        
    if new:
        chords = list(sequence.iterator())
        # Create a copy of this sequence
        sequence.id = None
        # Clear notes and omissions, so we don't give any clues to bias
        sequence.notes = ''
        sequence.omissions = ''
        sequence.save()
        
        # Copy each chord
        # Clear annotations to start afresh
        for chord in chords:
            chord.id = None
            chord.sequence = sequence
            chord.category = ''
            chord.save()
        
        # Chain together these chords
        previous_chord = chords[0]
        for chord in chords[1:]:
            previous_chord.next = chord
            previous_chord.save()
            previous_chord = chord
        chords[-1].next = None
        chords[-1].save()
        
        sequence.first_chord = chords[0]
        # Mark this as an alternative annotation
        sequence.alternative = True
        sequence.save()
        # Go to the editor page for this new sequence
        return HttpResponseRedirect(reverse('reannotate', args=(sequence.id,)))
    
    chord_form = ChordForm(readonly=True)
        
    chord_editor_options = json.dumps({
        'bars_across' : 4,
        'width' : 1000,
        'bar_length' : sequence.bar_length,
        'vertical_offset' : 280,
    })
    
    chord_data = sequence.to_json()
    
    chord_types = [( type.id, type.symbol ) for type in ChordType.objects.all()]
    
    context = {
        'sequence' : sequence,
        'form' : form,
        'song_form' : None,
        'chord_form' : chord_form,
        'chord_data' : chord_data,
        'chord_editor_options' : chord_editor_options,
        'chord_roots' : _root_choices,
        'chord_types' : chord_types,
        'categories' : category_pairs,
        'pos_tags' : pos_tags,
        'hidenotes' : True,
    }
    return render_to_response('sequences/reannotate_sequence.html', context, RequestContext(request))
    
def random_reannotate(request):
    """
    Select a sequence at random to reannotate. Checks whether an alternative 
    annotation already exists.
    
    """
    # Choose only from songs with no alternative chord sequence (annotations)
    songs = Song.objects.exclude(chordsequence__alternative=True)
    # Ignore unannotated songs
    songs = songs.exclude(chordsequence__analysis_omitted=True)
    # Choose songs until we find one that's fully annotated
    acceptable = False
    while not acceptable:
        rand_song = random.choice(songs)
        # Check all chords have annotations
        if rand_song.chordsequence_set.all()[0].fully_annotated and \
                all(not seq.alternative for seq in rand_song.chordsequence_set.all()):
            acceptable = True
    # Clone the first (probably only) chord sequence for reannotation
    sequence = rand_song.chordsequence_set.all()[0]
    return HttpResponseRedirect(reverse('start-reannotate', args=(sequence.id,)))
