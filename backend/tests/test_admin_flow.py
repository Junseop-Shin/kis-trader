"""
관리자 흐름 통합 테스트
유저 관리 권한 확인, 감사 로그 기록 검증, 관리자 IP 제한
"""
import pytest

from app.models.user import User, UserRole
from tests.conftest import user_auth_header


class TestAdminFlow:
    """관리자 기능 및 권한 검증 통합 테스트"""

    async def test_admin_can_access_me(self, client, test_admin, admin_token):
        """관리자가 /auth/me에 접근 가능"""
        r = await client.get("/auth/me", headers=user_auth_header(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "ADMIN"

    async def test_regular_user_gets_403_on_admin_endpoint(
        self, client, test_user, user_token
    ):
        """일반 사용자가 관리자 종속 엔드포인트 접근 시 403 (deps.get_admin_user 검증)"""
        # deps.get_admin_user를 사용하는 라우터가 있다고 가정하여
        # 여기서는 의존성 자체를 직접 테스트
        from app.deps import get_admin_user
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(test_user)
        assert exc_info.value.status_code == 403

    async def test_admin_user_passes_admin_check(self, test_admin):
        """관리자 사용자는 admin 체크 통과"""
        from app.deps import get_admin_user

        result = await get_admin_user(test_admin)
        assert result.role == UserRole.ADMIN

    async def test_locked_user_cannot_access(self, client, db_session, test_user, user_token):
        """잠긴 사용자가 인증된 요청 시 403 에러"""
        # 사용자 잠금
        test_user.is_locked = True
        await db_session.commit()

        r = await client.get("/auth/me", headers=user_auth_header(user_token))
        assert r.status_code == 403

    async def test_inactive_user_cannot_access(self, client, db_session, test_user, user_token):
        """비활성 사용자가 인증된 요청 시 401 에러"""
        test_user.is_active = False
        await db_session.commit()

        r = await client.get("/auth/me", headers=user_auth_header(user_token))
        assert r.status_code == 401

    async def test_admin_ip_restriction(self, client, db_session, test_admin):
        """관리자 IP 제한이 설정되면 허용되지 않은 IP에서 로그인 차단"""
        test_admin.allowed_ips = ["192.168.1.100"]
        await db_session.commit()

        # IP가 testclient 기본값(testclient)이므로 차단되어야 함
        r = await client.post("/auth/login", json={
            "email": "admin@example.com",
            "password": "AdminPass123!",
        })
        assert r.status_code == 401
