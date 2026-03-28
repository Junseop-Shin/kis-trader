import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    register_user,
    authenticate_user,
    refresh_tokens,
    revoke_refresh_token,
    setup_totp,
    verify_totp,
    generate_totp_secret,
    generate_totp_qr,
)
from app.models.user import User, RefreshToken as RefreshTokenModel


class TestPasswordHashing:
    def test_hash_then_verify(self):
        hashed = hash_password("MySecret123!")
        assert verify_password("MySecret123!", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("MySecret123!")
        assert verify_password("WrongPass!", hashed) is False

    def test_hash_is_different_each_time(self):
        h1 = hash_password("Same")
        h2 = hash_password("Same")
        assert h1 != h2  # bcrypt uses random salt


class TestTokenCreation:
    def test_create_access_token(self, settings):
        token = create_access_token(42, settings)
        assert isinstance(token, str)
        assert len(token) > 10

    def test_create_refresh_token(self):
        token = create_refresh_token()
        assert isinstance(token, str)
        assert len(token) > 20

    def test_refresh_tokens_are_unique(self):
        t1 = create_refresh_token()
        t2 = create_refresh_token()
        assert t1 != t2


class TestRegisterUser:
    async def test_register_success(self, db_session):
        user = await register_user("new@test.com", "Pass123!", "New User", db_session)
        assert user.email == "new@test.com"
        assert user.name == "New User"
        assert user.password_hash != "Pass123!"

    async def test_register_duplicate_email_raises(self, db_session, test_user):
        with pytest.raises(ValueError, match="Email already registered"):
            await register_user(test_user.email, "Pass123!", "Dup", db_session)


class TestAuthenticateUser:
    async def test_login_success(self, db_session, test_user, settings):
        result = await authenticate_user(
            test_user.email, "TestPassword123!", None, "127.0.0.1", db_session, settings
        )
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"

    async def test_wrong_password(self, db_session, test_user, settings):
        with pytest.raises(ValueError, match="Invalid email or password"):
            await authenticate_user(
                test_user.email, "WrongPass!", None, "127.0.0.1", db_session, settings
            )

    async def test_nonexistent_email(self, db_session, settings):
        with pytest.raises(ValueError, match="Invalid email or password"):
            await authenticate_user(
                "nobody@test.com", "Pass!", None, "127.0.0.1", db_session, settings
            )

    async def test_login_increments_fail_count(self, db_session, test_user, settings):
        with pytest.raises(ValueError):
            await authenticate_user(
                test_user.email, "WrongPass!", None, "127.0.0.1", db_session, settings
            )
        await db_session.refresh(test_user)
        assert test_user.login_fail_count == 1

    async def test_lockout_after_5_failures(self, db_session, test_user, settings):
        for i in range(4):
            with pytest.raises(ValueError, match="Invalid email or password"):
                await authenticate_user(
                    test_user.email, "wrong", None, "127.0.0.1", db_session, settings
                )

        # Fifth failure should lock
        with pytest.raises(ValueError, match="ACCOUNT_LOCKED"):
            await authenticate_user(
                test_user.email, "wrong", None, "127.0.0.1", db_session, settings
            )
        await db_session.refresh(test_user)
        assert test_user.is_locked is True

    async def test_locked_user_cannot_login(self, db_session, test_user, settings):
        test_user.is_locked = True
        await db_session.commit()

        with pytest.raises(ValueError, match="ACCOUNT_LOCKED"):
            await authenticate_user(
                test_user.email, "TestPassword123!", None, "127.0.0.1", db_session, settings
            )

    async def test_inactive_user_cannot_login(self, db_session, test_user, settings):
        test_user.is_active = False
        await db_session.commit()

        with pytest.raises(ValueError, match="Invalid email or password"):
            await authenticate_user(
                test_user.email, "TestPassword123!", None, "127.0.0.1", db_session, settings
            )

    async def test_success_resets_fail_count(self, db_session, test_user, settings):
        test_user.login_fail_count = 3
        await db_session.commit()

        await authenticate_user(
            test_user.email, "TestPassword123!", None, "127.0.0.1", db_session, settings
        )
        await db_session.refresh(test_user)
        assert test_user.login_fail_count == 0

    async def test_admin_ip_check_blocks(self, db_session, test_admin, settings):
        test_admin.allowed_ips = ["10.0.0.1"]
        await db_session.commit()

        with pytest.raises(ValueError, match="IP .* not allowed"):
            await authenticate_user(
                test_admin.email, "AdminPass123!", None, "192.168.1.1", db_session, settings
            )

    async def test_admin_ip_check_allows(self, db_session, test_admin, settings):
        test_admin.allowed_ips = ["10.0.0.1"]
        await db_session.commit()

        result = await authenticate_user(
            test_admin.email, "AdminPass123!", None, "10.0.0.1", db_session, settings
        )
        assert "access_token" in result

    async def test_totp_required_when_enabled(self, db_session, test_user, settings):
        test_user.totp_enabled = True
        test_user.totp_secret = generate_totp_secret()
        await db_session.commit()

        with pytest.raises(ValueError, match="TOTP code required"):
            await authenticate_user(
                test_user.email, "TestPassword123!", None, "127.0.0.1", db_session, settings
            )

    async def test_totp_wrong_code_rejected(self, db_session, test_user, settings):
        test_user.totp_enabled = True
        test_user.totp_secret = generate_totp_secret()
        await db_session.commit()

        with pytest.raises(ValueError, match="Invalid TOTP code"):
            await authenticate_user(
                test_user.email, "TestPassword123!", "000000", "127.0.0.1", db_session, settings
            )

    async def test_totp_valid_code_succeeds(self, db_session, test_user, settings):
        import pyotp

        secret = generate_totp_secret()
        test_user.totp_enabled = True
        test_user.totp_secret = secret
        await db_session.commit()

        totp = pyotp.TOTP(secret)
        code = totp.now()
        result = await authenticate_user(
            test_user.email, "TestPassword123!", code, "127.0.0.1", db_session, settings
        )
        assert "access_token" in result


class TestRefreshTokens:
    async def test_refresh_success(self, db_session, test_user, settings):
        # First login to get tokens
        result = await authenticate_user(
            test_user.email, "TestPassword123!", None, "127.0.0.1", db_session, settings
        )
        old_refresh = result["refresh_token"]

        # Refresh
        new_tokens = await refresh_tokens(old_refresh, db_session, settings)
        assert "access_token" in new_tokens
        assert new_tokens["refresh_token"] != old_refresh

    async def test_invalid_refresh_token_raises(self, db_session, settings):
        with pytest.raises(ValueError, match="Invalid refresh token"):
            await refresh_tokens("nonexistent-token", db_session, settings)

    async def test_expired_refresh_token_raises(self, db_session, test_user, settings):
        rt = RefreshTokenModel(
            user_id=test_user.id,
            token="expired-token-xyz",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            revoked=False,
        )
        db_session.add(rt)
        await db_session.commit()

        with pytest.raises(ValueError, match="Refresh token expired"):
            await refresh_tokens("expired-token-xyz", db_session, settings)

    async def test_revoked_token_raises(self, db_session, test_user, settings):
        rt = RefreshTokenModel(
            user_id=test_user.id,
            token="revoked-token-xyz",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            revoked=True,
        )
        db_session.add(rt)
        await db_session.commit()

        with pytest.raises(ValueError, match="Invalid refresh token"):
            await refresh_tokens("revoked-token-xyz", db_session, settings)


class TestRevokeRefreshToken:
    async def test_revoke_existing(self, db_session, test_user):
        rt = RefreshTokenModel(
            user_id=test_user.id,
            token="to-revoke-xyz",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            revoked=False,
        )
        db_session.add(rt)
        await db_session.commit()

        await revoke_refresh_token("to-revoke-xyz", db_session)
        await db_session.refresh(rt)
        assert rt.revoked is True

    async def test_revoke_nonexistent_no_error(self, db_session):
        # Should not raise
        await revoke_refresh_token("no-such-token", db_session)


class TestTOTP:
    def test_generate_totp_secret(self):
        secret = generate_totp_secret()
        assert isinstance(secret, str)
        assert len(secret) >= 16

    def test_generate_totp_qr(self):
        secret = generate_totp_secret()
        qr_b64 = generate_totp_qr(secret, "test@example.com")
        assert isinstance(qr_b64, str)
        assert len(qr_b64) > 100  # base64 encoded PNG should be long

    async def test_setup_totp(self, db_session, test_user):
        result = await setup_totp(test_user, db_session)
        assert "qr_code_base64" in result
        assert "secret" not in result
        assert test_user.totp_secret is not None

    async def test_verify_totp_success(self, db_session, test_user):
        import pyotp

        secret = generate_totp_secret()
        test_user.totp_secret = secret
        await db_session.commit()

        code = pyotp.TOTP(secret).now()
        success = await verify_totp(test_user, code, db_session)
        assert success is True
        assert test_user.totp_enabled is True

    async def test_verify_totp_wrong_code(self, db_session, test_user):
        secret = generate_totp_secret()
        test_user.totp_secret = secret
        await db_session.commit()

        result = await verify_totp(test_user, "000000", db_session)
        assert result is False

    async def test_verify_totp_no_secret_raises(self, db_session, test_user):
        test_user.totp_secret = None
        await db_session.commit()

        with pytest.raises(ValueError, match="TOTP not set up"):
            await verify_totp(test_user, "123456", db_session)
