import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt
from unittest.mock import MagicMock

from app.deps import get_current_user, get_admin_user
from app.models.user import User, UserRole


class TestGetCurrentUser:
    async def test_valid_token_returns_user(self, db_session, test_user, settings):
        token = jwt.encode(
            {"sub": str(test_user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        user = await get_current_user(token, db_session, settings)
        assert user.id == test_user.id
        assert user.email == test_user.email

    async def test_expired_token_raises_401(self, db_session, test_user, settings):
        from fastapi import HTTPException

        token = jwt.encode(
            {"sub": str(test_user.id), "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token, db_session, settings)
        assert exc_info.value.status_code == 401

    async def test_invalid_token_raises_401(self, db_session, settings):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("not.a.valid.token", db_session, settings)
        assert exc_info.value.status_code == 401

    async def test_missing_sub_raises_401(self, db_session, settings):
        from fastapi import HTTPException

        token = jwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token, db_session, settings)
        assert exc_info.value.status_code == 401

    async def test_nonexistent_user_raises_401(self, db_session, settings):
        from fastapi import HTTPException

        token = jwt.encode(
            {"sub": "99999", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token, db_session, settings)
        assert exc_info.value.status_code == 401

    async def test_inactive_user_raises_401(self, db_session, test_user, settings):
        from fastapi import HTTPException

        test_user.is_active = False
        await db_session.commit()

        token = jwt.encode(
            {"sub": str(test_user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token, db_session, settings)
        assert exc_info.value.status_code == 401

    async def test_locked_user_raises_403(self, db_session, test_user, settings):
        from fastapi import HTTPException

        test_user.is_locked = True
        await db_session.commit()

        token = jwt.encode(
            {"sub": str(test_user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token, db_session, settings)
        assert exc_info.value.status_code == 403


class TestGetAdminUser:
    async def test_admin_user_passes(self, test_admin):
        result = await get_admin_user(test_admin)
        assert result.role == UserRole.ADMIN

    async def test_regular_user_raises_403(self, test_user):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(test_user)
        assert exc_info.value.status_code == 403
