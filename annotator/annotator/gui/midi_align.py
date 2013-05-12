import gtk
import gobject
from midi import NoteOnEvent, NoteOffEvent
from apps.sequences.models import MidiChordAlignment
from jazzparser.utils.midi import get_midi_text
from jazzparser.utils.gtk import get_text_from_dialog

global currently_playing
currently_playing = None

class MidiScore(gtk.DrawingArea):
    """
    A Gtk widget to visualize a midi stream (L{midi.EventStream}).
    
    """
    def __init__(self, stream, tick_width=0.1, track_height=10, padding=(3,3), *args, **kwargs):
        self.stream = stream
        self.tick_width = tick_width
        self.track_height = track_height
        self.track_gap = 2
        self.padding = padding
        super(MidiScore, self).__init__(*args, **kwargs)
        
        # Prepare the data for drawing
        self.num_tracks = len(stream)
        self._prepare_data()
        
        # Only display tracks that have notes in them
        self.tracks = [i for i in range(self.num_tracks) if len(self._change_times[i]) > 0]
        
        self._prepare_pixel_data()
        self._pixmap = None
        
        # Size up the widget
        width = int(tick_width * stream.duration) + 2*padding[0]
        height = int(track_height * len(self.tracks) \
                        + self.track_gap * (len(self.tracks)-1) \
                        + 2*padding[1])
        self.set_size_request(width,height)
        
        # Get ready to draw ourself when required
        self.connect("expose-event", self.expose)
        
    def _draw_pixmap(self):
        """
        Prepare a pixmap containing the visualisation of the tracks 
        that we'll draw onto the screen in expose().
        
        This is only called the first time we expose: after that we 
        just redraw the pixmap, which is much faster.
        
        """
        width, height = self.window.get_size()
        pixmap = gtk.gdk.Pixmap(self.window, width, height)
        
        # Use this graphics context for all the drawing below
        gc = self.get_style().fg_gc[gtk.STATE_NORMAL]
        # Draw a white background
        gc.set_rgb_fg_color(gtk.gdk.color_parse("white"))
        pixmap.draw_rectangle(gc, True, 0, 0, width, height)
        
        # Display each track down the widget
        for line,pixels in enumerate(self._pixels):
            starty = line * (self.track_height + self.track_gap) + self.padding[1]
            endy = starty + self.track_height
            
            for pixel in sorted(pixels.keys()):
                intensity = pixels[pixel]
                if intensity > 0.0:
                    gc.set_rgb_fg_color(gtk.gdk.color_from_hsv(hue=intensity,saturation=0.8,value=1.0))
                    pixmap.draw_line(gc, pixel, starty, pixel, endy)
        
        gc.set_rgb_fg_color(gtk.gdk.Color(0,0,0))
        self._pixmap = pixmap
        
    def expose(self, area, event):
        """
        Expose event handler. Called whenever the visible area needs 
        to be redraw.
        
        """
        if self._pixmap is None:
            # The first time we expose, draw the image
            # No need to redraw after that
            self._draw_pixmap()
        # Now just draw the pixmap onto the area
        x, y, width, height = event.area
        self.window.draw_drawable(self.get_style().fg_gc[gtk.STATE_NORMAL],
                                  self._pixmap, x, y, x, y, width, height)
        
    def _prepare_data(self):
        self._change_times = {}
        change_times_notes = {}
        for i,track in enumerate(self.stream):
            track_change_times = {}
            # Find all the points where a new note starts playing
            #  or an old one stops.
            # Between these points, the number of notes playing doesn't 
            #  change
            playing = 0
            for event in sorted(track):
                if isinstance(event, NoteOnEvent) and event.velocity > 0:
                    # New note
                    playing += 1
                    track_change_times[event.tick] = playing
                elif isinstance(event, NoteOffEvent) or \
                        isinstance(event, NoteOnEvent):
                    # Note stops playing
                    # If this is a note-on it must have velocity 0
                    playing -= 1
                    track_change_times[event.tick] = playing
            # Remove any adjacent times with the same number of notes
            to_remove = []
            last_count = 0
            for time in sorted(track_change_times.keys()):
                if track_change_times[time] == last_count:
                    to_remove.append(time)
                else:
                    last_count = track_change_times[time]
            for rem_time in to_remove:
                del track_change_times[rem_time]
                
            change_times_notes[i] = track_change_times
            
        # Transform these from notes counts to intensities
        max_notes = max(sum([ct.values() for ct in change_times_notes.values()], [])+[0])
        if max_notes != 0:
            for i in change_times_notes:
                self._change_times[i] = {}
                for time in change_times_notes[i]:
                    self._change_times[i][time] = float(change_times_notes[i][time]) / max_notes
    
    def _prepare_pixel_data(self):
        # Work out the value to put in each pixel
        # (don't want to do this every time we expose)
        self._pixels = []
        for line,track in enumerate(self.tracks):
            startx = 0
            next_notes = 0
            xvalues = {}
            for change_time in sorted(self._change_times[track].keys()):
                endx = self.midi_tick_to_x(change_time)
                for pixel in range(startx, endx+1):
                    xvalues[pixel] = max(next_notes, xvalues.get(pixel, 0))
                startx = endx
                next_notes = self._change_times[track][change_time]
            self._pixels.append(xvalues)
    
    def midi_tick_to_x(self, tick):
        """
        Returns the x coordinate corresponding to the given midi tick 
        time.
        
        """
        return int(self.tick_width * tick) + self.padding[0]
        
    def x_to_midi_tick(self, x):
        """
        Given an x coordinate, returns the midi tick displayed at this 
        coordinate. Note that will generally be very rough.
        
        """
        return max(int((float(x)-self.padding[0]) / self.tick_width), 0)
        
