from __future__ import absolute_import
"""Internet access utilities.

Utilities for retreiving information or files from the internet.

"""
"""
============================== License ========================================
 Copyright (C) 2008, 2010-12 University of Edinburgh, Mark Granroth-Wilding
 
 This file is part of The Jazz Parser.
 
 The Jazz Parser is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 The Jazz Parser is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 
 You should have received a copy of the GNU General Public License
 along with The Jazz Parser.  If not, see <http://www.gnu.org/licenses/>.

============================ End license ======================================

"""
__author__ = "Mark Granroth-Wilding <mark.granroth-wilding@ed.ac.uk>"

SOURCES = ['jazzpage','vanbasco','intersearch','melodycatcher']

def find_midi_files(name, sources=None, verbose_out=None):
    """
    Given the name of a piece of music, tries to retrieve MIDI files 
    for a piece of that name.
    
    Looks up the name on vanBasco's midi search and tries to parse the 
    results to pull the file urls out. Most of these will fail, either 
    because the midi file isn't accessible at the obviously place, or 
    because the link's out of date (many are).
    
    C{name} may be a unicode string.
    
    @type sources: list of strings
    @param sources: list of source names to get files from. 
        Possibilities are in L{SOURCES}. If None, uses all sources.
    @type verbose_out: writable file-like object
    @param verbose_out: stream to send verbose output to (default None - 
        no verbose output)
    @return: list of (midi-file,song-name) pairs each containing a 
        L{midi.EventStream} for each file.
    
    """
    if sources is not None:
        for source in sources:
            if source not in SOURCES:
                raise ValueError, "invalid source name '%s'. Possibilities "\
                    "are: %s" % ", ".join(SOURCES)
    if sources is None or len(sources) == 0:
        # Default to using all sources
        sources = SOURCES
    
    # Fetch files from each source in turn
    files = []
    if 'vanbasco' in sources:
        files.extend(van_basco_midi_files(name, verbose_out=verbose_out))
    if 'jazzpage' in sources:
        files.extend(the_jazz_page_midi_files(name, verbose_out=verbose_out))
    if 'intersearch' in sources:
        files.extend(intersearch_midi_files(name, verbose_out=verbose_out))
    if 'melodycatcher' in sources:
        files.extend(melody_catcher_midi_files(name, verbose_out=verbose_out))
    # Get rid of any duplicates of the same data
    return remove_duplicate_files(files, key=lambda d:d[0])
    
def remove_duplicate_files(files, key=lambda x:x):
    """
    Given a list of file data strings, removes any duplicates of 
    the same data. Only the first occurence of the file data will 
    be kept.
    
    The list doesn't have to be just of the data, as long as the data 
    is returned by the key function applied to each value in the list.
    
    """
    keys = [key(f) for f in reversed(files)]
    to_remove = []
    for i,data in enumerate(keys):
        if data in keys[i+1:]:
            to_remove.append(i)
    print "Removing %d duplicates" % len(to_remove)
    
    files = list(reversed(
                [f for (i,f) in enumerate(reversed(files)) 
                    if i not in to_remove]
            ))
    return files
    
def the_jazz_page_midi_files(name, refresh_cache=False, verbose_out=None):
    """
    The Jazz Page has quite a few of midi files on a single page. 
    There's only one of most songs and it's not exactly a huge database, 
    but they claim to be high quality.
    
    By default, the list of midi files and song names will be cached 
    the first time it's fetched. Subsequently, songs will just be 
    looked up in the local database. Use C{refresh_cache=True} to 
    force the list to be re-read from the site.
    
    To refresh the cache without doing a search, see 
    L{refresh_the_jazz_page_cache}.
    
    @return: list of (midi-file,song-name) pairs each containing a 
        L{midi.EventStream} for each file. Unlikely to be more than one.
    
    """
    from jazzparser.settings import LOCAL_DATA_DIR
    from jazzparser.utils.csv import UnicodeCsvReader
    from urllib2 import urlopen, HTTPError, URLError
    from midi import read_midifile, MidiReadError
    import os, difflib
    from cStringIO import StringIO
    
    def _verbose(message):
        if verbose_out is not None:
            print >>verbose_out, message
            
    _verbose("<<<<<<<<<< The Jazz Page midi search >>>>>>>>>>>>>>")
    
    # Try reading the cache to see if we've fetched the data before
    cache_filename = os.path.join(LOCAL_DATA_DIR, "the_midi_site_cache")
    cached = os.path.exists(cache_filename)
    
    # Recreate the cache if it doesn't exist or it's being forced
    if not cached or refresh_cache:
        refresh_the_jazz_page_cache()
    
    # Now read in the cache from the file
    cache_file = open(cache_filename, 'r')
    try:
        reader = UnicodeCsvReader(cache_file)
        song_names = {}
        # Index the links by song name (allowing for multiple songs with 
        #  the same name)
        for link,song_name in reader:
            song_names.setdefault(song_name,[]).append(link)
    finally:
        cache_file.close()
    
    # Fetch each file for songs whose names are close to the search term
    _verbose("Searching for song name: %s" % name)
    matches = difflib.get_close_matches(name.lower(), song_names.keys(), cutoff=0.8)
    if len(matches) == 0:
        _verbose("No matches found")
    
    files = []
    for name in matches:
        for link in song_names[name]:
            _verbose("Fetching midi file %s" % link)
            file_data = urlopen(link).read()
            files.append((file_data, link, name))
        
    # Check that each one is actually a MIDI file (these should be good 
    #  quality in general)
    ok_files = []
    for data,link,name in files:
        try:
            mid = read_midifile(StringIO(data))
        except MidiReadError, err:
            _verbose("Invalid midi file: %s (%s)" % (link, err))
            # Skip this file
            pass
        else:
            ok_files.append((data,name))
    return ok_files
    
