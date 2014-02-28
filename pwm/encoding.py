import math
import string
from logging import getLogger

_logger = getLogger('pwm.encoding')

try:
    ord(b'1'[0])

    def ord_byte(char):
        ''' convert a single character into integer representation '''
        return ord(char)

except TypeError:
    # python 3
    def ord_byte(byte):
        ''' convert a single byte into integer representation '''
        return byte

DEFAULT_CHARSET = 'full'
DEFAULT_LENGTH = 16
PRESETS = {}

def ceildiv(dividend, divisor):
    ''' integer ceiling division '''
    return (dividend + divisor - 1) // divisor

def calc_chunklen(alph_len):
    '''
    computes the ideal conversion ratio for the given alphabet.
    A ratio is considered ideal when the number of bits in one output
    encoding chunk that don't add up to one input encoding chunk is minimal.
    '''
    binlen, enclen = min([
                          (i, i*8 / math.log(alph_len, 2))
                          for i in range(1, 7)
                         ], key=lambda k: k[1] % 1)

    return binlen, int(enclen)


class Encoder(object):
    '''
    general-purpose encoder. Encodes arbitrary binary data with a given
    specific base ("alphabet").
    '''

    def __init__(self, alphabet):
        self.alphabet = alphabet
        self.chunklen = calc_chunklen(len(alphabet))


    def encode(self, digest, totallen=DEFAULT_LENGTH):
        binstr = digest.digest()

        nchunks = ceildiv(len(binstr), self.chunklen[0])
        binstr = binstr.ljust(nchunks * self.chunklen[0], b'\0')

        return ''.join([
                self._encode_chunk(binstr, i) for i in range(0, nchunks)
            ])[:totallen]

    def _encode_chunk(self, data, index):
        '''
        gets a chunk from the input data, converts it to a number and
        encodes that number
        '''
        chunk = self._get_chunk(data, index)
        return self._encode_long(self._chunk_to_long(chunk))

    def _encode_long(self, val):
        '''
        encodes an integer of 8*self.chunklen[0] bits using the specified
        alphabet
        '''
        return ''.join([
                self.alphabet[(val//len(self.alphabet)**i) % len(self.alphabet)]
                for i in reversed(range(self.chunklen[1]))
            ])

    def _chunk_to_long(self, chunk):
        '''
        parses a chunk of bytes to integer using big-endian representation
        '''
        return sum([
                256**(self.chunklen[0]-1-i) * ord_byte(chunk[i])
                for i in range(self.chunklen[0])
            ])

    def _get_chunk(self, data, index):
        '''
        partition the data into chunks and retrieve the chunk at the given index
        '''
        return data[index*self.chunklen[0]:(index+1)*self.chunklen[0]]

PRESETS['full'] = string.ascii_lowercase + string.ascii_uppercase \
                  + 2 * string.digits + '!#$%&()*+,-./:;=?@[]^_|~'
DEFAULT_ALPHABET = PRESETS[DEFAULT_CHARSET]

def lookup_alphabet(charset):
    '''
    retrieves a named charset or treats the input as a custom alphabet and use that
    '''
    if charset in PRESETS:
        return PRESETS[charset]
    if len(charset) < 16:
        _logger.warning('very small alphabet in use, possibly a failed lookup?')
    return charset
