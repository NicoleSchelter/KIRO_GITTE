"""
Unit tests for security features.
Tests encryption, data deletion, input validation, and security middleware.
"""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.exceptions import ValidationError
from src.security.data_deletion import (
    DataDeletionError,
    DataDeletionService,
    DeletionRequest,
    DeletionScope,
)
from src.security.encryption import (
    AESEncryption,
    DecryptionError,
    EncryptionError,
    HybridEncryption,
    RSAEncryption,
    SecureStorage,
    generate_secure_token,
    hash_password,
    secure_compare,
    verify_password,
)
from src.security.middleware import SecurityMiddleware
from src.security.validation import (
    FormValidator,
    InputSanitizer,
    InputValidationError,
    InputValidator,
    check_sql_injection,
    check_xss_patterns,
    validate_and_sanitize_input,
)


class TestAESEncryption:
    """Test cases for AES encryption."""

    def test_aes_key_generation(self):
        """Test AES key generation."""
        key = AESEncryption.generate_key()
        assert len(key) == 32
        assert isinstance(key, bytes)

        # Keys should be different
        key2 = AESEncryption.generate_key()
        assert key != key2

    def test_aes_encryption_decryption(self):
        """Test AES encryption and decryption."""
        aes = AESEncryption()
        plaintext = "This is a secret message"

        # Encrypt
        encrypted = aes.encrypt(plaintext)

        assert "ciphertext" in encrypted
        assert "iv" in encrypted
        assert "tag" in encrypted
        assert encrypted["algorithm"] == "AES-256-GCM"

        # Decrypt
        decrypted = aes.decrypt(encrypted)
        assert decrypted.decode("utf-8") == plaintext

    def test_aes_encryption_bytes(self):
        """Test AES encryption with bytes input."""
        aes = AESEncryption()
        plaintext = b"Binary data \x00\x01\x02"

        encrypted = aes.encrypt(plaintext)
        decrypted = aes.decrypt(encrypted)

        assert decrypted == plaintext

    def test_aes_json_encryption(self):
        """Test AES JSON encryption."""
        aes = AESEncryption()
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        encrypted = aes.encrypt_json(data)
        decrypted = aes.decrypt_json(encrypted)

        assert decrypted == data

    def test_aes_key_derivation(self):
        """Test key derivation from password."""
        password = "strong_password"
        salt = b"random_salt_1234"

        key1 = AESEncryption.derive_key_from_password(password, salt)
        key2 = AESEncryption.derive_key_from_password(password, salt)

        assert key1 == key2  # Same password and salt should produce same key
        assert len(key1) == 32

        # Different salt should produce different key
        key3 = AESEncryption.derive_key_from_password(password, b"different_salt12")
        assert key1 != key3

    def test_aes_invalid_key_length(self):
        """Test AES with invalid key length."""
        with pytest.raises(EncryptionError):
            AESEncryption(b"short_key")

    def test_aes_decryption_failure(self):
        """Test AES decryption with corrupted data."""
        aes = AESEncryption()

        # Corrupt the ciphertext
        encrypted = aes.encrypt("test")
        encrypted["ciphertext"] = "corrupted_data"

        with pytest.raises(DecryptionError):
            aes.decrypt(encrypted)