class MidiAlignment(gtk.VBox):
    """
    A widget for displaying chords aligned with midi data.
    
    """
    def __init__(self, midi_stream, info_buffer=None, *args, **kwargs):
        gtk.VBox.__init__(self, *args, **kwargs)
        
        self.stream = midi_stream
        self.chord_height = 100
        self.info_buffer = info_buffer
        
        # We need to put a visualisation of the midi data in here
        self.score = MidiScore(midi_stream)
        
        # Create a fixed layout for positioning the chords
        self.chord_layout = gtk.Fixed()
        
        # Add a popup menu for clicking on the score
        self.menu = gtk.Menu()
        play_item = gtk.MenuItem("Play from here")
        play_item.show()
        play_item.connect("activate", self.play_from_here)
        self.menu.append(play_item)
        midi_events_item = gtk.MenuItem("Midi events from here")
        midi_events_item.show()
        midi_events_item.connect("activate", self.midi_events_from_here)
        self.menu.append(midi_events_item)
        
        self.pack_start(self.chord_layout)
        self.pack_end(self.score)
        
        self.show_all()
        
        # Pop up the menu when the score is clicked on
        self.score.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.score.connect("button_press_event", self.show_popup)
        
        # Keep a note of where the score was last clicked on
        self.selected_pos = None
        
        self.chords = []
        
    def add_chord_alignment(self, chord_al):
        ca_wrapper = MidiAlignment.ChordAlignmentWrapper(chord_al, 
                        self.score, self.chord_height, self.info_buffer)
        # Position the frame above the score
        self.chord_layout.put(ca_wrapper.widget, *ca_wrapper.position)
        self.chords.append(ca_wrapper)
        
    def add_chord_alignments(self, chord_al_list):
        for chord_al in chord_al_list:
            self.add_chord_alignment(chord_al)
            
    def clear_chord_alignments(self):
        """
        Removes all the chord alignments from the widget.
        
        Note that this doesn't actually delete them. You'll need to 
        do that when saving the alignments.
        
        """
        for caw in self.chords:
            for el in caw.elements:
                el.destroy()
        
    def do_size_request(self, requisition):
        # Get the size that the score wants
        score_size = self.score.size_request()
        requisition.width = score_size[0]
        requisition.height = score_size[1] + self.chord_height
        
    def show_popup(self, widget, event):
        self.selected_pos = event.get_coords()[0]
        self.menu.popup(None, None, None, event.button, event.time)
        
    def play_from_here(self, *args, **kwargs):
        if self.selected_pos is not None:
            from jazzparser.utils.midi import play_stream
            global currently_playing
            # Work out what time to start at from the click position
            start_time = self.score.x_to_midi_tick(self.selected_pos)
            slc = self.score.stream.slice(start_time)
            currently_playing = play_stream(slc.to_event_stream())
            
    def midi_events_from_here(self, *args, **kwargs):
        if self.selected_pos is not None:
            start_time = self.score.x_to_midi_tick(self.selected_pos)
            window = MidiEventWindow(self.stream, start_time, limit=100)
    
    def save(self):
        """
        Saves all the chord alignments currently in the score.
        
        """
        for caw in self.chords:
            caw.chord_alignment.save()
        
    class ChordAlignmentWrapper(object):
        """
        Wrapper class to encapsulate creation of all the elements 
        relating to a chord alignment and give access to those that 
        we need later.
        
        """
        def __init__(self, chord_al, score, height, text_buffer=None):
            self.text_buffer = text_buffer
            # Work out where to put it on the x axis
            start = score.midi_tick_to_x(chord_al.start)
            width = score.midi_tick_to_x(chord_al.end) - start
            
            label = gtk.Label(str(chord_al.chord))
            alignment = gtk.Alignment(0.0,0.0,1.0,1.0)
            frame = gtk.Frame()
            frame.add(alignment)
            alignment.add(label)
            
            event_box = gtk.EventBox()
            event_box.add(frame)
            #event_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("blue"))
            
            event_box.set_size_request(width, height-10)
            
            # Prepare a popup menu
            menu = gtk.Menu()
            play_item = gtk.MenuItem(label="Play")
            play_item.show()
            play_item.connect('activate', self.play)
            menu.append(play_item)
            
            midi_display_item = gtk.MenuItem(label="Midi events")
            midi_display_item.show()
            midi_display_item.connect('activate', self.show_midi)
            menu.append(midi_display_item)
            
            label.show()
            frame.show()
            event_box.show()
            alignment.show()
            
            self.chord_alignment = chord_al
            self.widget = event_box
            self.position = (start, 0)
            self.menu = menu
            
            # For destroying everything when we need to
            self.elements = [
                label, frame, event_box, menu, play_item, 
                midi_display_item
            ]
            # Pop up a menu when the chord's clicked on
            event_box.connect("button_press_event", self.clicked)
            # Display info text when hovering over the chord
            event_box.connect("enter_notify_event", self.hover)
            
            # Prepare some text about the chord that will get displayed
            #  in the info box when we hover over the chord
            text = """\
%(chord)s
Tick range: %(start)d-%(end)d
Sequence pos: %(index)s""" % {
                'chord' : str(chord_al.chord),
                'start' : chord_al.start,
                'end' : chord_al.end,
                'index' : chord_al.chord.index,
            }
            self.info_text = text
            
        def clicked(self, widget, event):
            if event.button == 1:
                self.menu.popup(None, None, None, event.button, event.time)
                
        def play(self, *args):
            global currently_playing
            currently_playing = self.chord_alignment.play()
            
        def show_midi(self, *args):
            window = MidiEventWindow(self.chord_alignment.midi.midi_stream, 
                                     self.chord_alignment.start,
                                     self.chord_alignment.end)
                                     
        def hover(self, *args):
            if self.text_buffer is not None:
                # Set the info text to the info about this chord
                self.text_buffer.set_text(self.info_text)

