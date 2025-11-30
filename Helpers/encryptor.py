"""Password-based encryption and decryption helpers.

This module provides small, self‑contained utilities to encrypt and
decrypt bytes using a user‑supplied password. It is designed so that
callers can *verify* that the password is correct **before** any
decryption of the ciphertext payload is attempted.

The API is deliberately minimal and avoids external dependencies so it
can be reused in both UI and data‑layer code without pulling in
additional packages.

Security notes
--------------

This implementation uses PBKDF2‑HMAC‑SHA256 for key derivation and
AES‑GCM (via the ``cryptography`` library) for authenticated
encryption. A separate HMAC is used purely for fast "password
correctness" checks *before* attempting decryption.

Data format
-----------

All encrypted blobs produced by :func:`encrypt` have the following
binary layout::

	[ 16 bytes salt ]
	[ 32 bytes password HMAC ]
	[ 12 bytes AES-GCM nonce ]
	[ N bytes AES-GCM ciphertext || 16-byte tag ]

Only the salt and password HMAC are used to check whether a supplied
password is correct. Decryption of the ciphertext is only attempted
once this check passes. AES-GCM itself provides integrity and
authenticity for the encrypted payload.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_SALT_SIZE = 16
_KEY_SIZE = 32
_PBKDF2_ITERATIONS = 200_000
_NONCE_SIZE = 12  # Recommended size for AES-GCM


@dataclass(frozen=True)
class EncryptedBlob:
	"""Structured view of an encrypted payload.

	Callers normally won't instantiate this directly; it is used
	internally so that we can cleanly separate the *password check*
	step from the *decryption* step.
	"""

	salt: bytes
	password_hmac: bytes
	nonce: bytes
	ciphertext: bytes

	@classmethod
	def from_bytes(cls, blob: bytes) -> "EncryptedBlob":
		if len(blob) < _SALT_SIZE + 32 + _NONCE_SIZE + 16:
			raise ValueError("Encrypted blob is too short or malformed.")
		salt = blob[:_SALT_SIZE]
		password_hmac = blob[_SALT_SIZE : _SALT_SIZE + 32]
		nonce = blob[_SALT_SIZE + 32 : _SALT_SIZE + 32 + _NONCE_SIZE]
		ciphertext = blob[_SALT_SIZE + 32 + _NONCE_SIZE :]
		if not ciphertext:
			raise ValueError("Encrypted blob has no ciphertext payload.")
		return cls(salt=salt, password_hmac=password_hmac, nonce=nonce, ciphertext=ciphertext)

	def to_bytes(self) -> bytes:
		return self.salt + self.password_hmac + self.nonce + self.ciphertext


def _derive_key(password: str, salt: bytes) -> bytes:
	"""Derive a symmetric key from the given password and salt."""

	if not isinstance(password, str):
		raise TypeError("password must be a string")
	if not isinstance(salt, (bytes, bytearray)):
		raise TypeError("salt must be bytes")

	return hashlib.pbkdf2_hmac(
		"sha256",
		password.encode("utf-8"),
		salt,
		_PBKDF2_ITERATIONS,
		dklen=_KEY_SIZE,
	)


def encrypt(password: str, plaintext: bytes) -> bytes:
	"""Encrypt ``plaintext`` with ``password`` and return a bytes blob.

	The returned bytes embed everything necessary for later password
	verification and decryption. They can be stored directly or encoded
	with :func:`base64.b64encode` if a text representation is needed.
	"""

	if not isinstance(plaintext, (bytes, bytearray)):
		raise TypeError("plaintext must be bytes")

	salt = os.urandom(_SALT_SIZE)
	key = _derive_key(password, salt)
	nonce = os.urandom(_NONCE_SIZE)

	aesgcm = AESGCM(key)
	ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

	# HMAC for password correctness only (does not cover ciphertext)
	password_hmac = hmac.new(key, b"password-check", hashlib.sha256).digest()

	blob = EncryptedBlob(salt=salt, password_hmac=password_hmac, nonce=nonce, ciphertext=ciphertext)
	return blob.to_bytes()


def is_password_correct(password: str, encrypted_blob: bytes) -> bool:
	"""Return ``True`` if ``password`` matches ``encrypted_blob``.

	This function performs *only* key derivation and HMAC comparison; it
	does **not** attempt to decrypt the ciphertext. This lets callers
	cheaply ask the user to re‑enter a password without risking partial
	or incorrect decryption.
	"""

	try:
		blob = EncryptedBlob.from_bytes(encrypted_blob)
	except ValueError:
		return False

	key = _derive_key(password, blob.salt)
	expected = hmac.new(key, b"password-check", hashlib.sha256).digest()
	return hmac.compare_digest(expected, blob.password_hmac)


def decrypt(password: str, encrypted_blob: bytes) -> bytes:
	"""Decrypt ``encrypted_blob`` with ``password`` and return plaintext.

	The function first verifies that the password is correct using the
	embedded password HMAC. Only if this check passes will it attempt to
	decrypt and verify the ciphertext. A :class:`ValueError` is raised
	if the password is wrong or the blob is malformed.
	"""

	blob = EncryptedBlob.from_bytes(encrypted_blob)

	key = _derive_key(password, blob.salt)

	# First, verify password without touching ciphertext
	expected_pw = hmac.new(key, b"password-check", hashlib.sha256).digest()
	if not hmac.compare_digest(expected_pw, blob.password_hmac):
		raise ValueError("Incorrect password for encrypted data.")

	aesgcm = AESGCM(key)
	try:
		plaintext = aesgcm.decrypt(blob.nonce, blob.ciphertext, associated_data=None)
	except Exception as exc:  # InvalidTag, ValueError, etc.
		raise ValueError("Encrypted data is corrupted or has been tampered with.") from exc

	return plaintext


def encrypt_to_base64(password: str, plaintext: bytes) -> str:
	"""Convenience wrapper that returns a base64‑encoded string."""

	return base64.b64encode(encrypt(password, plaintext)).decode("ascii")


def decrypt_from_base64(password: str, data: str) -> bytes:
	"""Inverse of :func:`encrypt_to_base64` for string payloads."""

	return decrypt(password, base64.b64decode(data.encode("ascii")))


__all__ = [
	"EncryptedBlob",
	"encrypt",
	"decrypt",
	"is_password_correct",
	"encrypt_to_base64",
	"decrypt_from_base64",
]

