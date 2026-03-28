import pytest
from unittest.mock import patch, MagicMock

from app.workers.kis_token_refresher import encrypt_value, decrypt_value


class TestEncryptDecrypt:
    @patch("app.workers.kis_token_refresher.get_settings")
    def test_encrypt_decrypt_roundtrip(self, mock_settings):
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        mock_settings.return_value = MagicMock(KIS_ENCRYPT_KEY=key)

        original = "my-secret-api-key-12345"
        encrypted = encrypt_value(original)
        assert encrypted != original

        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    @patch("app.workers.kis_token_refresher.get_settings")
    def test_encrypted_value_is_different_each_time(self, mock_settings):
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        mock_settings.return_value = MagicMock(KIS_ENCRYPT_KEY=key)

        e1 = encrypt_value("same-value")
        e2 = encrypt_value("same-value")
        # Fernet uses random IV so encrypted values differ
        assert e1 != e2
