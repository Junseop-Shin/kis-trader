-- Full Schema: Users, Stocks, Prices, Strategies, Orders, Account
-- Consolidated V1 for initial deployment

-- 0. Users (Authentication)
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- BCrypt Encoded
    name VARCHAR(50),
    role VARCHAR(20) DEFAULT 'ROLE_USER', -- ROLE_USER, ROLE_ADMIN
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- 1. Master Data: Stocks
CREATE TABLE IF NOT EXISTS stocks (
    ticker VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255),
    market_type VARCHAR(50), -- KOSPI, KOSDAQ
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- 2. Market Data: Daily Prices (Partitioned by Date optional, but keeping simple for V1)
CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGSERIAL,
    ticker VARCHAR(20) NOT NULL REFERENCES stocks(ticker),
    date DATE NOT NULL,
    open NUMERIC(19, 2),
    high NUMERIC(19, 2),
    low NUMERIC(19, 2),
    close NUMERIC(19, 2),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, date) -- Include partitioning key in PK
) PARTITION BY RANGE (date);

CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_date ON daily_prices(ticker, date);

-- 3. Market Data: Minute Prices (Partitioned)
CREATE TABLE IF NOT EXISTS minute_prices (
    id BIGSERIAL,
    ticker VARCHAR(20) NOT NULL REFERENCES stocks(ticker),
    datetime TIMESTAMP NOT NULL,
    open NUMERIC(19, 2),
    high NUMERIC(19, 2),
    low NUMERIC(19, 2),
    close NUMERIC(19, 2),
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id, datetime)
) PARTITION BY RANGE (datetime);

CREATE INDEX IF NOT EXISTS idx_minute_prices_ticker_dt ON minute_prices (ticker, datetime);

-- 4. Strategy Templates (Definition & React Flow Save)
CREATE TABLE IF NOT EXISTS strategy_templates (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id), -- NULL for System Templates, Set for User Custom
    name VARCHAR(255) NOT NULL,
    description TEXT,
    react_flow_data JSONB, -- Stores the visual graph { nodes: [], edges: [] }
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- 5. Strategy Instances (Execution)
CREATE TABLE IF NOT EXISTS strategy_instances (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    template_id BIGINT REFERENCES strategy_templates(id),
    name VARCHAR(255),
    params JSONB, -- Overrides or execution params
    is_active BOOLEAN DEFAULT false,
    last_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- 6. Trade Orders
CREATE TABLE IF NOT EXISTS trade_orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    instance_id BIGINT REFERENCES strategy_instances(id),
    ticker VARCHAR(20) NOT NULL,
    order_type VARCHAR(10), -- BUY, SELL
    price NUMERIC(19, 2),
    quantity INTEGER,
    fee NUMERIC(19, 2) DEFAULT 0,
    status VARCHAR(20), -- PENDING, FILLED, REJECTED
    mode VARCHAR(10), -- LIVE, PAPER
    filled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- 7. Account History (Snapshot)
CREATE TABLE IF NOT EXISTS account_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    date DATE NOT NULL,
    total_balance NUMERIC(19, 2),
    cash_balance NUMERIC(19, 2),
    holdings_snapshot JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
