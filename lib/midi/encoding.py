"""Utilities needed for encoding/decoding MIDI data.

"""

def read_varlen(data):
    """
    Reads a variable-length value from a stream as used in MIDI data.
    Pops all the bytes that form a part of the value and returns the 
    decoded numeric value.
    
    """
    NEXTBYTE = 1
    value = 0
    while NEXTBYTE:
        chr = ord(data.next())
        # is the hi-bit set?
        if not (chr & 0x80):
            # no next BYTE
            NEXTBYTE = 0
        # mask out the 8th bit
        chr = chr & 0x7f
        # shift last value up 7 bits
        value = value << 7
        # add new value
        value += chr
    return value

def write_varlen(value):
    """
    Encodes the given numeric value as a MIDI variable-length value 
    and returns the data as a string that should be written to a 
    data stream to represent that value.
    
    """
    if value>=pow(2,28):
        raise ValueError("A varlen must be less than 2^28")
    chr1 = chr(value & 0x7F)
    value >>= 7
    if value:
        chr2 = chr((value & 0x7F) | 0x80)
        value >>= 7
        if value:
            chr3 = chr((value & 0x7F) | 0x80)
            value >>= 7
            if value:
                chr4 = chr((value & 0x7F) | 0x80)
                res = chr4 + chr3 + chr2 + chr1
            else:
                res = chr3 + chr2 + chr1
        else:
            res = chr2 + chr1
    else:
        res = chr1
    return res


def r_varlen(hexstring):
    "reads a hex value as a string, returns an integer"
    value = ''
    
    length = len(hexstring) / 2
    
    for i in range(length):
        byte = '0x'+hexstring[2*i]+hexstring[2*i+1]
        byte = int(byte,16)
        

        binstring = bin(int(byte))
        binstring = binstring[2:]
        binstring = '0'*(8-len(binstring))+binstring
        binstring = binstring[1:]
        
        value+=binstring
        
    value='0b'+value
    value=int(value,2)

    return value


def __test_varlen():
    for value in xrange(0x0FFFFFFF):
        if not (value % 0xFFFF):
            print hex(value)
        datum = write_varlen(value)
        newvalue = read_varlen(iter(datum))
        if value != newvalue: 
            hexstr = str.join('', map(hex, map(ord, datum)))
            print "%s != %s (hex: %s)" % (value, newvalue, hexstr)
