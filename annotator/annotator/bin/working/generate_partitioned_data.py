"""
Just a quick simple script to partition the data and output
for each partition a file containing the partition and a file 
containing the rest of the sequences.
Ignores all but fully annotated sequences.

Might want to make this into a more reusable script at some point.
"""

from apps.sequences.datautils import save_pickled_data
from apps.sequences.models import ChordSequence
from django.db.models import Q
from jazzparser.utils.data import holdout_partition, partition
import os.path, sys

NUM_PARTITIONS = 10
FILENAME = "partition"

# Build a list of the sequences to put in each partition
# Only include fully annotated sequences
print >>sys.stderr, "Building list of fully annotated sequences"
seqs = [seq.id for seq in 
                ChordSequence.objects.filter(analysis_omitted=False)
                if seq.fully_annotated]
partitions = zip(partition(seqs, NUM_PARTITIONS), holdout_partition(seqs, NUM_PARTITIONS))

for i,parts in enumerate(partitions):
    part, rest = parts
    # Output two files for each partition
    part_file = "%s-%d" % (FILENAME, i)
    held_file = "%s-%d-heldout" % (FILENAME, i)
    print >>sys.stderr, "Outputing partition %d to %s and %s" % (i, part_file, held_file)
    # Output the partition's file
    query = Q(id__in=part)
    save_pickled_data(part_file, query)
    # Output the rest of the data
    query = Q(id__in=rest)
    save_pickled_data(held_file, query)
