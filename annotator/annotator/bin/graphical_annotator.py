"""
Runs the GUI tool for annotation.
"""
import sys
from optparse import OptionParser

from gui import SongListWindow

import gtk
    
def main():
    description = "Runs the graphical annotation tool"
    parser = OptionParser()
    options, arguments = parser.parse_args()
    
    window = SongListWindow()
    gtk.main()
    
if __name__ == "__main__":
    main()