class TestRSAEncryption:
    """Test cases for RSA encryption."""

    def test_rsa_key_generation(self):
        """Test RSA key generation."""
        rsa = RSAEncryption()

        assert rsa.private_key is not None
        assert rsa.public_key is not None

        # Test key serialization
        private_pem = rsa.get_private_key_pem()
        public_pem = rsa.get_public_key_pem()

        assert b"BEGIN PRIVATE KEY" in private_pem
        assert b"BEGIN PUBLIC KEY" in public_pem

    def test_rsa_encryption_decryption(self):
        """Test RSA encryption and decryption."""
        rsa = RSAEncryption()
        plaintext = "Short message"

        # Encrypt with public key
        encrypted = rsa.encrypt(plaintext)
        assert isinstance(encrypted, str)

        # Decrypt with private key
        decrypted = rsa.decrypt(encrypted)
        assert decrypted.decode("utf-8") == plaintext

    def test_rsa_large_data_error(self):
        """Test RSA encryption with data too large."""
        rsa = RSAEncryption()
        large_data = "x" * 200  # Too large for RSA

        with pytest.raises(EncryptionError):
            rsa.encrypt(large_data)

    def test_rsa_public_key_only(self):
        """Test RSA with public key only."""
        rsa1 = RSAEncryption()
        public_pem = rsa1.get_public_key_pem()

        # Create new instance with public key only
        rsa2 = RSAEncryption(public_key=public_pem)

        # Should be able to encrypt
        encrypted = rsa2.encrypt("test")

        # Should not be able to decrypt
        with pytest.raises(DecryptionError):
            rsa2.decrypt(encrypted)


class TestHybridEncryption:
    """Test cases for hybrid encryption."""

    def test_hybrid_encryption(self):
        """Test hybrid encryption with large data."""
        rsa = RSAEncryption()
        hybrid = HybridEncryption(rsa)

        # Large data that wouldn't fit in RSA
        large_data = "This is a very long message that exceeds RSA encryption limits. " * 10

        # Encrypt
        encrypted_package = hybrid.encrypt(large_data)

        assert "encrypted_data" in encrypted_package
        assert "encrypted_key" in encrypted_package
        assert encrypted_package["algorithm"] == "RSA+AES-256-GCM"

        # Decrypt
        decrypted = hybrid.decrypt(encrypted_package)
        assert decrypted.decode("utf-8") == large_data


class TestSecureStorage:
    """Test cases for secure storage."""

    def test_secure_storage(self):
        """Test secure data storage and retrieval."""
        storage = SecureStorage()

        data = {"sensitive": "information", "user_id": "12345"}
        identifier = "test_data"

        # Store data
        token = storage.store_sensitive_data(data, identifier)
        assert isinstance(token, str)

        # Retrieve data
        retrieved = storage.retrieve_sensitive_data(token)
        assert retrieved == data

    def test_secure_storage_invalid_token(self):
        """Test secure storage with invalid token."""
        storage = SecureStorage()

        with pytest.raises(DecryptionError):
            storage.retrieve_sensitive_data("invalid_token")


