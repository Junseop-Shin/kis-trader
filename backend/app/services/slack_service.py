import logging
from datetime import date

from slack_sdk.webhook import WebhookClient

from ..config import get_settings

logger = logging.getLogger(__name__)


class SlackService:
    def __init__(self, webhook_url: str | None = None):
        settings = get_settings()
        url = webhook_url or settings.SLACK_WEBHOOK_URL
        self.client = WebhookClient(url) if url else None

    def _send(self, text: str) -> None:
        if not self.client:
            logger.warning("Slack webhook not configured, skipping message")
            return
        try:
            self.client.send(text=text)
        except Exception as e:
            logger.error(f"Slack send failed: {e}")

    def send_trade_signal(self, ticker: str, action: str, price: float, strategy_name: str) -> None:
        text = (
            f"*Trade Signal*\n"
            f"Ticker: {ticker}\n"
            f"Signal: {action}\n"
            f"Price: {price:,.0f} KRW\n"
            f"Strategy: {strategy_name}"
        )
        self._send(text)

    def send_daily_report(self, account_summary: dict) -> None:
        text = (
            f"*Daily Report* ({date.today()})\n"
            f"Daily P&L: {account_summary.get('daily_pnl', 0):+,.0f} KRW\n"
            f"Total Value: {account_summary.get('total_value', 0):,.0f} KRW\n"
            f"Positions: {account_summary.get('position_count', 0)}\n"
            f"Active Strategies: {account_summary.get('active_strategies', 0)}"
        )
        self._send(text)

    def send_anomaly_alert(self, ticker: str, change_pct: float, action_taken: str) -> None:
        text = (
            f"*Anomaly Detected*\n"
            f"Ticker: {ticker}\n"
            f"Change: {change_pct:+.1f}%\n"
            f"Action: {action_taken}"
        )
        self._send(text)

    def send_security_alert(self, event: str, user_email: str, ip: str) -> None:
        text = (
            f"*Security Alert*\n"
            f"Event: {event}\n"
            f"Account: {user_email}\n"
            f"IP: {ip}"
        )
        self._send(text)

    def send_weekly_report(self, performance: dict) -> None:
        text = (
            f"*Weekly Report*\n"
            f"Weekly Return: {performance.get('weekly_return', 0):+.2f}%\n"
            f"Total Value: {performance.get('total_value', 0):,.0f} KRW\n"
            f"Trades This Week: {performance.get('trades_count', 0)}"
        )
        self._send(text)
