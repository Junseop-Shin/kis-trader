"""
알림 설정 흐름 통합 테스트
알림 설정 조회 -> 변경 -> 변경된 값 확인
"""
import pytest

from tests.conftest import user_auth_header


class TestSettingsFlow:
    """알림 설정 조회/변경 흐름 통합 테스트"""

    async def test_get_default_notification_settings(
        self, client, test_user, user_token
    ):
        """기본 알림 설정 조회 - 기본값이 반환되어야 함"""
        r = await client.get(
            "/trading/settings/notifications",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        # 기본값 확인
        assert data["trade_signal"] is True
        assert data["order_filled"] is True
        assert data["daily_report"] is True
        assert data["anomaly_alert"] is True
        assert data["weekly_report"] is False
        assert data["crash_threshold"] == -0.05
        assert data["portfolio_crash_threshold"] == -0.10
        assert data["auto_sell_on_crash"] is False

    async def test_update_notification_settings(
        self, client, test_user, user_token
    ):
        """알림 설정 변경 후 변경된 값 확인"""
        new_settings = {
            "trade_signal": False,
            "order_filled": True,
            "daily_report": False,
            "anomaly_alert": True,
            "weekly_report": True,
            "crash_threshold": -0.03,
            "portfolio_crash_threshold": -0.05,
            "auto_sell_on_crash": True,
        }
        r = await client.put(
            "/trading/settings/notifications",
            json=new_settings,
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["trade_signal"] is False
        assert data["weekly_report"] is True
        assert data["crash_threshold"] == -0.03
        assert data["auto_sell_on_crash"] is True

        # 다시 GET으로 확인 -> 저장된 값이 기본값보다 우선
        r = await client.get(
            "/trading/settings/notifications",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["trade_signal"] is False
        assert data["crash_threshold"] == -0.03

    async def test_update_settings_partial_values(
        self, client, test_user, user_token
    ):
        """일부 필드만 변경해도 다른 필드는 기본값 유지"""
        r = await client.put(
            "/trading/settings/notifications",
            json={
                "trade_signal": True,
                "order_filled": True,
                "daily_report": True,
                "anomaly_alert": True,
                "weekly_report": True,  # 이것만 변경
                "crash_threshold": -0.05,
                "portfolio_crash_threshold": -0.10,
                "auto_sell_on_crash": False,
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["weekly_report"] is True
        assert data["trade_signal"] is True  # 기본값 유지

    async def test_unauthenticated_settings_access(self, client):
        """인증 없이 알림 설정 접근 시 401 에러"""
        r = await client.get("/trading/settings/notifications")
        assert r.status_code == 401

        r = await client.put(
            "/trading/settings/notifications",
            json={"trade_signal": False},
        )
        assert r.status_code == 401
