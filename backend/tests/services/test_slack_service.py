import pytest
from unittest.mock import patch, MagicMock

from app.services.slack_service import SlackService


class TestSlackService:
    def test_init_with_webhook_url(self):
        svc = SlackService(webhook_url="https://hooks.slack.com/test")
        assert svc.client is not None

    @patch("app.services.slack_service.get_settings")
    def test_init_without_url_uses_settings(self, mock_settings):
        mock_settings.return_value = MagicMock(SLACK_WEBHOOK_URL="https://hooks.slack.com/from-settings")
        svc = SlackService()
        assert svc.client is not None

    @patch("app.services.slack_service.get_settings")
    def test_init_empty_url_no_client(self, mock_settings):
        mock_settings.return_value = MagicMock(SLACK_WEBHOOK_URL="")
        svc = SlackService()
        assert svc.client is None

    @patch("app.services.slack_service.get_settings")
    def test_send_skipped_when_no_client(self, mock_settings):
        mock_settings.return_value = MagicMock(SLACK_WEBHOOK_URL="")
        svc = SlackService()
        # Should not raise
        svc._send("test message")

    def test_send_trade_signal(self):
        svc = SlackService(webhook_url="https://hooks.slack.com/test")
        svc.client = MagicMock()
        svc.send_trade_signal("005930", "BUY", 70000.0, "MA Cross")
        svc.client.send.assert_called_once()
        call_text = svc.client.send.call_args[1]["text"]
        assert "005930" in call_text
        assert "BUY" in call_text

    def test_send_daily_report(self):
        svc = SlackService(webhook_url="https://hooks.slack.com/test")
        svc.client = MagicMock()
        svc.send_daily_report({"daily_pnl": 50000, "total_value": 10_050_000, "position_count": 3, "active_strategies": 2})
        svc.client.send.assert_called_once()

    def test_send_anomaly_alert(self):
        svc = SlackService(webhook_url="https://hooks.slack.com/test")
        svc.client = MagicMock()
        svc.send_anomaly_alert("005930", -6.5, "Alert only")
        svc.client.send.assert_called_once()
        call_text = svc.client.send.call_args[1]["text"]
        assert "Anomaly" in call_text

    def test_send_security_alert(self):
        svc = SlackService(webhook_url="https://hooks.slack.com/test")
        svc.client = MagicMock()
        svc.send_security_alert("LOCKOUT", "test@test.com", "1.2.3.4")
        svc.client.send.assert_called_once()

    def test_send_weekly_report(self):
        svc = SlackService(webhook_url="https://hooks.slack.com/test")
        svc.client = MagicMock()
        svc.send_weekly_report({"weekly_return": 2.5, "total_value": 10_250_000, "trades_count": 5})
        svc.client.send.assert_called_once()

    def test_send_handles_exception(self):
        svc = SlackService(webhook_url="https://hooks.slack.com/test")
        svc.client = MagicMock()
        svc.client.send.side_effect = Exception("Network error")
        # Should not raise, just log
        svc._send("test")
