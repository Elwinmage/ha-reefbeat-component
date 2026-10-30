"""Payload encryption of ReefBeat MQTT messages.

AES-128-CBC with PKCS7 padding, key = the device's ``api_secret`` (16
characters), payload format ``base64(ciphertext).base64(IV)``. Ported as is
from ``reefbeat_god_mode.py``.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY_LENGTH = 16


def _key(api_secret: str) -> bytes:
    key = api_secret.encode("utf-8")
    if len(key) != KEY_LENGTH:
        raise ValueError(f"api_secret must be {KEY_LENGTH} chars, got {len(key)}")
    return key


def decrypt_payload(encrypted: str, api_secret: str) -> Any:
    """Decrypt a payload: the parsed JSON, or the text when it is not JSON."""
    parts = encrypted.strip().split(".")
    if len(parts) != 2:
        raise ValueError(f"expected 'ciphertext.iv', got {len(parts)} parts")
    ct_b64 = parts[0].rstrip("=")
    ct_b64 += "=" * ((4 - len(ct_b64) % 4) % 4)
    ciphertext = base64.b64decode(ct_b64)
    iv = base64.b64decode(parts[1])
    if len(iv) != 16:
        raise ValueError(f"IV must be 16 bytes, got {len(iv)}")
    if len(ciphertext) % 16 != 0:
        raise ValueError(f"ciphertext length {len(ciphertext)} is not a multiple of 16")

    decryptor = Cipher(algorithms.AES(_key(api_secret)), modes.CBC(iv)).decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(plaintext) + unpadder.finalize()

    text = plaintext.decode("utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def decode_plain(raw: str) -> Any:
    """A payload sent in clear: base64 of a JSON object, padded with NUL
    bytes (the ``group/`` topics: ``{"method": "post", "url": "/group/sync"}``).

    Returns the object, None when the payload is not that.
    """
    text = raw.strip()
    if not text or "." in text:
        return None
    try:
        decoded = base64.b64decode(text + "=" * ((4 - len(text) % 4) % 4))
        value = json.loads(decoded.rstrip(b"\x00").decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


def encrypt_payload(data: Any, api_secret: str) -> str:
    """Encrypt a payload the way a ReefBeat device expects it."""
    key = _key(api_secret)
    iv = os.urandom(16)
    raw = (
        data.encode("utf-8")
        if isinstance(data, str)
        else json.dumps(data, separators=(",", ":")).encode("utf-8")
    )
    padder = padding.PKCS7(128).padder()
    padded = padder.update(raw) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return (
        base64.b64encode(ciphertext).decode("ascii")
        + "."
        + base64.b64encode(iv).decode("ascii")
    )