gobject.type_register(MidiAlignment)

class MidiAlignmentWindow(gtk.Window):
    """
    A window for editing the alignment of chords in a chord sequence 
    with passages of a midi file. Should be instantiated with a 
    L{apps.sequences.models.MidiData}.
    
    """
    def __init__(self, midi_data, chord_alignments=None, *args, **kwargs):
        """
        If C{chord_alignments} is given, this list of alignments will 
        be used to initialize the editor, rather than those from the 
        database. If it's None, the alignments will be read from the 
        database.
        
        """
        super(MidiAlignmentWindow, self).__init__(*args, **kwargs)
        self.midi_data = midi_data
        
        if chord_alignments is None:
            chord_alignments = list(midi_data.midichordalignment_set.all())
        # Keep a note of the alignments that are here when we start
        # If these are gone when we save, we'll want to remove them
        self.last_saved_ids = set(ca.id for ca in chord_alignments)
        
        self.set_default_size(1000, 500)
        self.set_title(u"%s - Midi Alignment - Jazznotate" % self.midi_data.sequence.name)
        self.set_border_width(5)
        
        # Remember the auto-alignment parameters between runs
        self.alignment_params = None
        
        # Keep track of whether the data's been modified
        self.dirty = False
        
        vbox = gtk.VBox()
        
        name_label = gtk.Label(midi_data.name)
        name_label.set_alignment(0.0, 0.5)
        self.name_label = name_label
        vbox.pack_start(name_label, expand=False)
        
        # This will get displayed later
        # Now we need it to connect it to the chord hover events
        chord_info_buffer = gtk.TextBuffer()
        
        # Display the midi data in a special widget
        midi_score = MidiAlignment(self.midi_data.midi_stream, info_buffer=chord_info_buffer)
        midi_score.add_chord_alignments(chord_alignments)
        
        score_scroller = gtk.ScrolledWindow()
        score_scroller.add_with_viewport(midi_score)
        score_scroller.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_NEVER)
        # Put a box around the score
        score_box = gtk.Frame()
        score_box.add(score_scroller)
        vbox.pack_start(score_box, expand=False, padding=5)
        
        # The next elements are in two columns
        bottom_columns = gtk.HBox()
        column_one = gtk.VBox()
        column_two = gtk.VBox()
        bottom_columns.pack_start(column_one)
        bottom_columns.pack_start(column_two)
        vbox.pack_start(bottom_columns)
        
        ### Column 1
        self.chord_info_buffer = chord_info_buffer
        chord_info_box = gtk.TextView(chord_info_buffer)
        chord_info_box.set_editable(False)
        chord_info_scroller = gtk.ScrolledWindow()
        chord_info_scroller.add(chord_info_box)
        chord_info_frame = gtk.Frame("Chord info")
        chord_info_frame.add(chord_info_scroller)
        column_one.pack_start(chord_info_frame, expand=True)
        
        ### Column 2
        # Add a box with info about the midi file
        desc_text = get_midi_text(midi_data.midi_stream).encode('utf8')
        desc_buff = gtk.TextBuffer()
        desc_buff.set_text(desc_text)
        desc_box = gtk.TextView(desc_buff)
        desc_box.set_editable(False)
        desc_scroller = gtk.ScrolledWindow()
        desc_scroller.add(desc_box)
        desc_frame = gtk.Frame("Descriptive midi text")
        desc_frame.add(desc_scroller)
        column_two.pack_start(desc_frame, expand=True)
        
        # Add a row of buttons at the bottom
        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_END)
        
        rename_button = gtk.Button("Rename")
        rename_button.connect("clicked", self.rename)
        button_box.pack_end(rename_button, expand=False, padding=5)
        play_button = gtk.Button("Play")
        play_button.connect("clicked", self.play_from_start)
        button_box.pack_end(play_button, expand=False, padding=5)
        stop_button = gtk.Button("Stop")
        stop_button.connect("clicked", stop_playing)
        button_box.pack_end(stop_button, expand=False, padding=5)
        autoalign_button = gtk.Button("_Auto-alignment", use_underline=True)
        autoalign_button.connect("clicked", self.open_autoalign)
        button_box.pack_end(autoalign_button, expand=False, padding=5)
        save_button = gtk.Button("_Save", use_underline=True)
        save_button.connect("clicked", self.save)
        button_box.pack_end(save_button, expand=False, padding=15)
        close_button = gtk.Button("_Close", use_underline=True)
        close_button.connect("clicked", self.close_clicked)
        button_box.pack_end(close_button, expand=False, padding=5)
        
        vbox.pack_start(button_box, expand=False, padding=10)
        
        self.midi_score = midi_score
        self.add(vbox)
        self.show_all()
        
        self.connect("delete_event", self.close)
        
    def close_clicked(self, *args, **kwargs):
        if not self.close():
            self.destroy()
        
    def close(self, *args, **kwargs):
        if self.dirty:
            # Unsaved data: ask whether to save
            dialog = gtk.MessageDialog(self, 
                            flags=gtk.DIALOG_MODAL,
                            type=gtk.MESSAGE_QUESTION,
                            buttons=gtk.BUTTONS_YES_NO,
                            message_format="Save changes to the alignment?")
            answer = dialog.run()
            dialog.destroy()
            if answer == gtk.RESPONSE_NONE:
                # Cancel the close
                # Currently this can't actually happen
                return True
            elif answer == gtk.RESPONSE_YES:
                self.save()
        
    def save(self, *args, **kwargs):
        """
        Saves all the chord alignments in their current state.
        
        """
        # Only bother doing anything if the data's changed
        if self.dirty:
            self.midi_score.save()
            # Delete any alignments that were here at the beginning 
            #  and aren't any more
            remaining_ids = set(caw.chord_alignment.id for caw in self.midi_score.chords)
            removed_ids = self.last_saved_ids - remaining_ids
            for removed_id in removed_ids:
                if removed_id is not None:
                    # Delete each ChordAlignment
                    ca = MidiChordAlignment.objects.get(id=removed_id)
                    ca.delete()
            self.last_saved_ids = remaining_ids
            self.dirty = False
        
    def open_autoalign(self, *args, **kwargs):
        autoalign = AutoAlignWindow(self.midi_data, 
                                    alignment_window=self, 
                                    init_params=self.alignment_params)
                
    def update_alignments(self, alignments):
        """
        Removes all the alignments currently displaying and replaces 
        them with a new set.
        
        """
        self.dirty = True
        self.midi_score.clear_chord_alignments()
        self.midi_score.add_chord_alignments(alignments)
        
    def play_from_start(self, event):
        global currently_playing
        currently_playing = self.midi_data.play()
        
    def rename(self, *args, **kwargs):
        """
        Show a rename dialog to update the name of the midi record.
        
        """
        text = get_text_from_dialog(
                    prompt="Enter a new name:",
                    initial=self.midi_data.name,
                    title="Rename midi")
        if text is not None:
            self.midi_data.name = text
            self.midi_data.save()
            # Update the label that shows the name
            self.name_label.set_text(text)
        
