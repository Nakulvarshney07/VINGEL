"""
Pure-stdlib drop-in for the three cryptography imports used in vault.py:
  - cryptography.fernet.Fernet / InvalidToken
  - cryptography.hazmat.primitives.hashes.SHA256  (marker class only)
  - cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC

Encryption: HMAC-SHA256 counter-mode (CTR) + HMAC-SHA256 authentication.
Key derivation: hashlib.pbkdf2_hmac (stdlib).
"""

import os
import hmac as _hmac
import hashlib
import struct
import base64


class InvalidToken(Exception):
    pass


class Fernet:
    def __init__(self, key: bytes):
        raw = base64.urlsafe_b64decode(key)
        if len(raw) != 32:
            raise ValueError("Key must decode to exactly 32 bytes.")
        self._sign_key = raw[:16]
        self._enc_key  = raw[16:]

    @staticmethod
    def generate_key() -> bytes:
        return base64.urlsafe_b64encode(os.urandom(32))

    def _keystream(self, iv: bytes, length: int) -> bytes:
        stream = bytearray()
        counter = 0
        while len(stream) < length:
            stream.extend(
                _hmac.new(self._enc_key, iv + struct.pack(">I", counter), hashlib.sha256).digest()
            )
            counter += 1
        return bytes(stream[:length])

    def encrypt(self, data: bytes) -> bytes:
        iv         = os.urandom(16)
        ks         = self._keystream(iv, len(data))
        ciphertext = bytes(a ^ b for a, b in zip(data, ks))
        mac        = _hmac.new(self._sign_key, iv + ciphertext, hashlib.sha256).digest()
        token      = iv + struct.pack(">I", len(data)) + ciphertext + mac
        return base64.urlsafe_b64encode(token)

    def decrypt(self, token: bytes) -> bytes:
        try:
            raw = base64.urlsafe_b64decode(token)
            if len(raw) < 16 + 4 + 32:
                raise InvalidToken()
            iv         = raw[:16]
            length     = struct.unpack(">I", raw[16:20])[0]
            ciphertext = raw[20 : 20 + length]
            mac        = raw[20 + length : 20 + length + 32]
            if len(mac) != 32:
                raise InvalidToken()
            expected = _hmac.new(self._sign_key, iv + ciphertext, hashlib.sha256).digest()
            if not _hmac.compare_digest(mac, expected):
                raise InvalidToken()
            ks = self._keystream(iv, length)
            return bytes(a ^ b for a, b in zip(ciphertext, ks))
        except InvalidToken:
            raise
        except Exception:
            raise InvalidToken("Decryption failed.")


class PBKDF2HMAC:
    def __init__(self, algorithm, length: int, salt: bytes, iterations: int):
        self._length     = length
        self._salt       = salt
        self._iterations = iterations

    def derive(self, key_material: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", key_material, self._salt, self._iterations, self._length
        )
