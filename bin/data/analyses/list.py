#!/usr/bin/env ../../jazzshell
from optparse import OptionParser
from jazzparser.data.tonalspace import TonalSpaceAnalysisSet

def main():
    usage = "%prog"
    description = "List tonal space analysis sets"
    parser = OptionParser(usage=usage, description=description)
    options, arguments = parser.parse_args()
    
    print ", ".join(TonalSpaceAnalysisSet.list())

if __name__ == "__main__":
    main()
