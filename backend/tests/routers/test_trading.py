import pytest

from app.models.trading import StrategyActivation, ActivationStatus
from tests.conftest import user_auth_header


class TestActivateStrategy:
    async def test_activate_success(self, client, test_user, user_token, test_strategy, test_account):
        r = await client.post(
            "/trading/activate",
            json={
                "strategy_id": test_strategy.id,
                "account_id": test_account.id,
                "tickers": ["005930", "000660"],
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["strategy_id"] == test_strategy.id
        assert data["status"] == "ACTIVE"

    async def test_activate_strategy_not_found(self, client, test_user, user_token, test_account):
        r = await client.post(
            "/trading/activate",
            json={"strategy_id": 9999, "account_id": test_account.id, "tickers": ["005930"]},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_activate_account_not_found(self, client, test_user, user_token, test_strategy):
        r = await client.post(
            "/trading/activate",
            json={"strategy_id": test_strategy.id, "account_id": 9999, "tickers": ["005930"]},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_activate_duplicate_raises_400(
        self, client, test_user, user_token, test_strategy, test_account
    ):
        # First activation
        await client.post(
            "/trading/activate",
            json={
                "strategy_id": test_strategy.id,
                "account_id": test_account.id,
                "tickers": ["005930"],
            },
            headers=user_auth_header(user_token),
        )
        # Second activation of same strategy+account
        r = await client.post(
            "/trading/activate",
            json={
                "strategy_id": test_strategy.id,
                "account_id": test_account.id,
                "tickers": ["005930"],
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 400

    async def test_activate_requires_auth(self, client):
        r = await client.post(
            "/trading/activate",
            json={"strategy_id": 1, "account_id": 1, "tickers": ["005930"]},
        )
        assert r.status_code == 401


class TestDeactivateStrategy:
    async def test_deactivate_success(
        self, client, test_user, user_token, test_strategy, test_account, db_session
    ):
        # Create activation
        activation = StrategyActivation(
            strategy_id=test_strategy.id,
            account_id=test_account.id,
            tickers=["005930"],
            status=ActivationStatus.ACTIVE,
        )
        db_session.add(activation)
        await db_session.commit()
        await db_session.refresh(activation)

        r = await client.post(
            "/trading/deactivate",
            json={"activation_id": activation.id},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        assert r.json()["message"] == "Strategy deactivated"

    async def test_deactivate_not_found(self, client, test_user, user_token):
        r = await client.post(
            "/trading/deactivate",
            json={"activation_id": 9999},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404


class TestListActive:
    async def test_list_active_empty(self, client, test_user, user_token):
        r = await client.get("/trading/active", headers=user_auth_header(user_token))
        assert r.status_code == 200
        assert r.json() == []

    async def test_list_active_with_activation(
        self, client, test_user, user_token, test_strategy, test_account, db_session
    ):
        activation = StrategyActivation(
            strategy_id=test_strategy.id,
            account_id=test_account.id,
            tickers=["005930"],
            status=ActivationStatus.ACTIVE,
        )
        db_session.add(activation)
        await db_session.commit()

        r = await client.get("/trading/active", headers=user_auth_header(user_token))
        assert r.status_code == 200
        assert len(r.json()) == 1


class TestNotificationSettings:
    async def test_get_default_settings(self, client, test_user, user_token):
        r = await client.get(
            "/trading/settings/notifications",
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["trade_signal"] is True
        assert data["auto_sell_on_crash"] is False

    async def test_update_settings(self, client, test_user, user_token):
        r = await client.put(
            "/trading/settings/notifications",
            json={
                "trade_signal": False,
                "order_filled": True,
                "daily_report": False,
                "anomaly_alert": True,
                "weekly_report": True,
                "crash_threshold": -0.08,
                "portfolio_crash_threshold": -0.15,
                "auto_sell_on_crash": True,
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["trade_signal"] is False
        assert data["auto_sell_on_crash"] is True

    async def test_get_settings_after_update(self, client, test_user, user_token):
        await client.put(
            "/trading/settings/notifications",
            json={
                "trade_signal": False,
                "order_filled": True,
                "daily_report": True,
                "anomaly_alert": True,
                "weekly_report": True,
                "crash_threshold": -0.08,
                "portfolio_crash_threshold": -0.15,
                "auto_sell_on_crash": True,
            },
            headers=user_auth_header(user_token),
        )
        r = await client.get(
            "/trading/settings/notifications",
            headers=user_auth_header(user_token),
        )
        assert r.json()["trade_signal"] is False
        assert r.json()["weekly_report"] is True
