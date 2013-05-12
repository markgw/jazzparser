
function showNotesClicked(id) {
	div = $('omission_notes_'+id);
	toggler = $('omission_notes_toggler_'+id);
	if (div.getStyle('display') == 'none') {
		div.setStyle('display', 'block');
		toggler.set('html', 'Hide notes');
	} else {
		div.setStyle('display', 'none');
		toggler.set('html', 'Show notes');
	}
}
