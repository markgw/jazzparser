from apps.sequences.models import ChordSequence, Chord, ChordType, Source
from django.contrib import admin

admin.site.register(Source)
admin.site.register(ChordSequence)
admin.site.register(Chord)
admin.site.register(ChordType)
