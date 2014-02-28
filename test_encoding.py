import pwm.encoding as uut

import string
import unittest

class EncodingTest(unittest.TestCase):

    def testCeilDiv(self):
        self.assertEqual(uut.ceildiv(0, 1), 0)
        self.assertEqual(uut.ceildiv(0, 7), 0)

        self.assertEqual(uut.ceildiv(1, 7), 1)
        self.assertEqual(uut.ceildiv(6, 7), 1)

        self.assertEqual(uut.ceildiv(7, 7), 1)
        self.assertEqual(uut.ceildiv(1, 1), 1)

        self.assertEqual(uut.ceildiv(8, 7), 2)
        self.assertEqual(uut.ceildiv(13, 7), 2)
        self.assertEqual(uut.ceildiv(14, 7), 2)
        self.assertEqual(uut.ceildiv(2, 1), 2)

    def testChunkLen(self):
        self.assertEqual(uut.calc_chunklen(64), (3, 4))
        self.assertEqual(uut.calc_chunklen(256), (1, 1))
        self.assertEqual(uut.calc_chunklen(48), (5, 7))
        self.assertEqual(uut.calc_chunklen(16), (1, 2))

    def testChunks(self):
        enc = uut.Encoder('a' * 48)
        n = 5
        data = b'A'*n + b'B'*n + b'C'*n

        self.assertEqual(enc._get_chunk(data, 0), b'A'*n)
        self.assertEqual(enc._get_chunk(data, 1), b'B'*n)
        self.assertEqual(enc._get_chunk(data, 2), b'C'*n)

    def testChunkToLong(self):
        enc = uut.Encoder('a' * 48)
        self.assertEqual(enc._chunk_to_long(b'\0\0\0\0\xff'), 255)
        self.assertEqual(enc._chunk_to_long(b'\0\0\0\xff\0'), 255 << 8)
        self.assertEqual(enc._chunk_to_long(b'\0\0\xff\0\0'), 255 << 16)
        self.assertEqual(enc._chunk_to_long(b'\0\xff\0\0\0'), 255 << 24)
        self.assertEqual(enc._chunk_to_long(b'\xff\0\0\0\0'), 255 << 32)

    def testLookupAlphabet(self):
        self.assertNotEqual(uut.lookup_alphabet('full'), 'full')
        self.assertEqual(uut.lookup_alphabet(string.ascii_letters),
                         string.ascii_letters)
