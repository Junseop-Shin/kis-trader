"""
인증 전체 흐름 통합 테스트
회원가입 -> 로그인 -> 토큰갱신 -> 로그아웃 -> 계정 잠금 -> TOTP 설정/검증
"""
import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import user_auth_header


class TestAuthFlow:
    """인증 전체 흐름 통합 테스트"""

    # --- 정상 회원가입 후 바로 로그인 가능한지 검증 ---

    async def test_register_then_login(self, client):
        """정상 회원가입 후 바로 로그인 가능한지 검증"""
        # 새 사용자 등록
        r = await client.post("/auth/register", json={
            "email": "user@test.com",
            "password": "ValidPass123!",
            "name": "TestUser"
        })
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "user@test.com"
        assert data["role"] == "USER"
        assert data["is_active"] is True

        # 같은 자격증명으로 로그인 -> 토큰 발급 확인
        r = await client.post("/auth/login", json={
            "email": "user@test.com",
            "password": "ValidPass123!"
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client):
        """이미 등록된 이메일로 회원가입 시 400 에러"""
        payload = {"email": "dup@test.com", "password": "ValidPass123!", "name": "User1"}
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 201

        # 동일 이메일로 재등록 시도
        r = await client.post("/auth/register", json=payload)
        assert r.status_code == 400

    async def test_register_short_password(self, client):
        """비밀번호가 최소 길이 미달이면 422 에러"""
        r = await client.post("/auth/register", json={
            "email": "short@test.com",
            "password": "short",
            "name": "User"
        })
        assert r.status_code == 422

    async def test_register_invalid_email(self, client):
        """이메일 형식이 잘못되면 422 에러"""
        r = await client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "ValidPass123!",
            "name": "User"
        })
        assert r.status_code == 422

    # --- 로그인 실패 / 계정 잠금 ---

    async def test_login_wrong_password(self, client, test_user):
        """잘못된 비밀번호로 로그인 시 401 에러"""
        r = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPassword!"
        })
        assert r.status_code == 401

    async def test_login_nonexistent_user(self, client):
        """존재하지 않는 사용자로 로그인 시 401 에러"""
        r = await client.post("/auth/login", json={
            "email": "nobody@test.com",
            "password": "AnyPassword123!"
        })
        assert r.status_code == 401

    async def test_account_lock_after_5_failures(self, client, test_user):
        """5회 연속 로그인 실패 시 계정이 잠기는지 검증"""
        for i in range(5):
            r = await client.post("/auth/login", json={
                "email": "test@example.com",
                "password": "WrongPassword!"
            })
            # 5번째 시도에서 ACCOUNT_LOCKED 발생 -> 423 반환
            if i < 4:
                assert r.status_code == 401
            else:
                assert r.status_code == 423

        # 잠긴 후 추가 시도 -> 423 반환
        r = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPassword!"
        })
        assert r.status_code == 423  # 이미 잠긴 계정

    # --- 토큰 갱신 ---

    async def test_refresh_token_flow(self, client, test_user):
        """로그인 후 refresh_token으로 새 토큰 발급"""
        # 먼저 로그인
        r = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        assert r.status_code == 200
        old_tokens = r.json()

        # refresh_token으로 새 토큰 발급
        r = await client.post("/auth/refresh", json={
            "refresh_token": old_tokens["refresh_token"]
        })
        assert r.status_code == 200
        new_tokens = r.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        # 새 refresh_token은 이전과 달라야 함 (회전)
        assert new_tokens["refresh_token"] != old_tokens["refresh_token"]

    async def test_refresh_token_reuse_rejected(self, client, test_user):
        """이미 사용된 refresh_token 재사용 시 거부"""
        r = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        old_refresh = r.json()["refresh_token"]

        # 첫 번째 갱신 성공
        r = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert r.status_code == 200

        # 같은 refresh_token 재사용 -> 거부
        r = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert r.status_code == 401

    async def test_refresh_with_invalid_token(self, client):
        """유효하지 않은 refresh_token 사용 시 401 에러"""
        r = await client.post("/auth/refresh", json={
            "refresh_token": "totally-invalid-token"
        })
        assert r.status_code == 401

    # --- 로그아웃 ---

    async def test_logout_revokes_refresh_token(self, client, test_user):
        """로그아웃 후 refresh_token이 무효화되는지 검증"""
        r = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })
        tokens = r.json()

        # 로그아웃
        r = await client.post("/auth/logout", json={
            "refresh_token": tokens["refresh_token"]
        })
        assert r.status_code == 200

        # 무효화된 refresh_token으로 갱신 시도 -> 실패
        r = await client.post("/auth/refresh", json={
            "refresh_token": tokens["refresh_token"]
        })
        assert r.status_code == 401

    # --- /auth/me ---

    async def test_me_with_valid_token(self, client, test_user, user_token):
        """유효한 토큰으로 /auth/me 조회 시 사용자 정보 반환"""
        r = await client.get("/auth/me", headers=user_auth_header(user_token))
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "USER"

    async def test_me_without_token(self, client):
        """토큰 없이 /auth/me 요청 시 401 에러"""
        r = await client.get("/auth/me")
        assert r.status_code == 401

    async def test_me_with_invalid_token(self, client):
        """유효하지 않은 토큰으로 /auth/me 요청 시 401 에러"""
        r = await client.get("/auth/me", headers={"Authorization": "Bearer invalid-jwt"})
        assert r.status_code == 401

    # --- TOTP ---

    async def test_totp_setup_and_verify(self, client, db_session, test_user, user_token):
        """TOTP 설정 후 올바른 코드로 활성화"""
        # TOTP 설정
        r = await client.post(
            "/auth/totp/setup",
            headers=user_auth_header(user_token)
        )
        assert r.status_code == 200
        data = r.json()
        assert "qr_code_base64" in data
        assert "secret" not in data

        # 올바른 TOTP 코드 생성 후 검증 — secret은 DB에서 읽음
        import pyotp
        from sqlalchemy import select
        from app.models.user import User
        await db_session.refresh(test_user)
        totp = pyotp.TOTP(test_user.totp_secret)
        code = totp.now()

        r = await client.post(
            "/auth/totp/verify",
            json={"code": code},
            headers=user_auth_header(user_token)
        )
        assert r.status_code == 200

    async def test_totp_setup_when_already_enabled(self, client, db_session, test_user, user_token):
        """이미 TOTP가 활성화된 상태에서 재설정 시도 -> 400 에러"""
        test_user.totp_enabled = True
        test_user.totp_secret = "JBSWY3DPEHPK3PXP"
        await db_session.commit()

        r = await client.post(
            "/auth/totp/setup",
            headers=user_auth_header(user_token)
        )
        assert r.status_code == 400

    async def test_totp_verify_with_wrong_code(self, client, test_user, user_token):
        """잘못된 TOTP 코드로 검증 시도 -> 400 에러"""
        # 먼저 TOTP 설정
        r = await client.post(
            "/auth/totp/setup",
            headers=user_auth_header(user_token)
        )
        assert r.status_code == 200

        # 잘못된 코드로 검증
        r = await client.post(
            "/auth/totp/verify",
            json={"code": "000000"},
            headers=user_auth_header(user_token)
        )
        assert r.status_code == 400