def refresh_the_jazz_page_cache():
    """
    Reads entries from The Jazz Page into a local cache for searching.
    
    @see: L{the_jazz_page_midi_files}
    
    """
    import os
    from urllib2 import urlopen
    from BeautifulSoup import BeautifulSoup
    from jazzparser.settings import LOCAL_DATA_DIR
    from jazzparser.utils.csv import UnicodeCsvWriter
    
    cache_filename = os.path.join(LOCAL_DATA_DIR, "the_midi_site_cache")
    domain = "http://www.thejazzpage.de"
    index_url = "%s/midiinfo.html" % domain
    
    if os.path.exists(cache_filename):
        # Remove the old cache file
        os.remove(cache_filename)
    # Create a new cache file
    cache_file = open(cache_filename, 'w')
    try:
        writer = UnicodeCsvWriter(cache_file)
        # Read in the index page to get the list of entries from
        soup = BeautifulSoup(urlopen(index_url).read())
        # After the first table, each one is a letter, apart from the last one
        tables = soup.findAll("table")[1:-1]
        rowspan = 0
        for table in tables:
            for row in table.findAll("tr"):
                cells = list(row)
                if rowspan == 0:
                    if cells[0].has_key("rowspan"):
                        rowspan = int(cells[0]["rowspan"]) -1
                    # This is a row with a first column in it
                    # Ignore the first column - we're only want the 2nd
                    middle_cell = cells[1]
                else:
                    middle_cell = cells[0]
                    rowspan -= 1
                # Get the file and song name from the middle cell
                if middle_cell.a is not None:
                    link = middle_cell.a["href"]
                    link = "%s/%s" % (domain,link)
                    name = middle_cell.a.text
                    name = name.replace("\n","").lower()
                    writer.writerow([link, name])
    finally:
        cache_file.close()