class TestPasswordHashing:
    """Test cases for password hashing."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "secure_password123"

        # Hash password
        hash_data = hash_password(password)

        assert "hash" in hash_data
        assert "salt" in hash_data
        assert hash_data["algorithm"] == "PBKDF2-SHA256"
        assert hash_data["iterations"] == 100000

        # Verify correct password
        assert verify_password(password, hash_data["hash"], hash_data["salt"])

        # Verify incorrect password
        assert not verify_password("wrong_password", hash_data["hash"], hash_data["salt"])

    def test_password_hashing_with_salt(self):
        """Test password hashing with provided salt."""
        password = "test_password"
        salt = b"custom_salt_1234"

        hash_data = hash_password(password, salt)

        # Same password and salt should produce same hash
        hash_data2 = hash_password(password, salt)
        assert hash_data["hash"] == hash_data2["hash"]


class TestSecurityUtilities:
    """Test cases for security utilities."""

    def test_secure_token_generation(self):
        """Test secure token generation."""
        token1 = generate_secure_token()
        token2 = generate_secure_token()

        assert token1 != token2
        assert len(token1) > 0
        assert isinstance(token1, str)

        # Test custom length
        long_token = generate_secure_token(64)
        assert len(long_token) > len(token1)

    def test_secure_compare(self):
        """Test timing-safe string comparison."""
        string1 = "secret_value"
        string2 = "secret_value"
        string3 = "different_value"

        assert secure_compare(string1, string2)
        assert not secure_compare(string1, string3)


class TestDataDeletionService:
    """Test cases for data deletion service."""

    @pytest.fixture
    def deletion_service(self):
        """Data deletion service for testing."""
        return DataDeletionService()

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing."""
        return uuid4()

    def test_deletion_request_creation(self, deletion_service, sample_user_id):
        """Test creation of deletion request."""
        with patch("src.security.data_deletion.get_session") as mock_session:
            # Mock database session and user query
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_user = Mock()
            mock_user.id = sample_user_id
            mock_db.query.return_value.filter.return_value.first.return_value = mock_user

            request_id = deletion_service.request_data_deletion(
                user_id=sample_user_id,
                scope=DeletionScope.USER_DATA,
                requested_by=sample_user_id,
                reason="User requested deletion",
            )

            assert isinstance(request_id, str)
            assert len(deletion_service.deletion_requests) == 1

    def test_deletion_request_invalid_user(self, deletion_service):
        """Test deletion request for non-existent user."""
        invalid_user_id = uuid4()

        with patch("src.security.data_deletion.get_session") as mock_session:
            # Mock database session with no user found
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            with pytest.raises(DataDeletionError):
                deletion_service.request_data_deletion(
                    user_id=invalid_user_id,
                    scope=DeletionScope.USER_DATA,
                    requested_by=invalid_user_id,
                    reason="Test",
                )

    def test_deletion_status_tracking(self, deletion_service, sample_user_id):
        """Test deletion status tracking."""
        # Create a mock deletion request
        request = DeletionRequest(
            user_id=sample_user_id,
            scope=DeletionScope.USER_DATA,
            requested_at=datetime.now(),
            requested_by=sample_user_id,
            reason="Test deletion",
        )

        deletion_service.deletion_requests.append(request)

        # Get status
        status = deletion_service.get_deletion_status(sample_user_id)

        assert len(status) == 1
        assert status[0]["user_id"] == str(sample_user_id)
        assert status[0]["scope"] == DeletionScope.USER_DATA.value

    def test_compliance_report(self, deletion_service):
        """Test compliance report generation."""
        report = deletion_service.get_compliance_report()

        assert "total_requests" in report
        assert "completed_requests" in report
        assert "compliance_rate" in report
        assert "report_generated_at" in report


