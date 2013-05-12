#!/usr/bin/env ../../jazzshell
from optparse import OptionParser
from jazzparser.data.tonalspace import TonalSpaceAnalysisSet

def main():
    usage = "%prog <name>"
    description = "Delete a tonal space analysis set"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    name = arguments[0]
    tsset = TonalSpaceAnalysisSet.load(name)
    tsset.delete()

if __name__ == "__main__":
    main()
