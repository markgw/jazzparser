var HideableSection = new Class({
	initialize : function(togglerId, sectionId, showingText, hiddenText, initHidden) {
		this.togglerId = togglerId;
		this.sectionId = sectionId;
		
		var currentText = $(togglerId).get('html');
		if (showingText == undefined) this.showingText = currentText;
		else this.showingText = showingText;
		
		if (hiddenText == undefined) this.hiddenText = currentText;
		else this.hiddenText = hiddenText;
		
		this.showing = true;
		if (initHidden == undefined) initHidden = true;
		
		if (initHidden) this.hide();
		else this.show();
		
		$(this.togglerId).addEvent('click', (function() {
			this.toggle();
			return false;
		}).bind(this));
	},
	
	toggle : function() {
		if (this.showing) this.hide();
		else this.show();
	},
	
	hide : function() {
		var el = $(this.sectionId);
		el.setStyle('display', 'none');
		var toggler = $(this.togglerId);
		toggler.set('html', this.hiddenText);
		this.showing = false;
	},
	
	show : function() {
		var el = $(this.sectionId);
		el.setStyle('display', 'block');
		var toggler = $(this.togglerId);
		toggler.set('html', this.showingText);
		this.showing = true;
	}
});