class TestInputValidator:
    """Test cases for input validation."""

    def test_validate_required(self):
        """Test required field validation."""
        # Valid values
        assert InputValidator.validate_required("test", "field") == "test"
        assert InputValidator.validate_required(123, "field") == 123

        # Invalid values
        with pytest.raises(InputValidationError):
            InputValidator.validate_required(None, "field")

        with pytest.raises(InputValidationError):
            InputValidator.validate_required("", "field")

        with pytest.raises(InputValidationError):
            InputValidator.validate_required("   ", "field")

    def test_validate_string(self):
        """Test string validation."""
        # Valid string
        result = InputValidator.validate_string("test", "field", min_length=2, max_length=10)
        assert result == "test"

        # Too short
        with pytest.raises(InputValidationError):
            InputValidator.validate_string("a", "field", min_length=2)

        # Too long
        with pytest.raises(InputValidationError):
            InputValidator.validate_string("very_long_string", "field", max_length=5)

        # Pattern validation
        pattern = InputValidator.PATTERNS["alphanumeric"]
        assert InputValidator.validate_string("abc123", "field", pattern=pattern) == "abc123"

        with pytest.raises(InputValidationError):
            InputValidator.validate_string("abc-123", "field", pattern=pattern)

        # Allowed values
        allowed = ["option1", "option2"]
        assert (
            InputValidator.validate_string("option1", "field", allowed_values=allowed) == "option1"
        )

        with pytest.raises(InputValidationError):
            InputValidator.validate_string("option3", "field", allowed_values=allowed)

    def test_validate_email(self):
        """Test email validation."""
        # Valid emails
        assert InputValidator.validate_email("test@example.com") == "test@example.com"
        assert (
            InputValidator.validate_email("user.name+tag@domain.co.uk")
            == "user.name+tag@domain.co.uk"
        )

        # Invalid emails
        with pytest.raises(InputValidationError):
            InputValidator.validate_email("invalid_email")

        with pytest.raises(InputValidationError):
            InputValidator.validate_email("@domain.com")

        with pytest.raises(InputValidationError):
            InputValidator.validate_email("user@")

    def test_validate_username(self):
        """Test username validation."""
        # Valid usernames
        assert InputValidator.validate_username("user123") == "user123"
        assert InputValidator.validate_username("test_user") == "test_user"
        assert InputValidator.validate_username("user-name") == "user-name"

        # Invalid usernames
        with pytest.raises(InputValidationError):
            InputValidator.validate_username("ab")  # Too short

        with pytest.raises(InputValidationError):
            InputValidator.validate_username("user@name")  # Invalid character

        with pytest.raises(InputValidationError):
            InputValidator.validate_username("a" * 31)  # Too long

    def test_validate_password(self):
        """Test password validation."""
        # Valid password
        valid_password = "StrongPass123!"
        assert InputValidator.validate_password(valid_password) == valid_password

        # Too short
        with pytest.raises(InputValidationError):
            InputValidator.validate_password("Short1!")

        # Missing uppercase
        with pytest.raises(InputValidationError):
            InputValidator.validate_password("lowercase123!")

        # Missing lowercase
        with pytest.raises(InputValidationError):
            InputValidator.validate_password("UPPERCASE123!")

        # Missing digit
        with pytest.raises(InputValidationError):
            InputValidator.validate_password("NoDigits!")

        # Missing special character
        with pytest.raises(InputValidationError):
            InputValidator.validate_password("NoSpecial123")

    def test_validate_integer(self):
        """Test integer validation."""
        # Valid integers
        assert InputValidator.validate_integer(42, "field") == 42
        assert InputValidator.validate_integer("123", "field") == 123

        # Range validation
        assert InputValidator.validate_integer(5, "field", min_value=1, max_value=10) == 5

        with pytest.raises(InputValidationError):
            InputValidator.validate_integer(0, "field", min_value=1)

        with pytest.raises(InputValidationError):
            InputValidator.validate_integer(11, "field", max_value=10)

        # Invalid input
        with pytest.raises(InputValidationError):
            InputValidator.validate_integer("not_a_number", "field")

    def test_validate_boolean(self):
        """Test boolean validation."""
        # Valid booleans
        assert InputValidator.validate_boolean(True, "field") is True
        assert InputValidator.validate_boolean(False, "field") is False
        assert InputValidator.validate_boolean("true", "field") is True
        assert InputValidator.validate_boolean("false", "field") is False
        assert InputValidator.validate_boolean("1", "field") is True
        assert InputValidator.validate_boolean("0", "field") is False

        # Invalid input
        with pytest.raises(InputValidationError):
            InputValidator.validate_boolean("maybe", "field")

    def test_validate_url(self):
        """Test URL validation."""
        # Valid URLs
        assert InputValidator.validate_url("https://example.com") == "https://example.com"
        assert InputValidator.validate_url("http://test.org/path") == "http://test.org/path"

        # Invalid URLs
        with pytest.raises(InputValidationError):
            InputValidator.validate_url("not_a_url")

        with pytest.raises(InputValidationError):
            InputValidator.validate_url("ftp://example.com")  # Wrong scheme

        with pytest.raises(InputValidationError):
            InputValidator.validate_url("https://")  # No domain


