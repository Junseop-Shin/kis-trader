"""V1 init - all tables and TimescaleDB hypertables

Revision ID: 001_v1_init
Revises:
Create Date: 2026-03-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, ENUM

revision: str = "001_v1_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

    # --- Users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.Enum("USER", "ADMIN", name="userrole"), nullable=False, server_default="USER"),
        sa.Column("totp_secret", sa.String(64), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("login_fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allowed_ips", JSON(), nullable=True),
        sa.Column("notification_settings", JSON(), nullable=True),
        sa.Column("slack_webhook_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_email_active", "users", ["email", "is_active"])

    # --- Refresh Tokens ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)

    # --- Stocks ---
    op.create_table(
        "stocks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("market", sa.String(10), nullable=False),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stocks_ticker", "stocks", ["ticker"], unique=True)
    op.create_index("ix_stocks_market_sector", "stocks", ["market", "sector"])

    # --- Price Daily (TimescaleDB hypertable) ---
    op.create_table(
        "price_daily",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Integer(), nullable=False),
        sa.Column("high", sa.Integer(), nullable=False),
        sa.Column("low", sa.Integer(), nullable=False),
        sa.Column("close", sa.Integer(), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("change_pct", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "date", name="uq_price_daily_ticker_date"),
    )
    op.create_index("ix_price_daily_ticker", "price_daily", ["ticker"])
    op.execute(
        "SELECT create_hypertable('price_daily', 'date', "
        "chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE, "
        "migrate_data => TRUE);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_price_daily_ticker_date_desc ON price_daily (ticker, date DESC);")

    # --- Price Minute (TimescaleDB hypertable) ---
    op.create_table(
        "price_minute",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Integer(), nullable=False),
        sa.Column("high", sa.Integer(), nullable=False),
        sa.Column("low", sa.Integer(), nullable=False),
        sa.Column("close", sa.Integer(), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "datetime", name="uq_price_minute_ticker_datetime"),
    )
    op.create_index("ix_price_minute_ticker", "price_minute", ["ticker"])
    op.execute(
        "SELECT create_hypertable('price_minute', 'datetime', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE, "
        "migrate_data => TRUE);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_price_minute_ticker_dt_desc ON price_minute (ticker, datetime DESC);")

    # --- Stock Fundamentals ---
    op.create_table(
        "stock_fundamentals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("per", sa.Float(), nullable=True),
        sa.Column("pbr", sa.Float(), nullable=True),
        sa.Column("roe", sa.Float(), nullable=True),
        sa.Column("eps", sa.Float(), nullable=True),
        sa.Column("bps", sa.Float(), nullable=True),
        sa.Column("div_yield", sa.Float(), nullable=True),
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "date", name="uq_fundamentals_ticker_date"),
    )
    op.create_index("ix_fundamentals_ticker", "stock_fundamentals", ["ticker"])

    # --- Accounts ---
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.Enum("REAL", "SIM", name="accounttype"), nullable=False),
        sa.Column("kis_account_no", sa.String(255), nullable=True),
        sa.Column("kis_app_key", sa.String(512), nullable=True),
        sa.Column("kis_app_secret", sa.String(512), nullable=True),
        sa.Column("kis_access_token", sa.String(1024), nullable=True),
        sa.Column("kis_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("initial_balance", sa.BigInteger(), nullable=False, server_default="10000000"),
        sa.Column("cash_balance", sa.BigInteger(), nullable=False, server_default="10000000"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_accounts_user_type", "accounts", ["user_id", "type"])

    # --- Positions ---
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("unrealized_pnl", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_positions_account_ticker", "positions", ["account_id", "ticker"], unique=True)

    # --- Strategies ---
    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "algorithm_type",
            sa.Enum(
                "MA_CROSS", "RSI", "MACD", "BOLLINGER", "MOMENTUM",
                "STOCHASTIC", "MEAN_REVERT", "MULTI", "CUSTOM",
                name="algorithmtype",
            ),
            nullable=False,
        ),
        sa.Column("params", JSON(), nullable=False, server_default="{}"),
        sa.Column("trade_params", JSON(), nullable=False, server_default="{}"),
        sa.Column("custom_code", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_strategies_user_algo", "strategies", ["user_id", "algorithm_type"])

    # --- Strategy Activations ---
    op.create_table(
        "strategy_activations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("ACTIVE", "PAUSED", "STOPPED", name="activationstatus"), nullable=False, server_default="ACTIVE"),
        sa.Column("tickers", JSON(), nullable=False),
        sa.Column("last_signal_date", sa.String(10), nullable=True),
        sa.Column("last_signal_action", sa.String(10), nullable=True),
        sa.Column("config", JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_activations_account_status", "strategy_activations", ["account_id", "status"])

    # --- Orders ---
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("strategy_activation_id", sa.Integer(), nullable=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("side", sa.Enum("BUY", "SELL", name="orderside"), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("filled_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filled_price", sa.Float(), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "FILLED", "PARTIAL", "CANCELLED", "FAILED", name="orderstatus"), nullable=False, server_default="PENDING"),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("kis_order_no", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_activation_id"], ["strategy_activations.id"]),
    )
    op.create_index("ix_orders_account_status", "orders", ["account_id", "status"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])

    # --- Account Daily ---
    op.create_table(
        "account_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("total_value", sa.BigInteger(), nullable=False),
        sa.Column("cash_balance", sa.BigInteger(), nullable=False),
        sa.Column("stock_value", sa.BigInteger(), nullable=False),
        sa.Column("daily_pnl", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("daily_return_pct", sa.Float(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_account_daily_account_date", "account_daily", ["account_id", "date"], unique=True)

    # --- Backtest Runs ---
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=False),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "DONE", "FAILED", name="backteststatus"), nullable=False, server_default="PENDING"),
        sa.Column("validation_mode", sa.Enum("SIMPLE", "WALK_FORWARD", "OPTIMIZE", name="validationmode"), nullable=False, server_default="SIMPLE"),
        sa.Column("validation_params", JSON(), nullable=True),
        sa.Column("tickers", JSON(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("benchmark_ticker", sa.String(20), nullable=True),
        sa.Column("result_json", JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_backtest_runs_user_status", "backtest_runs", ["user_id", "status"])
    op.create_index("ix_backtest_runs_created_at", "backtest_runs", ["created_at"])

    # --- Backtest Metrics ---
    op.create_table(
        "backtest_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("total_return_pct", sa.Float(), nullable=False),
        sa.Column("annualized_return", sa.Float(), nullable=False),
        sa.Column("benchmark_return", sa.Float(), nullable=False, server_default="0"),
        sa.Column("alpha", sa.Float(), nullable=False, server_default="0"),
        sa.Column("mdd_pct", sa.Float(), nullable=False),
        sa.Column("sharpe_ratio", sa.Float(), nullable=False),
        sa.Column("win_rate", sa.Float(), nullable=False),
        sa.Column("profit_factor", sa.Float(), nullable=False),
        sa.Column("total_trades", sa.Integer(), nullable=False),
        sa.Column("avg_holding_days", sa.Float(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["backtest_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id"),
    )

    # --- Backtest Trades ---
    op.create_table(
        "backtest_trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("action", sa.String(4), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("balance_after", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["backtest_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_backtest_trades_run_id", "backtest_trades", ["run_id"])

    # --- Backtest Equity Curve ---
    op.create_table(
        "backtest_equity_curve",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("portfolio_value", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["backtest_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_backtest_equity_run_id", "backtest_equity_curve", ["run_id"])

    # --- Audit Logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_body", JSON(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_path", "audit_logs", ["path"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("backtest_equity_curve")
    op.drop_table("backtest_trades")
    op.drop_table("backtest_metrics")
    op.drop_table("backtest_runs")
    op.drop_table("account_daily")
    op.drop_table("orders")
    op.drop_table("strategy_activations")
    op.drop_table("strategies")
    op.drop_table("positions")
    op.drop_table("accounts")
    op.drop_table("stock_fundamentals")
    op.drop_table("price_minute")
    op.drop_table("price_daily")
    op.drop_table("refresh_tokens")
    op.drop_table("stocks")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS userrole;")
    op.execute("DROP TYPE IF EXISTS accounttype;")
    op.execute("DROP TYPE IF EXISTS orderside;")
    op.execute("DROP TYPE IF EXISTS orderstatus;")
    op.execute("DROP TYPE IF EXISTS algorithmtype;")
    op.execute("DROP TYPE IF EXISTS activationstatus;")
    op.execute("DROP TYPE IF EXISTS backteststatus;")
    op.execute("DROP TYPE IF EXISTS validationmode;")
