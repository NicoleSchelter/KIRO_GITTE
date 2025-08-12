"""
Encryption utilities for GITTE system.
Provides AES-256 encryption for data backups, exports, and sensitive data storage.
"""

import base64
import logging
from datetime import datetime
from typing import Any

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
import json
import secrets

from src.exceptions import SecurityError

logger = logging.getLogger(__name__)


class EncryptionError(SecurityError):
    """Encryption-specific error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(f"Encryption error: {message}", **kwargs)
        self.user_message = "Data encryption failed. Please try again."


class DecryptionError(SecurityError):
    """Decryption-specific error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(f"Decryption error: {message}", **kwargs)
        self.user_message = "Data decryption failed. Please check your credentials."


class AESEncryption:
    """AES-256 encryption utilities."""

    def __init__(self, key: bytes | None = None):
        """
        Initialize AES encryption.

        Args:
            key: 32-byte encryption key. If None, generates a new key.
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise EncryptionError(
                "Cryptography library not available. Install with: pip install cryptography"
            )

        if key is None:
            self.key = self.generate_key()
        else:
            if len(key) != 32:
                raise EncryptionError("AES key must be exactly 32 bytes")
            self.key = key

    @staticmethod
    def generate_key() -> bytes:
        """Generate a secure 256-bit AES key."""
        return secrets.token_bytes(32)

    @staticmethod
    def derive_key_from_password(password: str, salt: bytes) -> bytes:
        """
        Derive AES key from password using PBKDF2.

        Args:
            password: User password
            salt: Random salt (16 bytes recommended)

        Returns:
            32-byte AES key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
            backend=default_backend(),
        )
        return kdf.derive(password.encode("utf-8"))

    def encrypt(self, data: str | bytes) -> dict[str, str]:
        """
        Encrypt data using AES-256-GCM.

        Args:
            data: Data to encrypt (string or bytes)

        Returns:
            Dict containing encrypted data, IV, and tag (all base64 encoded)
        """
        try:
            # Convert string to bytes if necessary
            if isinstance(data, str):
                data = data.encode("utf-8")

            # Generate random IV
            iv = secrets.token_bytes(12)  # 96-bit IV for GCM

            # Create cipher
            cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv), backend=default_backend())
            encryptor = cipher.encryptor()

            # Encrypt data
            ciphertext = encryptor.update(data) + encryptor.finalize()

            # Return encrypted data with metadata
            return {
                "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
                "iv": base64.b64encode(iv).decode("utf-8"),
                "tag": base64.b64encode(encryptor.tag).decode("utf-8"),
                "algorithm": "AES-256-GCM",
            }

        except Exception as e:
            logger.error(f"AES encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}")

    def decrypt(self, encrypted_data: dict[str, str]) -> bytes:
        """
        Decrypt AES-256-GCM encrypted data.

        Args:
            encrypted_data: Dict containing ciphertext, IV, and tag

        Returns:
            Decrypted data as bytes
        """
        try:
            # Decode base64 data
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            iv = base64.b64decode(encrypted_data["iv"])
            tag = base64.b64decode(encrypted_data["tag"])

            # Create cipher
            cipher = Cipher(algorithms.AES(self.key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()

            # Decrypt data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            return plaintext

        except Exception as e:
            logger.error(f"AES decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt data: {e}")

    def encrypt_json(self, data: dict[str, Any]) -> dict[str, str]:
        """
        Encrypt JSON-serializable data.

        Args:
            data: Dictionary to encrypt

        Returns:
            Encrypted data dictionary
        """
        json_str = json.dumps(data, separators=(",", ":"))
        return self.encrypt(json_str)

    def decrypt_json(self, encrypted_data: dict[str, str]) -> dict[str, Any]:
        """
        Decrypt JSON data.

        Args:
            encrypted_data: Encrypted data dictionary

        Returns:
            Decrypted dictionary
        """
        decrypted_bytes = self.decrypt(encrypted_data)
        json_str = decrypted_bytes.decode("utf-8")
        return json.loads(json_str)


class RSAEncryption:
    """RSA encryption utilities for key exchange and digital signatures."""

    def __init__(self, private_key: bytes | None = None, public_key: bytes | None = None):
        """
        Initialize RSA encryption.

        Args:
            private_key: PEM-encoded private key
            public_key: PEM-encoded public key
        """
        if private_key:
            self.private_key = serialization.load_pem_private_key(
                private_key, password=None, backend=default_backend()
            )
            self.public_key = self.private_key.public_key()
        elif public_key:
            self.public_key = serialization.load_pem_public_key(
                public_key, backend=default_backend()
            )
            self.private_key = None
        else:
            # Generate new key pair
            self.private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )
            self.public_key = self.private_key.public_key()

    def get_public_key_pem(self) -> bytes:
        """Get public key in PEM format."""
        return self.public_key.serialize(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def get_private_key_pem(self) -> bytes:
        """Get private key in PEM format."""
        if not self.private_key:
            raise EncryptionError("Private key not available")

        return self.private_key.serialize(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def encrypt(self, data: str | bytes) -> str:
        """
        Encrypt data with RSA public key.

        Args:
            data: Data to encrypt

        Returns:
            Base64-encoded encrypted data
        """
        try:
            if isinstance(data, str):
                data = data.encode("utf-8")

            # RSA can only encrypt small amounts of data
            if len(data) > 190:  # Conservative limit for 2048-bit key
                raise EncryptionError("Data too large for RSA encryption (max 190 bytes)")

            encrypted = self.public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            return base64.b64encode(encrypted).decode("utf-8")

        except Exception as e:
            logger.error(f"RSA encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt with RSA: {e}")

    def decrypt(self, encrypted_data: str) -> bytes:
        """
        Decrypt RSA-encrypted data.

        Args:
            encrypted_data: Base64-encoded encrypted data

        Returns:
            Decrypted data as bytes
        """
        try:
            if not self.private_key:
                raise DecryptionError("Private key required for decryption")

            encrypted_bytes = base64.b64decode(encrypted_data)

            decrypted = self.private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            return decrypted

        except Exception as e:
            logger.error(f"RSA decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt with RSA: {e}")


class HybridEncryption:
    """Hybrid encryption combining RSA and AES for large data encryption."""

    def __init__(self, rsa_encryption: RSAEncryption):
        """
        Initialize hybrid encryption.

        Args:
            rsa_encryption: RSA encryption instance
        """
        self.rsa = rsa_encryption

    def encrypt(self, data: str | bytes) -> dict[str, str]:
        """
        Encrypt data using hybrid encryption (RSA + AES).

        Args:
            data: Data to encrypt

        Returns:
            Dict containing encrypted data and encrypted AES key
        """
        try:
            # Generate random AES key
            aes_key = AESEncryption.generate_key()
            aes = AESEncryption(aes_key)

            # Encrypt data with AES
            encrypted_data = aes.encrypt(data)

            # Encrypt AES key with RSA
            encrypted_key = self.rsa.encrypt(aes_key)

            return {
                "encrypted_data": encrypted_data,
                "encrypted_key": encrypted_key,
                "algorithm": "RSA+AES-256-GCM",
            }

        except Exception as e:
            logger.error(f"Hybrid encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt with hybrid method: {e}")

    def decrypt(self, encrypted_package: dict[str, Any]) -> bytes:
        """
        Decrypt hybrid-encrypted data.

        Args:
            encrypted_package: Dict containing encrypted data and key

        Returns:
            Decrypted data as bytes
        """
        try:
            # Decrypt AES key with RSA
            aes_key = self.rsa.decrypt(encrypted_package["encrypted_key"])
            aes = AESEncryption(aes_key)

            # Decrypt data with AES
            decrypted_data = aes.decrypt(encrypted_package["encrypted_data"])

            return decrypted_data

        except Exception as e:
            logger.error(f"Hybrid decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt with hybrid method: {e}")


class SecureStorage:
    """Secure storage utilities for sensitive data."""

    def __init__(self, encryption_key: bytes | None = None):
        """
        Initialize secure storage.

        Args:
            encryption_key: AES encryption key
        """
        self.aes = AESEncryption(encryption_key)

    def store_sensitive_data(self, data: dict[str, Any], identifier: str) -> str:
        """
        Store sensitive data securely.

        Args:
            data: Data to store
            identifier: Unique identifier for the data

        Returns:
            Storage reference/token
        """
        try:
            # Add metadata
            storage_data = {
                "identifier": identifier,
                "timestamp": datetime.now().isoformat(),
                "data": data,
            }

            # Encrypt data
            encrypted = self.aes.encrypt_json(storage_data)

            # Generate storage token
            storage_token = base64.b64encode(json.dumps(encrypted).encode("utf-8")).decode("utf-8")

            logger.info(f"Stored sensitive data with identifier: {identifier}")
            return storage_token

        except Exception as e:
            logger.error(f"Failed to store sensitive data: {e}")
            raise EncryptionError(f"Failed to store data securely: {e}")

    def retrieve_sensitive_data(self, storage_token: str) -> dict[str, Any]:
        """
        Retrieve sensitive data.

        Args:
            storage_token: Storage reference/token

        Returns:
            Decrypted data
        """
        try:
            # Decode storage token
            encrypted_json = base64.b64decode(storage_token).decode("utf-8")
            encrypted_data = json.loads(encrypted_json)

            # Decrypt data
            storage_data = self.aes.decrypt_json(encrypted_data)

            logger.info(
                f"Retrieved sensitive data with identifier: {storage_data.get('identifier')}"
            )
            return storage_data["data"]

        except Exception as e:
            logger.error(f"Failed to retrieve sensitive data: {e}")
            raise DecryptionError(f"Failed to retrieve data securely: {e}")


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: Token length in bytes

    Returns:
        Base64-encoded secure token
    """
    token_bytes = secrets.token_bytes(length)
    return base64.urlsafe_b64encode(token_bytes).decode("utf-8")


def secure_compare(a: str, b: str) -> bool:
    """
    Perform timing-safe string comparison.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal
    """
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def hash_password(password: str, salt: bytes | None = None) -> dict[str, str]:
    """
    Hash password using PBKDF2 with SHA-256.

    Args:
        password: Password to hash
        salt: Optional salt (generates random if None)

    Returns:
        Dict containing hash and salt (both base64 encoded)
    """
    if salt is None:
        salt = secrets.token_bytes(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )

    password_hash = kdf.derive(password.encode("utf-8"))

    return {
        "hash": base64.b64encode(password_hash).decode("utf-8"),
        "salt": base64.b64encode(salt).decode("utf-8"),
        "algorithm": "PBKDF2-SHA256",
        "iterations": 100000,
    }


def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """
    Verify password against stored hash.

    Args:
        password: Password to verify
        stored_hash: Base64-encoded stored hash
        stored_salt: Base64-encoded stored salt

    Returns:
        True if password is correct
    """
    try:
        salt = base64.b64decode(stored_salt)
        expected_hash = base64.b64decode(stored_hash)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )

        # This will raise an exception if the password is wrong
        kdf.verify(password.encode("utf-8"), expected_hash)
        return True

    except Exception:
        return False