class TestInputSanitizer:
    """Test cases for input sanitization."""

    def test_sanitize_html(self):
        """Test HTML sanitization."""
        # Safe HTML
        safe_html = "<p>This is <strong>safe</strong> content.</p>"
        result = InputSanitizer.sanitize_html(safe_html)
        assert "<p>" in result
        assert "<strong>" in result

        # Dangerous HTML
        dangerous_html = "<script>alert('xss')</script><p>Content</p>"
        result = InputSanitizer.sanitize_html(dangerous_html)
        assert "<script>" not in result
        assert "<p>Content</p>" in result

        # Custom allowed tags
        html = "<div><p>Content</p></div>"
        result = InputSanitizer.sanitize_html(html, allowed_tags=["p"])
        assert "<div>" not in result
        assert "<p>Content</p>" in result

    def test_sanitize_text(self):
        """Test text sanitization."""
        # Normal text
        text = "Normal text content"
        assert InputSanitizer.sanitize_text(text) == text

        # Text with control characters
        text_with_control = "Text\x00with\x08control\x1fchars"
        result = InputSanitizer.sanitize_text(text_with_control)
        assert "\x00" not in result
        assert "\x08" not in result
        assert "\x1f" not in result

        # Text with excessive whitespace
        messy_text = "  Multiple   spaces   and\n\n\nnewlines  "
        result = InputSanitizer.sanitize_text(messy_text)
        assert result == "Multiple spaces and newlines"

        # Length limiting
        long_text = "a" * 100
        result = InputSanitizer.sanitize_text(long_text, max_length=10)
        assert len(result) == 10

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Normal filename
        assert InputSanitizer.sanitize_filename("document.pdf") == "document.pdf"

        # Dangerous characters
        dangerous = "../../etc/passwd"
        result = InputSanitizer.sanitize_filename(dangerous)
        assert "../" not in result

        # Reserved names
        assert InputSanitizer.sanitize_filename("CON.txt").startswith("file_")
        assert InputSanitizer.sanitize_filename("PRN.doc").startswith("file_")

        # Empty or invalid
        assert InputSanitizer.sanitize_filename("") == "unnamed_file"
        assert InputSanitizer.sanitize_filename(".") == "unnamed_file"

    def test_sanitize_url(self):
        """Test URL sanitization."""
        # Valid URLs
        assert InputSanitizer.sanitize_url("https://example.com") == "https://example.com"
        assert InputSanitizer.sanitize_url("http://test.org/path?q=1") == "http://test.org/path?q=1"

        # Invalid schemes
        assert InputSanitizer.sanitize_url("javascript:alert('xss')") == ""
        assert InputSanitizer.sanitize_url("ftp://example.com") == ""

        # Malformed URLs
        assert InputSanitizer.sanitize_url("not_a_url") == ""


class TestSecurityChecks:
    """Test cases for security pattern detection."""

    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        # Safe inputs
        assert not check_sql_injection("normal text")
        assert not check_sql_injection("user@example.com")

        # SQL injection patterns
        assert check_sql_injection("'; DROP TABLE users; --")
        assert check_sql_injection("1' OR '1'='1")
        assert check_sql_injection("UNION SELECT * FROM passwords")
        assert check_sql_injection("admin'--")

    def test_xss_detection(self):
        """Test XSS pattern detection."""
        # Safe inputs
        assert not check_xss_patterns("normal text content")
        assert not check_xss_patterns("<p>Safe HTML</p>")

        # XSS patterns
        assert check_xss_patterns("<script>alert('xss')</script>")
        assert check_xss_patterns("javascript:alert('xss')")
        assert check_xss_patterns("<img onload='alert(1)'>")
        assert check_xss_patterns("<iframe src='evil.com'></iframe>")


