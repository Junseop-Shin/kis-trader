import pytest
from app.config import Settings, get_settings


class TestSettings:
    def test_default_values(self):
        s = Settings(
            DATABASE_URL="sqlite+aiosqlite:///:memory:",
            JWT_SECRET_KEY="test",
        )
        assert s.JWT_ALGORITHM == "HS256"
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 15
        assert s.REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert s.KIS_BASE_URL == "https://openapi.koreainvestment.com:9443"
        assert "http://localhost:3000" in s.CORS_ORIGINS

    def test_get_settings_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_get_settings_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
