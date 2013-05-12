"""
Outputs latex code to draw a segment of the Longuet-Higgins tonal 
space to stdout.

Example usage:
  ./jazzshell latex_tonal_space.py -f n9,n6 -t 9,6 -s 1.5 -p 340x240 >tonalspace.tex
produces a huge tonal space on a big page.

@note: I have also developed a Latex package called C{tonalspace} for doing 
all of this within Latex. You should use that instead if possible.

"""
import sys, os
from optparse import OptionParser

def main():
    usage = "%prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-f", "--from", dest="bottom_left", action="store", default="-4,-2", help="coordinate of the bottom left square of the region to draw, in the form \"x,y\", where 0,0 is the central I. You may use \"n\" instead of \"-\" for negatives. [Default: -4,-2]")
    parser.add_option("-t", "--to", dest="top_right", action="store", default="4,3", help="coordinate of the top right square of the region to draw. [Default: 4,3]")
    parser.add_option("-s", "--grid-scale", dest="grid_scale", action="store", help="scaling factor for the grid. Note that this will not scale the text.")
    parser.add_option("-p", "--page-size", dest="page_size", action="store", help="page dimensions in the form \"WxH\", where W and H are the width and height in mm. [Default: a4]")
    parser.add_option("-a", "--alpha", dest="alpha", action="store_true", help="use note names, rather than roman numeral names.")
    options, arguments = parser.parse_args()
    
    # Get the coordinates of the region to draw
    bl = options.bottom_left.replace("n","-")
    bl_x,bl_y = bl.split(",")
    bottom_left = int(bl_x), int(bl_y)
    
    tr = options.top_right.replace("n", "-")
    tr_x,tr_y = tr.split(",")
    top_right = int(tr_x), int(tr_y)
    
    print >>sys.stderr, "Drawing tonal space region from %s to %s" % (bottom_left, top_right)
    
    # Options for the tikzpicture environment
    tikz_options = ""
    if options.grid_scale is not None:
        tikz_options += "scale=%s" % options.grid_scale
    # Add any other options here
    
    if tikz_options != "":
        tikz_options = "[%s]" % tikz_options
        
    # Further options to go in the preamble
    extra_preamble = ""
    
    if options.page_size is not None:
        width,height = options.page_size.split("x")
        width = int(width)
        height = int(height)
        # Use the geometry package to set the page size
        extra_preamble += """\
\\usepackage[centering]{geometry}
\\geometry{papersize={%dmm,%dmm},margin={20mm,20mm}}
""" % (width,height)
    
    # Output preliminaries
    print """\
\\documentclass[landscape]{article}
\\usepackage{tikz}
\\usepackage{fullpage}

\\pagestyle{empty}
%s

\\begin{document}
\\begin{center}
    \\begin{tikzpicture}%s
        \\draw[style=help lines] (%d,%d) grid (%d,%d); """ % \
            (extra_preamble,
             tikz_options,
             bottom_left[0],
             bottom_left[1]-1, 
             top_right[0]+1,
             top_right[1])
    
    # Iterate downwards, left to right over the block
    for y in range(top_right[1], bottom_left[1]-1, -1):
        print "\n        %% Row %d" % y
        for x in range(bottom_left[0], top_right[0]+1):
            symbol = point_symbol((x,y), alpha=options.alpha)
            if y<=0:
                node_y = "-%d.5" % (-1*y)
            else:
                node_y = "%d.5" % (y-1)
            if x<0:
                node_x = "-%d.5" % (-1*(x+1))
            else:
                node_x = "%d.5" % x
            # Output a node to contain the text of the label
            print "        \\node [font=\\scriptsize] at (%s,%s) { $%s$ };" % \
                                            (node_x,node_y,symbol)
    
    # Output ending stuff
    print """\
    \\end{tikzpicture}
\\end{center}
\\end{document}
"""

def local_space(coordinate):
    """
    Given an absolute coordinate in the tonal space, returns the 
    coordinate of the local (wrapped) space.
    """
    x,y = coordinate
    space_x = (y + 2*x + 2) / 7
    space_y = (4*y + 1 + x) / 7
    return space_x,space_y
    
def local_coordinate(coordinate):
    """
    Given an absolute tonal space coordinate, returns the coordinate 
    relative to the base point (the IV) of that local space.
    """
    x,y = coordinate
    base_x,base_y = space_base(coordinate)
    return x-base_x, y-base_y
    
def space_base(coordinate):
    """
    Given an absolute coordinate, returns the base point of the local 
    space that contains it.
    """
    space_x,space_y = local_space(coordinate)
    base_x = 4*space_x - 1 - space_y
    base_y = 2*space_y - space_x
    return base_x,base_y
    
POINT_NAMES = {
    (0,0) : "IV",
    (1,0) : "I",
    (2,0) : "V",
    (3,0) : "II",
    (0,1) : "VI",
    (1,1) : "III",
    (2,1) : "VII",
}

ALPHA_POINT_NAMES = {
    (0,0) : "F",
    (1,0) : "C",
    (2,0) : "G",
    (3,0) : "D",
    (0,1) : "A",
    (1,1) : "E",
    (2,1) : "B",
}
    
def point_symbol(coordinate, alpha=False):
    """
    Given an absolute coordinate, returns the string symbol that names
    that point.
    """
    # Choose the basic symbol by getting the coordinate within the 
    #  limited local space
    local_coord = local_coordinate(coordinate)
    if alpha:
        basic_name = ALPHA_POINT_NAMES[local_coord]
    else:
        basic_name = POINT_NAMES[local_coord]
    # Work out the additions to the symbol on the base of which local 
    #  space it's in
    space_x,space_y = local_space(coordinate)
    # Add a sharp for each space up, a flat for each space down
    if space_y > 0:
        accidentals = (r"\sharp" * space_y) + " "
    elif space_y < 0:
        accidentals = (r"\flat" * (-1*space_y)) + " "
    else:
        accidentals = ""
    # Add a minus for each space left, a plus for each space right
    if space_x > 0:
        detune = '^{%s}' % ('+'*space_x)
    elif space_x < 0:
        detune = '^{%s}' % ('-'*(-1*space_x))
    else:
        detune = ''
    return "%s%s%s" % (accidentals, basic_name, detune)

if __name__ == "__main__":
    sys.exit(main())
