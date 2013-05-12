from math import log, pow

def sequence_entropy(chords, grammar, tagger_class, model=None):
    # Convert the chords into a suitable form for tagger input
    tagger_input = " ".join([chord.jazz_parser_input for chord in chords])
    # Do the tagging of the sequence
    if model is not None:
        tagger = tagger_class(grammar, tagger_input, model=model)
    else:
        tagger = tagger_class(grammar, tagger_input)
    # Compute the entropy for every chord
    total_entropy = 0.0
    total_chords = 0
    for i,chord in enumerate(chords):
        # Don't include chords that aren't annotated - we could never get them right
        if chord.category != "":
            probability = tagger.get_tag_probability(i, chord.category)
            if probability == 0.0:
                entropy = 0.0
            else:
                entropy = probability * log(probability, 2)
            total_entropy += entropy
            total_chords += 1
    total_entropy = -1 * total_entropy
    return (total_entropy, total_chords)
