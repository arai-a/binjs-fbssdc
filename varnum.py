#!/usr/bin/env python3

import struct

# Implementation of vbytes

def write(value, out):
    while True:
        byte = ((value & 0x7F) << 1)
        if value > 0x7F:
            byte |= 1
        out.write(struct.pack('B', byte))
        value >>= 7
        if value == 0:
            break

def read(inp):
    '''Read a varnum
    >>> import io
    >>> def roundtrip(sample):
    ...   buf = io.BytesIO()
    ...   write(sample, buf)
    ...   print(len(buf.getvalue()))
    ...   buf.seek(0)
    ...   return read(buf)
    >>> roundtrip(0)
    1
    0
    >>> roundtrip(1)
    1
    1
    >>> roundtrip(10)
    1
    10
    >>> roundtrip(777)
    2
    777
    '''

    result = 0
    shift = 0
    while True:
        assert shift < 32 # FIXME: We need a better error message
        byte = struct.unpack('B', inp.read(1))[0]
        result |= (byte >> 1) << shift
        if byte & 1 == 0:
            return result
        shift += 7