class TestFormValidator:
    """Test cases for form validation."""

    def test_form_validation_success(self):
        """Test successful form validation."""
        validator = FormValidator()

        validator.validate_field("username", "testuser", InputValidator.validate_username)
        validator.validate_field("email", "test@example.com", InputValidator.validate_email)

        assert validator.is_valid()

        data = validator.get_validated_data()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_form_validation_errors(self):
        """Test form validation with errors."""
        validator = FormValidator()

        validator.validate_field("username", "ab", InputValidator.validate_username)  # Too short
        validator.validate_field("email", "invalid", InputValidator.validate_email)  # Invalid email

        assert not validator.is_valid()

        errors = validator.get_errors()
        assert "username" in errors
        assert "email" in errors

        with pytest.raises(ValidationError):
            validator.get_validated_data()

    def test_validate_and_sanitize_input(self):
        """Test combined validation and sanitization."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "description": "  Some text with   extra spaces  ",
        }

        rules = {
            "username": InputValidator.validate_username,
            "email": InputValidator.validate_email,
            "description": lambda x, f: InputValidator.validate_string(x, f, max_length=100),
        }

        result = validate_and_sanitize_input(data, rules, sanitize=True)

        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        assert result["description"] == "Some text with extra spaces"  # Sanitized


class TestSecurityMiddleware:
    """Test cases for security middleware."""

    @pytest.fixture
    def middleware(self):
        """Security middleware for testing."""
        return SecurityMiddleware()

    def test_csrf_token_generation(self, middleware):
        """Test CSRF token generation and validation."""
        user_id = "test_user"

        # Generate token
        token = middleware.generate_csrf_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

        # Validate token
        assert middleware.validate_csrf_token(token, user_id)

        # Token should be one-time use
        assert not middleware.validate_csrf_token(token, user_id)

    def test_csrf_token_user_mismatch(self, middleware):
        """Test CSRF token validation with wrong user."""
        token = middleware.generate_csrf_token("user1")

        # Should fail with different user
        assert not middleware.validate_csrf_token(token, "user2")

    def test_csrf_token_expiration(self, middleware):
        """Test CSRF token expiration."""
        # Mock time to simulate expiration
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000
            token = middleware.generate_csrf_token("user")

            # Token should be valid immediately
            assert middleware.validate_csrf_token(token, "user")

            # Simulate time passing beyond expiration
            mock_time.return_value = 1000 + middleware.csrf_token_lifetime + 1

            # Token should be expired
            assert not middleware.validate_csrf_token(token, "user")

    def test_rate_limiting(self, middleware):
        """Test rate limiting functionality."""
        identifier = "test_user"

        # Should allow requests within limit
        for _i in range(middleware.rate_limit_max_requests):
            assert middleware.check_rate_limit(identifier)

        # Should block when limit exceeded
        assert not middleware.check_rate_limit(identifier)

    def test_suspicious_activity_detection(self, middleware):
        """Test suspicious activity detection."""
        # Normal request
        normal_request = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "path": "/dashboard",
            "params": {"page": "1"},
            "ip_address": "192.168.1.1",
        }
        assert not middleware.detect_suspicious_activity(normal_request)

        # Suspicious user agent
        suspicious_request = {
            "user_agent": "sqlmap/1.0",
            "path": "/dashboard",
            "params": {},
            "ip_address": "192.168.1.2",
        }
        assert middleware.detect_suspicious_activity(suspicious_request)

        # Suspicious path
        suspicious_path_request = {
            "user_agent": "Mozilla/5.0",
            "path": "/admin/config",
            "params": {},
            "ip_address": "192.168.1.3",
        }
        assert middleware.detect_suspicious_activity(suspicious_path_request)

        # SQL injection in parameters
        sql_injection_request = {
            "user_agent": "Mozilla/5.0",
            "path": "/search",
            "params": {"q": "'; DROP TABLE users; --"},
            "ip_address": "192.168.1.4",
        }
        assert middleware.detect_suspicious_activity(sql_injection_request)

    def test_ip_blocking(self, middleware):
        """Test IP blocking functionality."""
        ip_address = "192.168.1.100"

        # IP should not be blocked initially
        assert not middleware.is_ip_blocked(ip_address)

        # Block IP
        middleware.block_ip(ip_address, "Suspicious activity")
        assert middleware.is_ip_blocked(ip_address)

        # Unblock IP
        middleware.unblock_ip(ip_address)
        assert not middleware.is_ip_blocked(ip_address)

    def test_security_headers(self, middleware):
        """Test security headers generation."""
        headers = middleware.get_security_headers()

        # Check for important security headers
        assert "X-Frame-Options" in headers
        assert "X-Content-Type-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Content-Security-Policy" in headers
        assert "Strict-Transport-Security" in headers

        # Check header values
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "default-src" in headers["Content-Security-Policy"]