def van_basco_midi_files(name, verbose_out=None):
    """
    One method of getting midi files used by L{find_midi_files}.
    
    Looks up the name on vanBasco's midi search and tries to parse the 
    results to pull the file urls out. Most of these will fail, either 
    because the midi file isn't accessible at the obviously place, or 
    because the link's out of date (many are).
    
    Beware that this can take a long time, since it has to look up many 
    servers and most of them are slow.
    
    @type verbose_out: file-like object
    @param verbose_out: stream to print verbose output to. This is a 
        good way of knowing whether anything's happening, since this 
        process can be slow.
    @return: list of (midi-file,song-name) pairs each containing a 
        L{midi.EventStream} for each file. May return up to 50, but 
        probably far fewer.
    
    """
    from urllib2 import urlopen, HTTPError, URLError
    from xml.sax.saxutils import unescape
    from urllib import quote
    from BeautifulSoup import BeautifulSoup, NavigableString
    from midi import read_midifile, MidiReadError
    from cStringIO import StringIO
    
    def _verbose(message):
        if verbose_out is not None:
            print >>verbose_out, message
    
    _verbose("<<<<<<<<<< vanBasco midi search >>>>>>>>>>>>>>")
    
    string_name = name.encode('ascii', 'replace')
    # Construct the url for the search query
    query = u"+".join(name.split())
    domain = "http://www.vanbasco.com"
    url = "%s/search.html?resultsperpage=50&q=%s" % (domain, quote(query.encode('utf-8')))
    _verbose("Querying %s" % url)
    
    def _links_from_page(page_url, mirror_page=False):
        """
        This parses a page of vanBasco results and pulls out possible 
        midi file links from it.
        
        It's defined as a function so that it can be called recursively 
        if the midi file isn't found, but a page of mirrors is offered 
        by vanBasco. The mirrors page is almost the same as the results 
        page.
        
        """
        # Read the page into a beautiful soup to parse it
        soup = BeautifulSoup(urlopen(page_url).read())
        # Pull out the central part of the page
        central = soup.table.tr.findAll("td", recursive=False)[1]
        
        # The mirrors pages are structured very slightly differently
        if mirror_page:
            central = central.p.contents
        else:
            central = central.contents
        
        # Pick out the lines we want from this
        midi_files = []
        current_link = None
        current_name = None
        current_filename = None
        current_mirrors = None
        
        for tag in central:
            if isinstance(tag, NavigableString):
                # Just a raw string: see if it's a filename
                if current_link is not None:
                    # Try to pull a MIDI filename out of this line
                    line = unescape(unicode(tag)).lower().replace("&nbsp;", " ")
                    name = line.split()[0]
                    if name.endswith(".mid") or name.endswith(".midi"):
                        # Found one: use this with the link we have already
                        current_filename = name
            elif tag.name == "a":
                link = tag['href']
                if link.startswith("http://"):
                    # External link: treat as a new result
                    if current_filename is not None:
                        # First store the previous result
                        midi_files.append((current_link,
                                           current_filename,
                                           current_name,
                                           current_mirrors))
                    current_link = unicode(link)
                    current_name = unicode(tag.contents[0])
                    current_filename = None
                    current_mirrors = None
                elif link.startswith("/search.html"):
                    # This is a link to a mirrors page: keep it in case 
                    #  we can't get the main file
                    current_mirrors = u"%s%s" % (domain, link)
        # Add the final link
        if current_link is not None and current_filename is not None:
            # First store the previous result
            midi_files.append((current_link,
                               current_filename,
                               current_name,
                               current_mirrors))
        
        # Try to get a MIDI file from each of these links
        files = []
        for link,filename,name,mirror_link in midi_files:
            # Many of these will fail, since the sites are crap and most 
            #  files have gone. We'll get some, though, enshalla.
            _verbose("Trying to get file %s from %s" % (filename.encode('ascii','replace'), link.encode('ascii','replace')))
            try:
                got_file = get_linked_file(link, filename)
            except Exception, err:
                _verbose("  %s" % err)
                # File wasn't found, couldn't be read or timed out
                if not mirror_page and mirror_link is not None:
                    # Try going to the mirrors page to see if we can 
                    #  fetch any mirrors of this midi file
                    _verbose("Recursively fetching mirror files from %s" % mirror_link.encode('ascii','replace'))
                    mirror_files = _links_from_page(mirror_link, mirror_page=True)
                    if len(mirror_files) > 0:
                        # Found this file at at least one mirror
                        # Just use one copy of it
                        files.append(mirror_files[0])
                    _verbose("Returning to top level. Found %d mirror files" % len(mirror_files))
                # If no mirrors are available, we just accept that we 
                #  can't get the file and hope it wasn't any good anyway
            else:
                _verbose("  Success")
                files.append((got_file,filename,name))
        return files
        
    midi_files = _links_from_page(url)
            
    # Check that each one is actually a MIDI file - some may be adverts
    ok_files = []
    for data,filename,name in midi_files:
        try:
            mid = read_midifile(StringIO(data))
        except MidiReadError, err:
            _verbose("Invalid midi file: %s (%s)" % (filename.encode('ascii','replace'), err))
            # Skip this file
            pass
        else:
            ok_files.append((data,name))
    return ok_files



