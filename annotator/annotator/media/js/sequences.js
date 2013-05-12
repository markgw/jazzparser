function selectOptionByValue(selectId, value) {
	var opts = $(selectId).options;
	var found = false;
	for (var i=0; i<opts.length; i++) {
		if (!found && opts[i].value == value) {
			opts[i].selected = true;
			found = true;
		} else {
			opts[i].selected = false;
		}
	}
	if (!found) opts[0].selected = true;
}

function trim(stringToTrim) {
	return stringToTrim.replace(/^\s+|\s+$/g,"");
}
function ltrim(stringToTrim) {
	return stringToTrim.replace(/^\s+/,"");
}
function rtrim(stringToTrim) {
	return stringToTrim.replace(/\s+$/,"");
}


function clone_chord(chord) {
	var newChord = {};
	for (var key in chord) {
		newChord[key] = chord[key];
	}
	newChord['id'] = undefined;
	return newChord;
}

function findKey(dict, value) {
	for (var key in dict) {
		if (dict[key] == value)
			return key;
	}
}

function chordToText(chord) {
	var text = "";
	text += window.chordRoots[chord['root']];
	text += window.chordTypes[chord['type']];
	if (chord['additions'] != undefined && chord['additions'] != "") {
		text += "("+chord['additions']+")";
	}
	if (chord['bass'] != undefined && chord['bass'] != "") {
		text += "/"+window.chordRoots[chord['bass']];
	}
	text += "-"+ chord['duration'];
	if (chord['category'] != undefined && chord['category'] != "") {
		text += "["+chord['category']+"]";
	}
	return text
}

