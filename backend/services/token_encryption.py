"""
Symmetric encryption for refresh tokens stored in the database.
Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography library.
The key must be a URL-safe base64-encoded 32-byte value — generate with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from cryptography.fernet import Fernet
from config import get_settings


def _fernet() -> Fernet:
    return Fernet(get_settings().encryption_key.encode())


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