def intersearch_midi_files(name, verbose_out=None):
    """
    One method of getting midi files used by L{find_midi_files}.
    
    Looks up the name on Intersearch midi search and tries to parse the 
    results to pull the file urls out.
    
    This is very similar to the vanBasco search, since the results 
    are in roughly the same format. These pages are slightly cleaner.
    
    @see: U{http://www.inter-search.co.uk}
    
    @type verbose_out: file-like object
    @param verbose_out: stream to print verbose output to. This is a 
        good way of knowing whether anything's happening, since this 
        process can be slow.
    @return: list of (midi-file,song-name) pairs each containing a 
        L{midi.EventStream} for each file. May return up to 50, but 
        probably far fewer.
    
    """
    from urllib2 import urlopen, HTTPError, URLError
    from xml.sax.saxutils import unescape
    from urllib import quote
    from BeautifulSoup import BeautifulSoup, NavigableString
    from midi import read_midifile, MidiReadError
    from cStringIO import StringIO
    import re
    
    def _verbose(message):
        if verbose_out is not None:
            print >>verbose_out, message
    
    _verbose("<<<<<<<<<< Intersearch midi search >>>>>>>>>>>>>>")
    
    string_name = name.encode('ascii', 'replace')
    # Construct the url for the search query
    query = u"+".join(name.split())
    domain = "http://www.inter-search.co.uk"
    url = "%s/midi/search.pl?t=%s&m=1&x=50" % (domain, quote(query.encode('utf-8')))
    _verbose("Querying %s" % url)
    
    # Read the page into a beautiful soup to parse it
    soup = BeautifulSoup(urlopen(url).read())
    # Get all the paragraphs from the middle of the page
    pars = soup.findAll("p")
    
    # Ignore pars with certain CSS classes
    ignore_classes = ["b1", "b1t"]
    
    files = []
    # Pick out the lines we want from this
    for paragraph in pars:
        if paragraph.has_key("class") and paragraph["class"] in ignore_classes:
            continue
        # The link to the host page should be the only link in this par
        link = paragraph.findAll("a")[0]
        link.extract()
        url = link["href"]
        name = link.text
        # Process the remain tags one by one to find the filename
        filename = None
        for tag in paragraph:
            if isinstance(tag, NavigableString):
                # The first one is the filename, the rest is useless
                filename = unicode(tag)
                break
        if filename is None:
            # No filename found: can't do anything with this
            continue
        # Now try fetching the file
        _verbose("Trying to get file %s from %s" % (filename.encode('ascii','replace'), url.encode('ascii','replace')))
        try:
            got_file = get_linked_file(url, filename)
        except Exception, err:
            _verbose("  %s" % err)
        else:
            _verbose("  Success")
            files.append((got_file,filename,name))
    
    # Check that each one is actually a MIDI file - some may be adverts
    ok_files = []
    for data,filename,name in files:
        try:
            mid = read_midifile(StringIO(data))
        except MidiReadError, err:
            _verbose("Invalid midi file: %s (%s)" % (filename.encode('ascii','replace'), err))
            # Skip this file
            pass
        else:
            ok_files.append((data,name))
    return ok_files


def melody_catcher_midi_files(name, verbose_out=None):
    """
    One method of getting midi files used by L{find_midi_files}.
    
    Looks up the name on Melody Catcher midi search and tries to parse 
    the results to pull the file urls out.
    Melody Catcher is meant primarily as a query-by-humming search, but 
    also offers a title search, which we use.
    
    @see: U{http://www.melodycatcher.com}
    
    @type verbose_out: file-like object
    @param verbose_out: stream to print verbose output to. This is a 
        good way of knowing whether anything's happening, since this 
        process can be slow.
    @return: list of (midi-file,song-name) pairs each containing a 
        L{midi.EventStream} for each file. May return up to 50, but 
        probably far fewer.
    
    """
    from urllib2 import urlopen, Request
    from urllib import urlencode
    from BeautifulSoup import BeautifulSoup, NavigableString
    from midi import read_midifile, MidiReadError
    from cStringIO import StringIO
    from jazzparser.utils.strings import strip_accents
    
    def _verbose(message):
        if verbose_out is not None:
            print >>verbose_out, message
    
    _verbose("<<<<<<<<<< Melody Catcher midi search >>>>>>>>>>>>>>")
    
    string_name = name.encode('ascii', 'replace')
    # Remove accents from characters
    search_name = strip_accents(name)
    # Construct the url for the search query
    domain = "http://www.melodycatcher.com"
    url = "%s/search.php" % domain
    # Form uses POST to search (tut)
    post_data = {
        'ts' : search_name,   # Search query
        'send' : "Submit",
    }
    data = urlencode(post_data)
    request = Request(url, data)
    _verbose("Querying %s (POST: %s)" % (url,data))
    
    # Read the page into a beautiful soup to parse it
    soup = BeautifulSoup(urlopen(request).read())
    # Simplest way to detect no results: this string somewhere on the page
    if "No results found for your search" in str(soup):
        _verbose("No results")
        return []
    # First table is the whole page (tut), next two are menus, third 
    #  is search form, fourth contains the results
    table = soup.findAll("table")[4]
    # Each row is a result
    files = []
    for row in table.findAll("tr"):
        # We only want the second column
        cell = row.findAll("td")[1]
        # The first link is to the midi file
        link = cell.findAll("a")[0]
        url = link["href"]
        # Get rid of the file extension from the name (which is really 
        #  a filename, but not a nice one)
        name = link.text.encode('ascii','ignore').replace(".midi","").replace(".mid","")
        filename = url.rpartition("/")[2]
        # Now try fetching the file itself
        _verbose("Trying to get %s" % url)
        try:
            got_file = urlopen(url, timeout=3)
        except Exception, err:
            _verbose("  %s" % err)
        else:
            _verbose("  Success")
            files.append((got_file.read(),filename,name))
            got_file.close()
    
    # Check that each one is actually a MIDI file - some may be adverts
    ok_files = []
    for data,filename,name in files:
        try:
            mid = read_midifile(StringIO(data))
        except MidiReadError, err:
            _verbose("Invalid midi file: %s (%s)" % (filename, err))
            # Skip this file
            pass
        else:
            ok_files.append((data,name))
    return ok_files


