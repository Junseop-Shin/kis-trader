# Pending Actions

## 1. Credentials Required

These must be set in `.env` (copy from `.env.template`):

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | TimescaleDB password |
| `JWT_SECRET_KEY` | Generate with `openssl rand -hex 32` |
| `KIS_ENCRYPT_KEY` | Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL for notifications |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare Tunnel token |
| `WINDOWS_PC_IP` | Windows PC LAN IP for Mac Mini worker |

## 2. UI Library

The project was designed to use your local `my-ui-lib`. Currently, UI components are implemented inline using Tailwind CSS. To integrate `my-ui-lib`:

- Install it: `cd frontend && npm link my-ui-lib` (or however it's published)
- Replace inline components with `my-ui-lib` equivalents (Dialog, Select, Slider, Switch, Tabs, Tooltip)
- Radix UI primitives are included as dependencies as a fallback

## 3. Docker Configuration

### Windows PC (`docker-compose.yml`)
- Postgres and Redis ports are NOT exposed externally by default
- If Mac Mini needs to connect, add port mappings or use Docker network
- Set real `POSTGRES_PASSWORD` and `CLOUDFLARE_TUNNEL_TOKEN`

### Mac Mini (`docker-compose.mac.yml`)
- Set `WINDOWS_PC_IP` to the actual Windows PC LAN IP
- Docker socket is mounted for custom code sandbox
- Ensure the Python Docker image (`python:3.12-slim`) is pulled: `docker pull python:3.12-slim`

## 4. First-Time Setup Steps

```bash
# 1. Start infrastructure
docker compose up -d postgres redis

# 2. Run database migrations
cd backend
pip install -r requirements.txt
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/kistrader alembic upgrade head

# 3. Initial data load (takes ~30 minutes for 3 years of KOSPI+KOSDAQ)
# The data-collector service does this automatically on first start:
docker compose up -d data-collector
# Or run manually:
cd data-collector && python -c "
import asyncio
from collector import _get_engine, _get_session_factory, initial_bulk_load
engine = _get_engine('postgresql+asyncpg://postgres:PASSWORD@localhost:5432/kistrader')
sf = _get_session_factory(engine)
asyncio.run(initial_bulk_load(sf))
"

# 4. Start all services
docker compose up -d

# 5. Start Mac Mini worker
# On Mac Mini:
docker compose -f docker-compose.mac.yml up -d

# 6. Install frontend dependencies and run
cd frontend
npm install
npm run dev
```

## 5. TimescaleDB Extension

The Alembic migration creates the TimescaleDB extension automatically:
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

Ensure you're using the `timescale/timescaledb:latest-pg17` Docker image (NOT plain postgres). If using a managed database, enable TimescaleDB extension first.

## 6. Architecture Decisions vs. Plan

| Area | Decision | Reason |
|------|----------|--------|
| Frontend framework | Next.js 15 (not 16) | 16 is too new/unstable; 15.0.0 is stable |
| Inline signal generation | Backend has simplified signal gen | Avoids importing backtest-worker code into backend |
| Custom code sandbox | Uses Docker-in-Docker | Requires Docker socket mount on Mac Mini |
| WebSocket backtest progress | Simplified polling | Full Celery event stream would require additional Redis pub/sub |
| Slack notifications | Webhook-based (not Bot API) | Simpler setup, no bot user needed |
| Audit middleware | Raw SQL insert | Avoids ORM overhead in middleware hot path |
| Risk manager defaults | Conservative (500K daily loss, 30% position) | Production-safe defaults; adjust per user |

## 7. Known Limitations

- **Admin user management**: The admin page is a placeholder. Implement admin-only endpoints for user CRUD.
- **pykrx rate limiting**: Bulk collection uses 100-150ms delays. Initial 3-year load takes ~30 min.
- **Walk-forward optimization UI**: The backend supports it; frontend shows results but doesn't have a dedicated optimization parameter grid UI.
- **KIS WebSocket real-time**: The real-trading service has a WebSocket stub. Full KIS WebSocket integration requires their streaming API subscription.
- **Custom code sandbox**: Requires `docker pull python:3.12-slim` on the Mac Mini before first use.
- **Email verification**: Not implemented. Add if needed for public-facing deployment.
