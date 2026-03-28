import pytest

from tests.conftest import user_auth_header


class TestRegister:
    async def test_register_success(self, client):
        r = await client.post(
            "/auth/register",
            json={"email": "new@test.com", "password": "ValidPass123!", "name": "New User"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "new@test.com"
        assert data["name"] == "New User"

    async def test_register_duplicate_email(self, client, test_user):
        r = await client.post(
            "/auth/register",
            json={"email": test_user.email, "password": "ValidPass123!", "name": "Dup"},
        )
        assert r.status_code == 400

    async def test_register_short_password(self, client):
        r = await client.post(
            "/auth/register",
            json={"email": "x@test.com", "password": "short", "name": "User"},
        )
        assert r.status_code == 422

    async def test_register_invalid_email(self, client):
        r = await client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "ValidPass123!", "name": "User"},
        )
        assert r.status_code == 422

    async def test_register_empty_name(self, client):
        r = await client.post(
            "/auth/register",
            json={"email": "x@test.com", "password": "ValidPass123!", "name": ""},
        )
        assert r.status_code == 422


class TestLogin:
    async def test_login_success(self, client, test_user):
        r = await client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "TestPassword123!"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client, test_user):
        r = await client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "WrongPass!"},
        )
        assert r.status_code == 401

    async def test_login_nonexistent_email(self, client):
        r = await client.post(
            "/auth/login",
            json={"email": "nobody@test.com", "password": "Pass!"},
        )
        assert r.status_code == 401

    async def test_login_lockout_after_5_failures(self, client, test_user):
        for _ in range(5):
            await client.post(
                "/auth/login",
                json={"email": test_user.email, "password": "wrong"},
            )
        r = await client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "TestPassword123!"},
        )
        assert r.status_code == 423


class TestRefresh:
    async def test_refresh_success(self, client, test_user):
        login_r = await client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "TestPassword123!"},
        )
        refresh_token = login_r.json()["refresh_token"]

        r = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_refresh_invalid_token(self, client):
        r = await client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert r.status_code == 401


class TestLogout:
    async def test_logout_success(self, client, test_user):
        login_r = await client.post(
            "/auth/login",
            json={"email": test_user.email, "password": "TestPassword123!"},
        )
        refresh_token = login_r.json()["refresh_token"]

        r = await client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert r.status_code == 200
        assert r.json()["message"] == "Logged out successfully"


class TestMe:
    async def test_me_success(self, client, test_user, user_token):
        r = await client.get("/auth/me", headers=user_auth_header(user_token))
        assert r.status_code == 200
        assert r.json()["email"] == test_user.email

    async def test_me_without_token(self, client):
        r = await client.get("/auth/me")
        assert r.status_code == 401

    async def test_me_with_invalid_token(self, client):
        r = await client.get("/auth/me", headers=user_auth_header("bad.token.here"))
        assert r.status_code == 401


class TestTOTP:
    async def test_totp_setup(self, client, test_user, user_token):
        r = await client.post("/auth/totp/setup", headers=user_auth_header(user_token))
        assert r.status_code == 200
        assert "qr_code_base64" in r.json()
        assert "secret" not in r.json()

    async def test_totp_setup_already_enabled(self, client, test_user, user_token, db_session):
        test_user.totp_enabled = True
        await db_session.commit()
        r = await client.post("/auth/totp/setup", headers=user_auth_header(user_token))
        assert r.status_code == 400

    async def test_totp_verify_success(self, client, test_user, user_token, db_session):
        import pyotp
        from app.services.auth_service import generate_totp_secret

        secret = generate_totp_secret()
        test_user.totp_secret = secret
        await db_session.commit()

        code = pyotp.TOTP(secret).now()
        r = await client.post(
            "/auth/totp/verify",
            json={"code": code},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200

    async def test_totp_verify_bad_code(self, client, test_user, user_token, db_session):
        from app.services.auth_service import generate_totp_secret

        test_user.totp_secret = generate_totp_secret()
        await db_session.commit()

        r = await client.post(
            "/auth/totp/verify",
            json={"code": "000000"},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 400