def get_linked_file(page_url, filename, timeout=3):
    """
    Often the links on search results pages for MIDI files will be to 
    a page that references the file, rather than to the file itself.
    Given the url to this page and the filename (also supplied in the 
    search results), this function returns the file itself, if it 
    can find it on the page.
    
    This may raise an exception in the process of fetching the file. 
    This function doesn't catch anything raised by urlopen.
    
    If a link to the file can't be found on the page, we next try 
    getting the file from the same directory as the page. If neither 
    of these works, the last error encountered while try to get a file 
    is raised (although errors reading files linked to on the page will 
    be raised in preference to those from the last-ditch directory 
    attempt).
    
    @type timeout: int
    @param timeout: a timeout used on every url access (default 3 secs)
    
    """
    from BeautifulSoup import BeautifulSoup
    from urllib2 import urlopen
    from urllib import quote
    from urlparse import urljoin
    
    # Fetch the referring page and parse it
    soup = BeautifulSoup(urlopen(page_url, timeout=timeout).read())
    # Get all the links out of the page
    links = soup.findAll("a")
    file_links = []
    last_error = None
    # Look for possible links to this file
    for link in links:
        if link.has_key("href"):
            target = urljoin(page_url, link["href"])
            if target.endswith(filename):
                # Looks like this is a link to the right file
                try:
                    link_file = urlopen(target, timeout=timeout)
                    try:
                        return link_file.read()
                    finally:
                        link_file.close()
                except Exception, err:
                    # Don't raise this unless this is the last link available
                    last_error = err
                    continue
    # No more links left to try
    # Last ditch attempt: try the directory containing the page
    link = urljoin(page_url, filename)
    try:
        link_file = urlopen(link, timeout=timeout)
        try:
            return link_file.read()
        finally:
            link_file.close()
    except Exception, err:
        if last_error is None:
            last_error = err
    # If there was an error, raise it
    raise last_error


