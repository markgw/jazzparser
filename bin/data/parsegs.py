#!/usr/bin/env ../jazzshell
import sys, os.path, logging

from jazzparser.data.db_mirrors import SequenceIndex
from jazzparser.data.tonalspace import TonalSpaceAnalysisSet
from jazzparser.evaluation.parsing import parse_sequence_with_annotations
from jazzparser.grammar import get_grammar
from jazzparser.utils.loggers import create_plain_stderr_logger
from jazzparser.utils.options import options_help_text, ModuleOption
from jazzparser.parsers.cky.parser import DirectedCkyParser
from jazzparser.parsers import ParseError

from optparse import OptionParser
    
def main():
    usage = "%prog [options] <seq-file>"
    description = "Parses a sequence from a sequence index file using the "\
        "annotations stored in the same file."
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("--popt", "--parser-options", dest="popts", action="append", help="specify options for the parser. Type '--popt help' to get a list of options (we use a DirectedCkyParser)")
    parser.add_option("--derivations", "--deriv", dest="derivations", action="store_true", help="print out derivation traces of all the results")
    parser.add_option("--index", "-i", dest="index", action="store", type="int", help="parse just the sequence with this index")
    parser.add_option("--quiet", "-q", dest="quiet", action="store_true", help="show only errors in the output")
    parser.add_option("--tonal-space", "--ts", dest="tonal_space", action="store_true", help="show the tonal space path (with -q, shows only paths)")
    parser.add_option("--output-set", "-o", dest="output_set", action="store", help="store the analyses to a tonal space analysis set with this name")
    parser.add_option("--trace-parse", "-t", dest="trace_parse", action="store_true", help="output a trace of the shift-reduce parser's operations in producing the full interpretation from the annotations")
    options, arguments = parser.parse_args()
    
    if len(arguments) < 1:
        print "You must specify a sequence file"
        sys.exit(1)
    
    if options.popts is not None:
        poptstr = options.popts
        if "help" in [s.strip().lower() for s in poptstr]:
            # Output this tagger's option help
            print options_help_text(DirectedCkyParser.PARSER_OPTIONS, intro="Available options for the directed parser")
            return 0
    else:
        poptstr = ""
    popts = ModuleOption.process_option_string(poptstr)
    
    grammar = get_grammar()
    if options.quiet:
        logger = create_plain_stderr_logger(log_level=logging.ERROR)
    else:
        logger = create_plain_stderr_logger()
    
    if options.trace_parse:
        parse_logger = logger
    else:
        parse_logger=None
    
    seq_index = SequenceIndex.from_file(arguments[0])
    # Get the chord sequence(s)
    if options.index is None:
        seqs = seq_index.sequences
    else:
        seqs = [seq_index.sequence_by_index(options.index)]
    logger.info("%d sequences\n" % len(seqs))
    
    full_analyses = []
    stats = {
        'full' : 0,
        'partial' : 0,
        'fail' : 0,
    }
    # Try parsing every sequence
    for seq in seqs:
        logger.info("====== Sequence %s =======" % seq.string_name)
        try:
            results = parse_sequence_with_annotations(seq, grammar, 
                                                      logger=logger, 
                                                      parse_logger=parse_logger)
        except ParseError, err:
            logger.error("Error parsing: %s" % err)
            stats['fail'] += 1
        else:
            # This may have resulted in multiple partial parses
            logger.info( "%d partial parses" % len(results))
            
            if len(results) == 1:
                stats['full'] += 1
            else:
                stats['partial'] += 1
            
            if options.derivations:
                # Output the derivation trace for each partial parse
                for result in results:
                    print
                    print result.derivation_trace
            
            if options.tonal_space:
                # Output the tonal space coordinates
                path = grammar.formalism.sign_to_coordinates(results[0])
                for i,point in enumerate(path):
                    print "%d, %d: %s" % (seq.id, i, point)
            
            # Only include a result in the output analyses if it was a full parse
            if len(results) == 1:
                full_analyses.append((seq.string_name, results[0].semantics))
            else:
                logger.warn("%s was not included in the output analyses, "\
                    "since it was not fully parsed" % seq.string_name)
    
    logger.info("Fully parsed: %d" % stats['full'])
    logger.info("Partially parsed: %d" % stats['partial'])
    logger.info("Failed: %d" % stats['fail'])
    
    if options.output_set:
        # Output the full analyses to a file
        anal_set = TonalSpaceAnalysisSet(full_analyses, options.output_set)
        anal_set.save()
        print "Wrote analyses to analysis set '%s'" % options.output_set
    
if __name__ == "__main__":
    main()