class AutoAlignWindow(gtk.Window):
    """
    Window to get parameters for auto-aligning a chord sequence with 
    midi data.
    
    """
    def __init__(self, midi_data, alignment_window=None, init_params=None, *args, **kwargs):
        """
        init_params optionally initializes the values from a 
        SequenceMidiAlignmentParams.
        
        """
        super(AutoAlignWindow, self).__init__(*args, **kwargs)
        self.midi_data = midi_data
        self.alignment_window = alignment_window
        
        ####### Window furniture
        # Set up the appearance of the window
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_title(u"Auto-align - Jazznotate")
        self.set_border_width(5)
        # A box to put all the widgets in
        vbox = gtk.VBox()
        self.add(vbox)
        
        # Create the fields
        form_opts = {
            'xpadding' : 5,
            'ypadding' : 3,
            'xoptions' : gtk.FILL,
        }
        def _left(obj):
            al = gtk.Alignment(xalign=0.0)
            al.add(obj)
            return al
        form = gtk.Table(2,2,False)
        
        # Fields to add to the table
        mbpb_label = gtk.Label("Midi beats per beat")
        mbpb_field = gtk.SpinButton()
        mbpb_field.set_numeric(True)
        mbpb_field.set_range(-256, 256)
        mbpb_field.set_increments(1,4)
        mbpb_field.set_value(1)
        start_label = gtk.Label("Sequence start (midi ticks)")
        start_field = gtk.SpinButton()
        start_field.set_numeric(True)
        start_field.set_range(0, 100000)
        start_field.set_increments(1,4)
        
        # Position the fields
        form.attach(mbpb_label,         0,1, 0,1, **form_opts)
        form.attach(_left(mbpb_field),  1,2, 0,1, **form_opts)
        form.attach(start_label,        0,1, 1,2, **form_opts)
        form.attach(_left(start_field), 1,2, 1,2, **form_opts)
        
        # Keep hold of these for later
        self.mbpb_field = mbpb_field
        self.start_field = start_field
        
        # A form for putting repeat span fields in
        repeat_form = gtk.Table(1,6,False)
        repeat_label = gtk.Label("Repeat spans:")
        repeat_label.set_alignment(0.0, 0.5)
        self.repeat_form = repeat_form
        self.repeat_fields = []
        
        # A similar form for putting gap fields in
        gap_form = gtk.Table(1,6,False)
        gap_label = gtk.Label("Gaps:")
        gap_label.set_alignment(0.0, 0.5)
        self.gap_form = gap_form
        self.gap_fields = []
        
        vbox.pack_start(form, expand=False, padding=5)
        vbox.pack_start(repeat_label, expand=False, padding=10)
        vbox.pack_start(repeat_form, expand=False, padding=5)
        vbox.pack_start(gap_label, expand=False, padding=10)
        vbox.pack_start(gap_form, expand=False, padding=5)
        
        # Add a button to add a new repeat span or gap
        repeat_button_box = gtk.HButtonBox()
        repeat_button_box.set_layout(gtk.BUTTONBOX_END)
        add_repeat_button = gtk.Button("Add _repeat span", use_underline=True)
        add_repeat_button.connect("clicked", self.add_repeat_clicked)
        add_gap_button = gtk.Button("Add _gap", use_underline=True)
        add_gap_button.connect("clicked", self.add_gap_clicked)
        repeat_button_box.pack_end(add_repeat_button)
        repeat_button_box.pack_end(add_gap_button)
        vbox.pack_start(repeat_button_box)
        
        # Add buttons at the bottom
        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_END)
        
        align_button = gtk.Button("_Align", use_underline=True)
        align_button.connect("clicked", self.align)
        cancel_button = gtk.Button("_Cancel", use_underline=True)
        cancel_button.connect("clicked", self.exit)
        
        button_box.pack_end(cancel_button, expand=False, padding=5)
        button_box.pack_end(align_button, expand=False, padding=5)
        vbox.pack_end(button_box, expand=False, padding=5)
        
        # Initialize the values from an old alignment params instance
        if init_params is not None:
            self.initialize(init_params)
        
        self.show_all()
        
    def align(self, obj=None):
        """
        Perform the alignment and open up a window to show it in.
        
        Sets the parent window's C{alignment_params} attribute to 
        the parameters used as a C{SequenceMidiAlignmentParams}.
        
        """
        from apps.sequences.utils import SequenceMidiAlignmentParams
        alignment = SequenceMidiAlignmentParams()
        
        # Get values from all the fields
        alignment.midi_beats_per_beat = self.mbpb_field.get_value_as_int()
        alignment.sequence_start = self.start_field.get_value_as_int()
        for start_field, end_field, count_field in self.repeat_fields:
            start = start_field.get_value_as_int()
            end = end_field.get_value_as_int()
            count = count_field.get_value_as_int()
            # If the count is 0, ignore this span
            if count > 0:
                alignment.repeat_spans.append((start,end,count))
        for chord_field, occ_field, beats_field in self.gap_fields:
            chord = chord_field.get_value_as_int()
            occ = occ_field.get_value_as_int()
            beats = beats_field.get_value_as_int()
            # If the length is 0 beats, ignore the gap
            if beats > 0:
                alignment.gaps.append((chord,occ,beats))
        # Perform the alignment
        als = alignment.align(self.midi_data)
        
        # Update the parent window's alignments
        if self.alignment_window is not None:
            self.alignment_window.update_alignments(als)
            self.alignment_window.alignment_params = alignment
        self.exit()
        
    def initialize(self, params):
        self.mbpb_field.set_value(params.midi_beats_per_beat)
        self.start_field.set_value(params.sequence_start)
        for rs in params.repeat_spans:
            self.add_repeat_span(rs)
        for gap in params.gaps:
            self.add_gap(gap)
        
    def add_repeat_clicked(self, event):
        """Callback for "add repeat span" button. """
        self.add_repeat_span()
        
    def add_repeat_span(self, init_vals=None):
        """
        Adds the fields to the form to allow input of parameters for 
        a repeat span. Optionally initializes the values in the fields.
        
        """
        so_far = len(self.repeat_fields)
        self.repeat_form.resize(so_far+1, 6)
        
        # Create the fields
        start_label = gtk.Label("Start")
        start_field = gtk.SpinButton()
        start_field.set_numeric(True)
        start_field.set_range(0, 500)
        start_field.set_increments(1,5)
        end_label = gtk.Label("End")
        end_field = gtk.SpinButton()
        end_field.set_numeric(True)
        end_field.set_range(0, 500)
        end_field.set_increments(1,5)
        count_label = gtk.Label("Count")
        count_field = gtk.SpinButton()
        count_field.set_numeric(True)
        count_field.set_range(0, 100)
        count_field.set_increments(1,5)
        
        # Add them to the layout
        form_opts = {
            'xpadding' : 5,
            'ypadding' : 3,
            'xoptions' : gtk.FILL,
        }
        def _left(obj):
            al = gtk.Alignment(xalign=0.0)
            al.add(obj)
            return al
        self.repeat_form.attach(start_label, 0,1, so_far,so_far+1, **form_opts)
        self.repeat_form.attach(start_field, 1,2, so_far,so_far+1, **form_opts)
        self.repeat_form.attach(end_label,   2,3, so_far,so_far+1, **form_opts)
        self.repeat_form.attach(end_field,   3,4, so_far,so_far+1, **form_opts)
        self.repeat_form.attach(count_label, 4,5, so_far,so_far+1, **form_opts)
        self.repeat_form.attach(count_field, 5,6, so_far,so_far+1, **form_opts)
        
        start_label.show()
        start_field.show()
        end_label.show()
        end_field.show()
        count_label.show()
        count_field.show()
        
        self.repeat_fields.append((start_field,end_field,count_field))
        
        # Initialize the fields
        if init_vals is not None:
            if len(init_vals) != 3:
                raise ValueError, "need 3 values to initialize a repeat span"
            start,end,count = init_vals
            start_field.set_value(start)
            end_field.set_value(end)
            count_field.set_value(count)
        
        # Focus the first field we've just added
        start_field.grab_focus()
        
    def add_gap_clicked(self, event):
        """Callback for "add gap" button. """
        self.add_gap()
        
    def add_gap(self, init_vals=None):
        """
        Adds the fields to the form to allow input of parameters for 
        a gap in the chord sequence. Optionally initializes the values 
        in the fields.
        
        """
        so_far = len(self.gap_fields)
        self.gap_form.resize(so_far+1, 6)
        
        # Create the fields
        chord_label = gtk.Label("Gap after chord")
        chord_field = gtk.SpinButton()
        chord_field.set_numeric(True)
        chord_field.set_range(0, 500)
        chord_field.set_increments(1,5)
        occ_label = gtk.Label("occurrence")
        occ_field = gtk.SpinButton()
        occ_field.set_numeric(True)
        occ_field.set_range(1, 500)
        occ_field.set_increments(1,5)
        beats_label = gtk.Label("Length (beats)")
        beats_field = gtk.SpinButton()
        beats_field.set_numeric(True)
        beats_field.set_range(1, 100)
        beats_field.set_increments(1,5)
        
        # Add them to the layout
        form_opts = {
            'xpadding' : 5,
            'ypadding' : 3,
            'xoptions' : gtk.FILL,
        }
        self.gap_form.attach(chord_label, 0,1, so_far,so_far+1, **form_opts)
        self.gap_form.attach(chord_field, 1,2, so_far,so_far+1, **form_opts)
        self.gap_form.attach(occ_label,   2,3, so_far,so_far+1, **form_opts)
        self.gap_form.attach(occ_field,   3,4, so_far,so_far+1, **form_opts)
        self.gap_form.attach(beats_label, 4,5, so_far,so_far+1, **form_opts)
        self.gap_form.attach(beats_field, 5,6, so_far,so_far+1, **form_opts)
        
        chord_label.show()
        chord_field.show()
        occ_label.show()
        occ_field.show()
        beats_label.show()
        beats_field.show()
        
        self.gap_fields.append((chord_field,occ_field,beats_field))
        
        # Initialize the fields
        if init_vals is not None:
            if len(init_vals) != 3:
                raise ValueError, "need 3 values to initialize a gap"
            chord,occurrence,beats = init_vals
            chord_field.set_value(chord)
            occ_field.set_value(occurrence)
            beats_field.set_value(beats)
        
        # Focus the first field we've just added
        chord_field.grab_focus()
        
    def exit(self, obj=None):
        self.destroy()

