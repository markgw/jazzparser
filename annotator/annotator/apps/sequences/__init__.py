import jazzparser.settings as jazzsettings
from django.conf import settings
from jazzparser.grammar import Grammar
import re


def prepare_pos_tags():
    # Read in the possible categories from the grammar
    if settings.GRAMMAR is None:
        grammar = Grammar(jazzsettings.DEFAULT_GRAMMAR)
    else:
        grammar = Grammar(settings.GRAMMAR)
    return list(sorted(grammar.families.keys()))
    
pos_tags = prepare_pos_tags()
    
def prepare_category_pairs():
    """
    Used to display something fancy as tag label, but now POS tags 
    are readable themselves.
    """
    return [(t,t) for t in pos_tags]
    
category_pairs = prepare_category_pairs()