def get_vanilla_book():
    """
    Downloads the whole of the Vanilla Book: 
    L{http://www.ralphpatt.com/Song.html}.
    
    """
    from BeautifulSoup import BeautifulSoup
    from urllib2 import urlopen
    from urllib import quote
    from urlparse import urljoin
    import re
    from jazzparser.utils.base import group_pairs
    
    #~ raise NotImplementedError, "not finished writing this"
    
    INDEX_PAGE = 'http://www.ralphpatt.com/Song.html'
    SONG_BASE = 'http://www.ralphpatt.com/'
    # The overbar alternative ending marker
    alt_end_re = re.compile(r'(\d+).(_+)')
    
    # Fetch the referring page and parse it
    soup = BeautifulSoup(urlopen(INDEX_PAGE).read())
    # Pull out all the links
    links = soup.findAll("a")
    # Get just the links to songs: all in VB/
    song_links = [l['href'] for l in links if l.has_key("href") and \
                                        l['href'].startswith("VB/")]
    
    for song_link in song_links:
        url = "%s%s" % (SONG_BASE, song_link)
        song_soup = BeautifulSoup(urlopen(url).read())
        # The song's name is in the title tag
        song_name = song_soup.title.string.strip()
        print song_name
        # The chords are in a pre tag
        chord_text = ''.join(song_soup.body.pre.findAll(text=True))
        # Remove the key line
        lines = chord_text.split("\n")
        start_line = 0
        for i,line in enumerate(lines):
            if line.lower().startswith("key"):
                # Found the key line: ignore everything up to here
                start_line = i+1
                break
        else:
            # No key line found!
            print "No key line for %s" % song_name
            continue
        lines = lines[start_line:]
        
        # Find the chord lines: they start with | or [
        song_lines = []
        for i,line in enumerate(lines):
            if line.startswith("[") or line.startswith("|"):
                song_lines.append((lines[i-1], lines[i]))
        
        try:
            bars = []
            bar_ranges = []
            open_repeats = []
            for overline,line in song_lines:
                barlines = list(re.finditer(r"(\|\|)|(\|)|(\[:)|(:\])|(\[)", line))
                barline_ptns = []
                for i,(start_match,end_match) in enumerate(group_pairs(barlines)):
                    # If the bar has zero length, it's just two barlines 
                    #  next to each other: ignore
                    if start_match.end() == end_match.start():
                        continue
                    barline_ptns.append(start_match.start())
                    # Get the upper and lower parts of this bar
                    if i == len(barlines) - 2:
                        # If this is the last bar on the line, go to the end
                        overbar = overline[start_match.start()-2:]
                    else:
                        overbar = overline[start_match.start()-2:end_match.start()]
                    overbar_cnt = overbar.strip()
                    if len(overbar_cnt) < 2:
                        overbar_cnt = ""
                    bar = line[start_match.end():end_match.start()]
                    
                    # We might loose some timing information at this point, 
                    #  but it's not really worth trying to get
                    chords = [str(c) for c in bar.split() if c != "/"]
                    bars.append(chords)
                    
                    # Check the starting barline for a repeat
                    barline = line[start_match.start():start_match.end()]
                    end_barline = line[end_match.start():end_match.end()]
                    # If we're starting a repeat, note that it starts here
                    if barline == "[:":
                        open_repeats.append(len(bars)-1)
                    # If we're ending a repeat, copy in the repeated bars
                    if end_barline == ":]":
                        if len(open_repeats) == 0:
                            print "Unmatched open repeat in %s" % song_name
                            raise ChordSequenceParseError
                        repeat_start = open_repeats.pop()
                        bars.extend(bars[repeat_start:])
                
                    if overbar_cnt.startswith("__"):
                        overbar_cnt = overbar_cnt[2:].lstrip()
                    elif overbar_cnt.startswith("_"):
                        overbar_cnt = overbar_cnt[1:].lstrip()
                    if len(overbar_cnt):
                        alt_end = alt_end_re.match(overbar_cnt)
                        if alt_end:
                            print "alt end", alt_end.groups()[0]
                        else:
                            print overbar_cnt
                    ## TODO: deal with alternative endings (in the overbar)
                    
        except ChordSequenceParseError:
            continue

def get_irealb(url, skip=0):
    """
    Get the iReal b format chord sequences from a webpage. The sequences are 
    encoded in a URL (!) which is huuuuge. The argument URL is that of the 
    page containing the URL with the sequences in. If C{skip} is given, 
    C{skip} irealb:// urls are skipped (in case you don't want to download 
    the first on the page).
    
    """
    from BeautifulSoup import BeautifulSoup
    from urllib2 import urlopen
    from urllib import unquote
    
    # Fetch the page and parse it
    soup = BeautifulSoup(urlopen(url).read())
    # Pull out all the links
    links = soup.findAll("a")
    # Get just the links that are sequence databases
    irealb_links = [l['href'] for l in links if l.has_key("href") and \
                                        l['href'].startswith("irealb://")]
    if skip >= len(irealb_links):
        raise ValueError, "there are only %d irealb links on the page" % \
            len(irealb_links)
    
    link = irealb_links[skip]
    text = unquote(link)
    
    for sequence in text.split("==0=0==="):
        data = sequence.split("=")
        # The last one is just the name of the corpus
        if len(data) < 2:
            continue
        # Split up the meta data
        # 2 doesn't seem to be used (lyricist?)
        # 5 is never used
        name = data[0]
        composer = data[1]
        style = data[3]
        key = data[4]
        chord_data = data[6]
        print "=== %s ===" % name
        # Decode the chord sequences
        for bar in chord_data.split("|"):
            print "BAR"
            for chord in bar.split(","):
                ### TODO: can't work out how to decode this
                print chord

class ChordSequenceParseError(Exception):
    pass
