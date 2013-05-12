from __future__ import absolute_import
"""Additional CSV reading/writing utilities.

Comma-separated value file reader and writer that wraps the standard 
package to handle unicode.

This stuff comes straight from the example in the CSV package's 
documentation.

Original author: Skip Montanaro <skip@pobox.com>

@see: U{http://docs.python.org/library/csv.html}

"""

class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to 
    UTF-8.
    
    """
    def __init__(self, f, encoding):
        import codecs
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeCsvReader(object):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    
    """
    def __init__(self, f, dialect='excel', encoding="utf-8", **kwds):
        import csv
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeCsvWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    
    """
    def __init__(self, f, dialect='excel', encoding="utf-8", **kwds):
        import csv, cStringIO, codecs
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([unicode(s).encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
