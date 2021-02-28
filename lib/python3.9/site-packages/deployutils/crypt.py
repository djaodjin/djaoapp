# Copyright (c) 2019, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Encryption and Decryption functions
"""
from __future__ import unicode_literals
from __future__ import absolute_import

import decimal, json, logging, os, six
from base64 import b64decode, b64encode
from binascii import hexlify

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes

LOGGER = logging.getLogger(__name__)

IV_BLOCK_SIZE = 16


class JSONEncoder(json.JSONEncoder):

    def default(self, obj): #pylint: disable=method-hidden
        # parameter is called `o` in json.JSONEncoder.
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(JSONEncoder, self).default(obj)


def _log_debug(salt, key, iv_, encrypted_text, plain_text,
               passphrase=None, debug_stmt=None):
    #pylint:disable=too-many-arguments
    if six.PY2:
        hex_salt = ''.join(["%X" % ord(c) for c in salt])
    else:
        hex_salt = ''.join(["%X" % c for c in salt])
    try:
        if debug_stmt:
            LOGGER.debug('=========== %s', debug_stmt)
        else:
            LOGGER.debug('==========================================')
        LOGGER.debug('passphrase:    %s', passphrase)
        LOGGER.debug('salt:          %s', hex_salt)
        LOGGER.debug('key:           %s', hexlify(key).upper())
        LOGGER.debug('iv:            %s', hexlify(iv_).upper())
        LOGGER.debug('encrypt:       %s', encrypted_text)
        if plain_text:
            if hasattr(plain_text, 'encode'):
                plain_text.encode('utf-8')
            LOGGER.debug("plain:         '%s'", plain_text)
    except UnicodeDecodeError:
        LOGGER.debug('decryption failed')
    LOGGER.debug('*****************************************')


def _openssl_key_iv(passphrase, salt):
    """
    Returns a (key, iv) tuple that can be used in AES symmetric encryption
    from a *passphrase* (a byte or unicode string) and *salt* (a byte array).
    """
    def _openssl_kdf(req):
        if hasattr(passphrase, 'encode'):
            passwd = passphrase.encode('ascii', 'ignore')
        else:
            passwd = passphrase
        prev = b''
        while req > 0:
            digest = hashes.Hash(hashes.MD5(), backend=default_backend())
            digest.update(prev + passwd + salt)
            prev = digest.finalize()
            req -= IV_BLOCK_SIZE
            yield prev
    assert passphrase is not None
    assert salt is not None
    # AES key: 32 bytes, IV: 16 bytes
    mat = b''.join([x for x in _openssl_kdf(32 + IV_BLOCK_SIZE)])
    return mat[0:32], mat[32:32 + IV_BLOCK_SIZE]


def decrypt(source_text, passphrase, debug_stmt=None):
    """
    Returns plain text from *source_text*, a base64 AES encrypted string
    as generated with openssl.

        $ echo '_source_text_' | openssl aes-256-cbc -a -k _passphrase_ -p
        salt=...
        key=...
        iv=...
        _full_encrypted_
    """
    salt = ""
    key = b""
    iv_ = b""
    plain_text = ""
    if debug_stmt is None:
        debug_stmt = "decrypt"
    try:
        full_encrypted = b64decode(source_text)
        salt = full_encrypted[8:IV_BLOCK_SIZE]
        encrypted_text = full_encrypted[IV_BLOCK_SIZE:]
        key, iv_ = _openssl_key_iv(passphrase, salt)
        cipher = Cipher(
            algorithms.AES(key), modes.CBC(iv_), default_backend()
        ).decryptor()
        plain_text = cipher.update(encrypted_text)
        plain_text += cipher.finalize()
        # PKCS#7 padding
        if six.PY2:
            padding = ord(plain_text[-1])
        else:
            padding = plain_text[-1]
        plain_text = plain_text[:-padding]
        if hasattr(plain_text, 'decode'):
            plain_text = plain_text.decode('utf-8')
    finally:
        _log_debug(salt, key, iv_, source_text, plain_text,
            passphrase=passphrase, debug_stmt=debug_stmt)
    return plain_text


def encrypt(source_text, passphrase, debug_stmt=None):
    """
    Returns *source_text* as a base64 AES encrypted string.

    The full encrypted text is special crafted to be compatible
    with openssl. It can be decrypted with:

        $ echo _full_encypted_ | openssl aes-256-cbc -d -a -k _passphrase_ -p
        salt=...
        key=...
        iv=...
        _source_text_
    """
    if debug_stmt is None:
        debug_stmt = "encrypt"
    prefix = b'Salted__'
    salt = os.urandom(IV_BLOCK_SIZE - len(prefix))
    key, iv_ = _openssl_key_iv(passphrase, salt)
    cipher = Cipher(
        algorithms.AES(key), modes.CBC(iv_), default_backend()
    ).encryptor()

    # PKCS#7 padding
    if hasattr(source_text, 'encode'):
        source_utf8 = source_text.encode('utf-8')
    else:
        source_utf8 = str(source_text)
    padding = (IV_BLOCK_SIZE - len(source_utf8) % IV_BLOCK_SIZE)
    if six.PY2:
        padding = chr(padding) * padding
    else:
        padding = bytes([padding for _ in range(padding)])
    plain_text = source_utf8 + padding
    encrypted_text = cipher.update(plain_text) + cipher.finalize()
    full_encrypted = b64encode(prefix + salt + encrypted_text)
    _log_debug(salt, key, iv_, full_encrypted, source_text,
        passphrase=passphrase, debug_stmt=debug_stmt)
    return full_encrypted