class MidiEventWindow(gtk.Window):
    """
    Simple window to display a list of the events in a midi stream, 
    or a portion of it.
    
    """
    def __init__(self, stream, start=0, end=None, limit=None, *args, **kwargs):
        super(MidiEventWindow, self).__init__(*args, **kwargs)
        self.stream = stream
        
        if limit is not None:
            limit_text = " up to %d events" % limit
        else:
            limit_text = ""
            
        if end is None and start == 0:
            range_text = ""
        elif end is None:
            range_text = " (%d-end)" % start
        else:
            range_text = " (%d-%d)" % (start,end)
        self.set_default_size(400, 700)
        self.set_title(u"Midi Event Viewer%s%s - Jazznotate" % (range_text,limit_text))
        
        # For each track, get the events that are in the time range
        text = ""
        for tracknum,track in enumerate(stream):
            text += "Track %d:\n" % tracknum
            if end is None:
                events = [ev for ev in sorted(track) if ev.tick >= start]
            else:
                events = [ev for ev in sorted(track) if ev.tick >= start and ev.tick < end]
            if limit is not None:
                events = events[:limit]
            text += "\n".join([str(ev) for ev in events])
            text += "\n\n"
        
        # Display the text in a buffer
        buff = gtk.TextBuffer()
        buff.set_text(text)
        text_view = gtk.TextView(buff)
        
        scroller = gtk.ScrolledWindow()
        scroller.add_with_viewport(text_view)
        
        self.add(scroller)
        
        self.show_all()

def stop_playing(*args):
    """
    Stop the currently playing midi fragment.
    
    """
    global currently_playing
    if currently_playing is not None:
        # This may not be still playing, but it won't hurt to call stop
        currently_playing.stop()
        currently_playing = None
