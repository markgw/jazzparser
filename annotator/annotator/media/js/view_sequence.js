/*
 * A read-only version of the ChordEditor for outputting lots of 
 * chord sequences. Designed to have more than one on a page and 
 * doesn't show any editing features.
 * 
 * This code is copied (boo) directly from the main chord editor, with
 * editing functionality removed. This is nasty, but will do the job 
 * for now. Ideally, the ChordEditor would subclass this.
 */


function trim(stringToTrim) {
	return stringToTrim.replace(/^\s+|\s+$/g,"");
}
function ltrim(stringToTrim) {
	return stringToTrim.replace(/^\s+/,"");
}
function rtrim(stringToTrim) {
	return stringToTrim.replace(/\s+$/,"");
}

var ChordViewer = new Class({
	initialize : function(id, options) {
		this.id = id;
		this.options = options;
		this.input = id + "_data";
		this.chordChartId = id + "_chords";
		this.colourCycle = ['#C7E0C5','#C6D8E0'];
		this.chordPositions = [];
		this.endPos = [0,0];
		this.lineHeight = 66;
		this.verticalOffset = 285;
		this.horizontalOffset = 20;
		
		if (options['bar_length'] != undefined)
			this.barLength = options['bar_length'];
		else
			this.barLength = 4;
			
		if (options['show_cat'] == undefined)
			options['show_cat'] = true;
		
		this.calculateWidth(options);
		
		this.drawChords();
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
	},
	
	readData : function() {
		this.data = JSON.decode($(this.input).value);
		if (this.data.length == undefined) {
			this.data = [];
		}
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
						if (window.pos_tags.indexOf(catSymbol) == -1) {
							// We don't know this category label - it's probably old
							catSymbol = current[0]['category'] + " (unknown)";
							if (this.options['highlight_unknown'])
								// We highlight the categories that aren't in our dictionary
								catSymbol = '<strong>'+catSymbol+'</strong>';
						}
					} else if (this.options['highlight_unknown']) {
						// Just show question marks to highlight the empty space
						catSymbol = '<strong>??</strong>';
					}
					var catDiv = new Element("div", {
						'class' : 'category_name',
						'html' : catSymbol
					}).inject(chord_div);
				}
			}
			lineDiv.inject(container);
		}
	}
});

