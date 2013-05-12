#!../jazzshell
"""
Runs one of a selection of commands relating to the database. 
All of these require the Django annotator tool to be configured with a 
working chord sequence database.

All this does is to run scripts in the annotator tool's bin directory, 
but it makes it easier to run these common scripts without having to 
explore the annotator's codebase every time!

"""
import sys, os, subprocess
from optparse import OptionParser

DJANGO_PATH = os.path.join("..", "..", "annotator", "django-admin")

def _script_path(script):
    return os.path.join("..", "..", "annotator", "annotator", "bin", *script)

# Define the database tools that we provide access to
TOOLS = {
    'categories' : {
        'script' : ['count_category_use.py'],
        'desc' : 'Display statistics about the coverage of categories '\
            'in the annotations',
    },
    'chords' : {
        'script' : ['count_chord_type_use.py'],
        'desc' : 'Display statistics about the coverage of chord types '\
            'in the annotations',
    },
    'transpose' : {
        'script' : ['transpose_sequence.py'],
        'desc' : 'Transpose a single chord sequence',
    },
    'candcdata' : {
        'script' : ['data', 'generate_model_data.py'],
        'desc' : 'Generate data in a format suitable for training '\
            'a C&C model',
    },
    'pcfgtrain' : {
        'script' : ['data', 'train_pcfg.py'],
        'desc' : 'Train a PCFG model using the database\'s data',
    },
    'tree' : {
        'script' : ['analysis', 'build_tree.py'],
        'desc' : 'Build a derivation tree for an annotated sequence',
    },
    'parse' : {
        'script' : ['analysis', 'parse.py'],
        'desc' : 'Run the full parse according to the annotated '\
            'derivation structure of a sequence',
    },
    'sems' : {
        'script' : ['analysis', 'semantics.py'],
        'desc' : 'Run the full parse according to the annotated '\
            'derivation structure of a sequence in order to get the '\
            'semantics for it',
    },
    'seqinfo' : {
        'script' : ['analysis', 'sequence_info.py'],
        'desc' : 'Display some information about a chord sequence',
    },
    'deorphan' : {
        'script' : ['remove_orphaned_chords.py'],
        'desc' : 'Remove chords that do not belong to a chord sequence',
    },
    'ancov' : {
        'script' : ['analysis', 'annotation_coverage.py'],
        'desc' : 'Display statistics relating to the current coverage of '\
            'chord annotation',
    },
    'mirror' : {
        'script' : ['data', 'generate_mirror_data.py'],
        'desc' : 'Output database-independent mirrors of the sequences '\
            'in the database to a file',
    },
}

def main():
    arguments = sys.argv[1:]
    
    def _available_tools():
        return "\n".join(["%s:  %s" % (format(name, " >15s"), info['desc']) for \
                (name,info) in TOOLS.items()])
    
    if len(arguments) == 0:
        print >>sys.stderr, "Database Utilities\n==================\n"
        print >>sys.stderr, "Run data analysis and processing tools on "\
            "the annotation database. Note that the database must be "\
            "set up locally for these to work."
        print >>sys.stderr, "Specify a command to run. The following are "\
            "available:\n%s" % _available_tools()
        print >>sys.stderr, "\nUse the -h option to any command to get more information"
    elif arguments[0] not in TOOLS:
        print >>sys.stderr, "%s is not a known command. The following are "\
            "available:\n%s" % (arguments[0], _available_tools())
    else:
        script = _script_path(TOOLS[arguments[0]]['script'])
        pargs = [DJANGO_PATH, "run", script] + arguments[1:]
        print >>sys.stderr, "Running: %s" % " ".join(pargs)
        return subprocess.call(pargs)
    
if __name__ == "__main__":
    main()