function textToChord(text) {
	var chord = {};
	// Remove anything after a - - this is the duration
	var textParts = text.split("-");
	var durationText = "4";
	if (textParts.length > 1)
		durationText = textParts[1];
	text = textParts[0];
	// Remove anything after a [ - this is the category
	var textParts = durationText.split("[");
	durationText = textParts[0];
	var categoryText = "";
	if (textParts.length > 1) {
		categoryText = textParts[1]
		categoryText = categoryText.substr(0, categoryText.length-1);
	}
	chord['category'] = categoryText;
	chord['duration'] = parseInt(durationText);
	// Get the root out
	var rootRe = /^(b|#)*[XIV]+/;
	var root = rootRe.exec(text)[0];
	text = text.substr(root.length);
	chord['root'] = findKey(window.chordRoots, root);
	// Figure out the chord type
	// First remove any bass from the end
	var bassRe = /\/(.*)$/;
	if (text.match(bassRe)) {
		var bassText = bassRe.exec(text)[0].substr(1);
		chord['bass'] = findKey(window.chordRoots, bassText);
		text = text.substr(0, text.length-bassText.length-1)
	}
	// Next remove any additions
	var additionsRe = /\((.+?)\)$/;
	if (text.match(additionsRe)) {
		var additionsText = additionsRe.exec(text)[0];
		chord['additions'] = additionsText.substr(1, additionsText.length-2);
		text = text.substr(0, text.length-chord['additions'].length-2);
	} else
		chord['additions'] = ""
	// What's left must be the chord type
	chord['type'] = findKey(window.chordTypes, text);
	return chord
}


var ChordEditor = new Class({
	initialize : function(id, options) {
		this.id = id;
		this.options = options;
		this.input = id + "_data";
		this.chordChartId = id + "_chords";
		this.colourCycle = ['#C7E0C5','#C6D8E0'];
		this.editingChord = null;
		this.chordPositions = [];
		this.endPos = [0,0];
		this.newChordAfter = undefined;
		this.lineHeight = 66;
		this.verticalOffset = 395;
		this.horizontalOffset = 20;
		
		if (options['vertical_offset'] != undefined)
			this.verticalOffset = options['vertical_offset'];
		
		if (options['bar_length'] != undefined)
			this.barLength = options['bar_length'];
		else
			this.barLength = 4;
		
		this.calculateWidth(options);
		
		// Define actions
		$('editor_box_close').addEvent('click', (function() {
			this.hideEditor();
			return false;
		}).bind(this));
		$('chord_editor_form').addEvent('submit', (function(e) {
			e.stop();
			var currentChord = this.editingChord;
			// Write the data back to the hidden field
			this.updateFromEditor();
			// Redraw
			this.drawChords();
			// Move onto the next chord
			if (currentChord == undefined)
				// Add a new chord at the end
				this.editNewChordAfter(this.data.length-1);
			else
				this.editChord(currentChord+1);
			// Focus the first field
			$('id_root').focus();
		}).bind(this));
		$('edit_as_text_button').addEvent('click', (function() {
			this.showTextEditor();
			return false;
		}).bind(this));
		$('id_cancel_text_chords').addEvent('click', (function(e) {
			e.stopPropagation();
			this.hideTextEditor();
			return false;
		}).bind(this));
		$('id_submit_text_chords').addEvent('click', (function(e) {
			e.stopPropagation();
			this.submitTextEditor();
			return false;
		}).bind(this));
		
		this.drawChords();
		this.editChord();
	},
	
	calculateWidth : function(options) {
		this.beatsAcross = this.barLength * options['bars_across'];
		if (this.beatsAcross == 0)
			this.beatsAcross = 12;
		this.beatWidth = options['width'] / this.beatsAcross;
	},
	
	recalculateWidth : function(options) {
		this.calculateWidth(options);
		this.drawChords();
		this.editChord();
	},
	
	deleteChord : function(chordNumber) {
		this.data.splice(chordNumber, 1);
		this.writeData();
		this.drawChords();
	},
	
	readData : function() {
		this.data = JSON.decode($(this.input).value);
		if (this.data.length == undefined) {
			this.data = [];
		}
	},
	writeData : function() {
		$(this.input).value = JSON.encode(this.data);
	},
	
	updateFromEditor : function() {
		// Get the data from the editor box and update the chord chart
		// First check whether we're copying chords
		if ($('id_copy_start').value != "" && $('id_copy_end').value != "") {
			var start = parseInt($('id_copy_start').value);
			var end = parseInt($('id_copy_end').value);
			this.copyChords(start, end, this.newChordAfter);
			this.writeData();
			this.drawChords();
		} else {
			// Read the data from the form
			if (this.editingChord == undefined) {
				if (this.newChordAfter == undefined) {
					// First chord
					this.data.push({});
					this.editingChord = 0;
				} else {
					// Insert a new chord
					this.data.splice(this.newChordAfter+1, 0, {});
					this.editingChord = this.newChordAfter+1
				}
			}
			var chordData = this.data[this.editingChord];
			chordData['root'] = $('id_root').value;
			chordData['type'] = $('id_type').value;
			chordData['duration'] = parseInt($('id_duration').value);
			chordData['category'] = $('id_category').value;
			chordData['additions'] = $('id_additions').value;
			chordData['bass'] = parseInt($('id_bass').value);
			chordData['coord_resolved'] = $('id_coord_resolved').checked;
			chordData['coord_unresolved'] = $('id_coord_unresolved').checked;
		}
		// Store the data to the hidden field
		this.writeData();
	},
	
	editNewChordAfter : function(chordNumber) {
		var pos;
		if (chordNumber >= this.data.length-1) {
			// If we're putting it after the end chord, use the end position
			pos = this.endPos;
		} else {
			// Otherwise use the start of the next chord
			pos = this.chordPositions[chordNumber + 1];
		}
		pos = [ pos[0]*this.beatWidth - 37 + this.horizontalOffset, pos[1]*this.lineHeight + this.verticalOffset ]
		this.editingChord = undefined;
		this.newChordAfter = chordNumber;
		this.showEditBox(pos);
	},
	
	editChord : function(chordNumber) {
		this.hideEditor();
		// Find the chord we're editing
		if (chordNumber == undefined) {
			if (this.data.length == 0) {
				// No chords yet - add a new one at the beginning
				this.editingChord = undefined;
			} else {
				// Edit the first chord
				this.editingChord = 0;
			}
		} else {
			if (chordNumber >= this.data.length) {
				// Beyond the end: add a new chord
				return this.editNewChordAfter(this.data.length-1);
			} else {
				this.editingChord = chordNumber;
			}
		}
		var pos;
		if (undefined == this.editingChord) {
			pos = this.endPos;
		} else {
			pos = this.chordPositions[this.editingChord];
		}
		pos = [ pos[0]*this.beatWidth + this.horizontalOffset, pos[1]*this.lineHeight + this.verticalOffset ]
		// Not adding a new chord
		this.newChordAfter = undefined;
		this.showEditBox(pos);
	},
	
	showEditBox : function(position) {
		// Position the editor box by the chord we're editing
		$('editor_box').setStyles({
			'top' : position[1],
			'left' : position[0]
		});
		if (this.editingChord == undefined) {
			selectOptionByValue('id_root', null);
			selectOptionByValue('id_type', null);
			$('id_duration').value = this.barLength;
			selectOptionByValue('id_category', null);
			$('id_additions').value = "";
			selectOptionByValue('id_bass', null);
		} else {
			// Put the correct values in the form
			var chordData = this.data[this.editingChord];
			selectOptionByValue('id_root', chordData['root']);
			selectOptionByValue('id_type', chordData['type'])
			$('id_duration').value = chordData['duration'];
			selectOptionByValue('id_category', chordData['category']);
			$('id_additions').value = chordData['additions'];
			selectOptionByValue('id_bass', chordData['bass']);
			$('id_coord_resolved').checked = chordData['coord_resolved'];
			$('id_coord_unresolved').checked = chordData['coord_unresolved'];
		}
		// Show the chord number
		if (this.editingChord == undefined) {
			// Put a chord copying widget instead of the chord number
			$('editor_chord_number').setStyle('display', "none");
			$('editor_chord_copier').setStyle('display', "");
		} else {
			$('editor_chord_number').set('html', this.editingChord);
			$('editor_chord_number').setStyle('display', "");
			$('editor_chord_copier').setStyle('display', "none");
			// Set some hover information on the chord number
			$('editor_chord_number').removeEvents('mouseover');
			$('editor_chord_number').removeEvents('mousemove');
			// You can put any other information about the chord in here
			this.addHover($('editor_chord_number'), '<strong>More chord info</strong><br/>ID: '+chordData['id']);
		}
		// Clear copy chords fields
		$('id_copy_start').value = "";
		$('id_copy_end').value = "";
		// Display the editor box
		$('editor_box').setStyles({
			'display': ''
		});
		$('id_root').focus();
	},
	
	hideEditor : function() {
		$('editor_box').setStyles({
			'display': 'none'
		});
	},
	
	copyChords : function(start, end, destination) {
		var newChords = [];
		for (var i=start; i<=end; i++) {
			newChords.push(clone_chord(this.data[i]));
		}
		for (var i=0; i<newChords.length; i++) {
			this.data.splice(destination+1, 0, newChords[newChords.length-1-i]);
		}
	},
	
	showTextEditor : function() {
		// Put the text data in the box
		var textData = this.dataAsText();
		$('text_chords').value = textData;
		// Display the editor
		$('text_chord_editor').setStyle('display','block');
	},
	
	submitTextEditor : function() {
		var data = $('text_chords').value;
		this.dataFromText(data);
		this.hideTextEditor();
	},
	
	hideTextEditor : function() {
		$('text_chord_editor').setStyle('display','none');
	},
	
	dataAsText : function() {
		// Return the data in a human editable text form
		var text = "";
		for (var i=0; i<this.data.length; i++) {
			text += chordToText(this.data[i]) + " ";
		}
		return text
	},
	
	dataFromText : function(text) {
		// Store the chord data from a text input
		var tokens = text.split(" ");
		var newData = [];
		for (var i=0; i<tokens.length; i++) {
			var tokenText = trim(tokens[i]);
			if (tokenText.length > 0) 
				newData.push(textToChord(tokens[i]));
		}
		this.data = newData;
		this.writeData();
		this.editingChord = undefined;
		this.newChordAfter = undefined;
		this.drawChords();
	},
	
	drawChords : function() {
		// Build the display elements
		// Read the data from the hidden input
		this.readData();
		// Put each chord on the page
		var lines = Array();
		var currentLine = Array();
		var beatsSoFar = 0;
		var spill;
		var colourIndex = 0;
		for (var chord=0; chord < this.data.length; chord++) {
			var current = this.data[chord];
			var colour = this.colourCycle[colourIndex];
			// Record the starting position of this chord
			this.chordPositions[chord] = [ beatsSoFar, lines.length ];
			if (beatsSoFar + current['duration'] >= this.beatsAcross) {
				if (beatsSoFar + current['duration'] > this.beatsAcross) {
					// Extends past the end: use up the remaining space
					spill = current['duration'] - this.beatsAcross + beatsSoFar;
				} else spill = 0;
				currentLine.push([current, {
						'block_length':this.beatsAcross-beatsSoFar,
						'colour':colour,
						'buttons': (spill==0),
						'text': true,
						'chord_number': chord
					}]);
				// Start a new line
				lines.push(currentLine);
				currentLine = Array();
				// Fill as many lines as necessary
				while (spill >= this.beatsAcross) {
					currentLine.push([current, {
						'block_length': this.beatsAcross,
						'colour': colour,
						'buttons': (spill == this.beatsAcross),
						'text': false,
						'chord_number': chord
					}])
					spill -= this.beatsAcross
					lines.push(currentLine);
					currentLine = Array();
				}
				if (spill > 0) {
					currentLine.push([current, {
							'block_length':spill,
							'colour':colour,
							'buttons':true,
							'text': false,
							'chord_number': chord
						}]);
				}
				beatsSoFar = spill;
			} else {
				// Add the chord to the line
				currentLine.push([current, {
						'block_length':current['duration'],
						'colour':colour,
						'buttons':true,
						'text':true,
						'chord_number': chord
					}]);
				beatsSoFar += current['duration'];
			}
			colourIndex = (colourIndex + 1) % this.colourCycle.length;
		}
		this.endPos = [ beatsSoFar, lines.length ];
		if (currentLine.length > 0) lines.push(currentLine);
		// Add elements to the page for these chords
		var container = $(this.chordChartId);
		// Clear all children
		container.getChildren().each(function(child) {
			child.dispose();
		});
		// Construct a closure for the click action
		var getEditClick = (function(i) {
			return (function(e) {
				this.editChord(i);
			}).bind(this)
		}).bind(this)
		var getAddClick = (function(i) {
			return (function(e) {
				// Prevent the edit box showing because we clicked within the area
				e.stopPropagation();
				this.editNewChordAfter(i);
				return false;
			}).bind(this)
		}).bind(this)
		var getDeleteClick = (function(i) {
			return (function(e) {
				// Prevent the edit box showing because we clicked within the area
				e.stopPropagation();
				this.deleteChord(i);
				this.editChord(i);
				return false;
			}).bind(this)
		}).bind(this)
		// Create a hover div to contain any text we want to hover
		hover_box = new Element("div", {
			'class' : 'hover_box'
		});
		hover_box.inject(window.document.body);
		this.hover_box = hover_box;
		for (var line=0; line<lines.length; line++) {
			var lineDiv = new Element("div", {
				'class' : 'chord_line'
			});
			for (var chord=0; chord<lines[line].length; chord++) {
				var current = lines[line][chord];
				// -4 for border and 1px gap
				var width = current[1]['block_length'] * this.beatWidth - 4;
				// The green box
				var chord_div = new Element("div", {
					'styles' : {
						'width' : width + 'px',
						'background-color' : current[1]['colour']
					},
					'class' : 'chord_box'
				}).inject(lineDiv);
				var clickables = [ chord_div ];
				if (current[1]['text']) {
					// The name of the chord
					var rootName = window.chordRoots[current[0]['root']];
					if (rootName == undefined)
						rootName = "\""+current[0]['root']+"\"";
					var typeName = window.chordTypes[current[0]['type']];
					if (typeName == undefined)
						typeName = current[0]['type'] + "??"
					var bassName = window.chordRoots[current[0]['bass']];
					if (bassName == undefined)
						bassName = "";
					else
						bassName = " /"+bassName;
					var additions = current[0]['additions'];
					var additionsSymbol = "";
					if (trim(additions).length > 0)
						additionsSymbol = "("+additions+")";
					var chordSymbol = rootName + typeName + additionsSymbol + bassName;
					var nameDiv = new Element("div", {
						'class' : 'chord_name',
						'html' : chordSymbol
					}).inject(chord_div);
					// The assigned category
					var catSymbol = "";
					if (current[0]['category'] != "") {
						catSymbol = current[0]['category'];
						if (window.pos_tags.indexOf(catSymbol) == -1)
							catSymbol = catSymbol + " (unknown)";
					}
					var catDiv = new Element("div", {
						'class' : 'category_name',
						'html' : catSymbol
					}).inject(chord_div);
					clickables.push(nameDiv);
					clickables.push(catDiv);
					// Another div to contain icons for extra features
					var iconDiv = new Element("div", {
						'class' : 'icon_box'
					});
					iconDiv.inject(chord_div);
					clickables.push(iconDiv);
					// Put the icons in the icon div
					if (current[0]['coord_resolved']) {
						(new Element("img", {
							'src' : '/media/img/icons/coord_resolved.png'
						})).inject(iconDiv);
					}
					if (current[0]['coord_unresolved']) {
						(new Element("img", {
							'src' : '/media/img/icons/coord_unresolved.png'
						})).inject(iconDiv);
					}
				}
				if (current[1]['buttons']) {
					// Button to add a new chord
					var addButton = new Element("a", {
						'href' : '#',
						'html' : '+',
						'onclick' : (function() { return false; })
					}).inject(
						new Element("div", {
							'class' : 'add_after'
						}).inject(chord_div));
					addButton.addEvent('click', getAddClick(current[1]['chord_number']));
					// Button to edit chord
					/*var editButton = new Element("a", {
						'href' : '#',
						'html' : 'Edit'
					}).inject(
						new Element("div", {
							'class' : 'edit_chord'
						}).inject(chord_div));
					clickables.push(editButton);*/
					// Button to delete chord
					var delButton = new Element("a", {
						'href' : '#',
						'html' : 'X'
					}).inject(
						new Element("div", {
							'class' : 'delete_chord'
						}).inject(chord_div));
					delButton.addEvent('click', getDeleteClick(current[1]['chord_number']));
				}
				// Allow clicking on the box itself and the edit button
				clickables.each(function(clickable) {
					clickable.addEvent('click', getEditClick(current[1]['chord_number']));
				});
			}
			lineDiv.inject(container);
		}
	},
	
	addHover : function(element, text) {
		element.addEvent('mouseover', (function(e) {
			box = this.hover_box;
			box.setStyle('display', 'block');
			box.set('html', text);
		}).bind(this));
		element.addEvent('mousemove', (function(e) {
			box = this.hover_box;
			box.setStyles({
				'left' : (e.page.x + 10) + 'px',
				'top' : (e.page.y + 10) + 'px'
			});
		}).bind(this));
		element.addEvent('mouseout', (function(e) {
			box = this.hover_box;
			box.setStyle('display', 'none');
		}).bind(this));
	}
});
