"""SID encoder."""
import base64
import hashlib
import struct

from Crypto.Cipher import Blowfish
from django.conf import settings


class SidEncoder(object):
    """Encoder/decoder of SIDs from IDs.

    Given an integer ID, its SID is the base32 encoded ciphertext from applying
    the Blowfish cipher using the Django SECRET_KEY as the key and the SHA-256
    hash of the model label as an initialization vector. For example, an
    integer ID of 1 may have a SID that looks like 'iw6pz4-n47rkn6'.

    Blowfish is the chosen cipher because it's generally considered the least
    insecure cipher for 64 bit blocks and also pretty fast to compute. We use
    a 64 bit block to keep the SIDs short.

    We use the model label to create an initialization vector so that the same
    numeric IDs between different models (which is common since they all start
    from 1) don't yield the same SIDs. This keeps them very likely unique so
    that searching for an SID won't include log entries from other models that
    coincidentally have the same underlying integer ID.

    Base32 is the chosen text encoding for SIDs to be safely included in
    URLs, filesystem paths, hostnames, VM names, etc. Unlike base64, base32
    avoids visually similar characters like (O vs 0) that may be misread.
    Unlike base58, the encoded text can be safely used in case-insensitive
    contexts like DNS. The encoded length is just a couple characters more than
    base64/base58 encoding.

    Finally, convert the encoded SID to lower case and split it up with a '-'
    character (not a '_' since that can't be used in hostnames) just to make
    them a little easier for human eyes to distinguish. Since lower case 'l'
    and '1' look too similar, replace 'l' with '8'.
    """

    def __init__(self, model):
        """Initialize the SidEncoder."""
        self.model = model

    def _get_cipher(self):
        model_defining_id = self.model._meta.get_field('id').model
        sha256 = hashlib.sha256()
        sha256.update(model_defining_id._meta.label.encode('UTF-8'))
        iv = sha256.digest()[-Blowfish.block_size:]
        return Blowfish.new(settings.SECRET_KEY, Blowfish.MODE_CBC, iv)

    def encode(self, pk):
        cipher = self._get_cipher()
        encrypted = cipher.encrypt(struct.pack('>q', pk))
        encoded_bytestring = base64.b32encode(encrypted)
        encoded = encoded_bytestring.decode('UTF-8')
        formatted = encoded.rstrip('=').lower().replace('l', '8')
        return formatted[:-7] + '-' + formatted[-7:]

    def decode(self, sid):
        cipher = self._get_cipher()
        formatted = sid.replace('-', '')
        encoded = formatted.replace('8', 'l').upper().ljust(16, '=')
        try:
            encrypted = base64.b32decode(encoded)
        except (OverflowError, TypeError, UnboundLocalError) as e:
            raise ValueError('Invalid SID %s (causing %s)' %
                             (repr(sid), str(e)))
        return struct.unpack('>q', cipher.decrypt(encrypted))[0]


def get_sid(obj):
    return SidEncoder(obj.__class__).encode(obj.pk)
