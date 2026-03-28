"""
KIS 토큰 갱신 워커 테스트
refresh_kis_tokens 함수 — REAL 계정의 KIS 액세스 토큰 자동 갱신 검증
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from app.models.account import Account, AccountType
from app.workers.kis_token_refresher import encrypt_value, decrypt_value, refresh_kis_tokens


class TestEncryptDecrypt:
    """암호화/복호화 단위 테스트"""

    def test_encrypt_and_decrypt_roundtrip(self):
        """암호화 후 복호화하면 원본 값 반환"""
        original = "test-api-key-12345"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    def test_encrypt_produces_different_value(self):
        """암호화된 값은 원본과 달라야 함"""
        original = "my-secret-key"
        encrypted = encrypt_value(original)
        assert encrypted != original

    def test_encrypt_different_inputs_different_outputs(self):
        """다른 입력값은 다른 암호화 결과 생성"""
        enc1 = encrypt_value("key-one")
        enc2 = encrypt_value("key-two")
        assert enc1 != enc2


class TestRefreshKisTokens:
    """refresh_kis_tokens 통합 테스트"""

    async def test_refresh_no_real_accounts(self):
        """REAL 계정이 없으면 HTTP 호출 없이 종료"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.kis_token_refresher.async_session_factory", return_value=mock_cm):
            await refresh_kis_tokens()

        mock_session.commit.assert_awaited_once()

    async def test_refresh_success_updates_token(self):
        """REAL 계정 KIS 토큰 갱신 성공 → 토큰 업데이트"""
        # 암호화된 KIS 키 생성
        encrypted_key = encrypt_value("test-app-key")
        encrypted_secret = encrypt_value("test-app-secret")

        account = MagicMock()
        account.id = 1
        account.kis_app_key = encrypted_key
        account.kis_app_secret = encrypted_secret
        account.kis_access_token = None
        account.kis_token_expires_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [account]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        # KIS API 응답 mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new-access-token-abc123",
            "expires_in": 86400,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.workers.kis_token_refresher.async_session_factory", return_value=mock_cm):
            with patch("httpx.AsyncClient") as mock_http_cls:
                mock_http = AsyncMock()
                mock_http.post = AsyncMock(return_value=mock_response)
                mock_http_cls.return_value.__aenter__.return_value = mock_http
                await refresh_kis_tokens()

        # 계정 토큰이 업데이트되었는지 확인
        assert account.kis_access_token is not None
        assert account.kis_token_expires_at is not None
        mock_session.commit.assert_awaited_once()

    async def test_refresh_http_error_continues(self):
        """HTTP 오류 발생 시 해당 계정 건너뛰고 계속 진행"""
        encrypted_key = encrypt_value("test-app-key")
        encrypted_secret = encrypt_value("test-app-secret")

        account = MagicMock()
        account.id = 1
        account.kis_app_key = encrypted_key
        account.kis_app_secret = encrypted_secret

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [account]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.kis_token_refresher.async_session_factory", return_value=mock_cm):
            with patch("httpx.AsyncClient") as mock_http_cls:
                mock_http = AsyncMock()
                mock_http.post = AsyncMock(side_effect=Exception("Connection timeout"))
                mock_http_cls.return_value.__aenter__.return_value = mock_http
                # 예외가 외부로 전파되지 않아야 함
                await refresh_kis_tokens()

        # 오류가 있어도 commit 호출
        mock_session.commit.assert_awaited_once()

    async def test_refresh_multiple_accounts(self):
        """여러 REAL 계정의 토큰을 순차적으로 갱신"""
        encrypted_key = encrypt_value("app-key")
        encrypted_secret = encrypt_value("app-secret")

        accounts = []
        for i in range(3):
            acc = MagicMock()
            acc.id = i + 1
            acc.kis_app_key = encrypted_key
            acc.kis_app_secret = encrypted_secret
            acc.kis_access_token = None
            acc.kis_token_expires_at = None
            accounts.append(acc)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = accounts

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "new-token", "expires_in": 86400}
        mock_response.raise_for_status = MagicMock()

        with patch("app.workers.kis_token_refresher.async_session_factory", return_value=mock_cm):
            with patch("httpx.AsyncClient") as mock_http_cls:
                mock_http = AsyncMock()
                mock_http.post = AsyncMock(return_value=mock_response)
                mock_http_cls.return_value.__aenter__.return_value = mock_http
                await refresh_kis_tokens()

        # 3개 계정 모두 토큰 업데이트
        for acc in accounts:
            assert acc.kis_access_token is not None
