# 풀스택 주식 자동화 시스템 설계서

> **v2 — 로컬 배포 전환 (2026.03)**
> GCP 기반 설계에서 Windows + Mac Mini 2대 로컬 머신으로 전환.
> Cloudflare Tunnel로 HTTPS 외부 접근, Firebase → Spring Boot WebSocket(STOMP) 대체.

---

## 1. 전체 네트워크 아키텍처

```mermaid
graph TD
    Browser["🌐 브라우저\n(어디서든 접속)"]

    subgraph CF["☁️ Cloudflare"]
        DNS["DNS 관리"]
        Tunnel["Cloudflare Tunnel\n(SSL 자동, 포트 오픈 불필요)"]
    end

    subgraph WIN["🖥️ Windows (웹 + 매매 서버)"]
        cloudflared["cloudflared\n(터널 에이전트)"]

        subgraph DockerCompose["Docker Compose"]
            Frontend["Next.js Frontend\n:3000"]
            Backend["Spring Boot Backend\n:8080"]
            DB["PostgreSQL 17\n:5432"]
            LiveEngine["Live Trading Engine\n(FastAPI) :8000"]
        end
    end

    subgraph MAC["🍎 Mac Mini (백테스팅 전담)"]
        BacktestEngine["Backtesting Engine\n(FastAPI) :8001"]
    end

    subgraph KIS["🏦 한국투자증권"]
        KisAPI["KIS REST API\nopenapi.koreainvestment.com:9443"]
    end

    Browser -- "HTTPS" --> CF
    CF -- "app.도메인.com" --> cloudflared
    CF -- "api.도메인.com" --> cloudflared
    CF -- "ws.도메인.com" --> cloudflared

    cloudflared -- ":3000" --> Frontend
    cloudflared -- ":8080" --> Backend

    Frontend <-- "REST / WebSocket(STOMP)" --> Backend
    Backend --> DB
    Backend -- "Feign :8000" --> LiveEngine
    Backend -- "Feign :8001" --> BacktestEngine

    LiveEngine -- "REST" --> KisAPI
```

### 클라우드 → 로컬 전환 대응표

| 기존 (GCP) | 변경 (Local) |
|---|---|
| GCP Cloud SQL (PostgreSQL 17) | Windows Docker `postgres:17` |
| Firebase RTDB (실시간 알림) | Spring Boot WebSocket + STOMP |
| GCP Compute Engine (단일 VM) | Windows(웹/매매) + Mac Mini(백테스팅) 분산 |
| Cloud NAT → KIS API | Windows 직접 인터넷 연결 |
| HTTPS + 도메인 | Cloudflare Tunnel (SSL 자동, 포트 오픈 불필요) |
| Nginx 리버스 프록시 | Cloudflare Tunnel + 서비스별 서브도메인 |

---

## 2. 머신별 서비스 구성

```mermaid
graph LR
    subgraph WIN["🖥️ Windows — Docker Compose"]
        direction TB
        FE["Next.js Frontend\n:3000\n─────────────\nReact Flow 전략 빌더\n백테스트 결과 차트\nWebSocket 클라이언트"]
        BE["Spring Boot Backend\n:8080\n─────────────\nREST API\nJWT 인증\nFlyway 마이그레이션\nSTOMP WebSocket 브로커"]
        PG["PostgreSQL 17\n:5432\n─────────────\nusers, strategies\ndaily_price, minute_price\ntrade_orders"]
        LE["Live Trading Engine\n(FastAPI) :8000\n─────────────\nKIS 토큰 관리\n실시간 시세 조회\n주문 실행"]
        CF2["cloudflared\n─────────────\nCloudflare Tunnel\n인바운드 HTTPS 처리"]

        FE <--> BE
        BE --> PG
        BE --> LE
        CF2 --> FE
        CF2 --> BE
    end

    subgraph MAC["🍎 Mac Mini — 직접 실행 or Docker"]
        direction TB
        BT["Backtesting Engine\n(FastAPI) :8001\n─────────────\nRSI 전략 시뮬레이션\nSharpe / MDD 계산\n과거 데이터 처리"]
    end

    BE -- "LAN\nhttp://mac-ip:8001" --> BT
    LE -- "Internet\nKIS REST API" --> KIS["🏦 KIS API"]
```

| 머신 | 역할 | 실행 서비스 |
|---|---|---|
| **Windows** | 웹 서버 + 실전 매매 서버 | Next.js, Spring Boot, PostgreSQL, Live Engine, cloudflared |
| **Mac Mini** | 개발 + 백테스팅 전담 | Backtesting Engine (FastAPI) |

---

## 3. 데이터 흐름

### 3-1. 백테스팅 흐름

```mermaid
sequenceDiagram
    actor User as 👤 사용자
    participant FE as Next.js Frontend
    participant BE as Spring Boot Backend
    participant BT as Backtesting Engine (Mac Mini)
    participant DB as PostgreSQL

    User->>FE: 전략 설정 + 기간 입력 (React Flow 빌더)
    FE->>BE: POST /api/backtest/run
    BE->>BT: POST /backtest (BacktestEngineFeignClient)

    Note over BT: 1. prices → DataFrame 변환<br/>2. RSI 계산 (pandas)<br/>3. BUY/SELL 시뮬레이션<br/>4. Sharpe / MDD 계산

    BT-->>BE: BacktestResult {return_pct, max_drawdown, sharpe_ratio, trades[]}
    BE->>DB: 결과 저장 (strategy_instance)
    BE-->>FE: 백테스트 결과 JSON
    FE->>User: 수익률 차트 (recharts) + 거래 내역
```

### 3-2. 실전 매매 흐름

```mermaid
sequenceDiagram
    actor User as 👤 사용자
    participant FE as Next.js Frontend
    participant BE as Spring Boot Backend
    participant LE as Live Engine (Windows)
    participant KIS as KIS API
    participant DB as PostgreSQL

    Note over LE: 서버 시작 시 KIS 토큰 발급 / 만료 전 자동 갱신

    User->>FE: 매수/매도 버튼 클릭
    FE->>BE: POST /api/live/order
    BE->>LE: POST /order (LiveEngineFeignClient)
    LE->>KIS: POST /uapi/.../order-cash
    KIS-->>LE: 주문 접수 결과
    LE-->>BE: {success, data}
    BE->>DB: trade_order 저장
    BE-->>FE: 주문 결과

    Note over BE,FE: STOMP /user/{id}/queue/trades<br/>로 실시간 체결 알림 푸시

    FE->>User: 체결 알림 표시

    loop 시세 조회 (스케줄)
        BE->>LE: GET /price/{ticker}
        LE->>KIS: GET inquire-daily-price
        KIS-->>LE: 현재가
        LE-->>BE: {ticker, price, change_rate}
        BE->>FE: STOMP /topic/market 브로드캐스트
    end
```

---

## 4. 프로젝트 파일 구조

```mermaid
graph TD
    ROOT["kis-trader/"]

    ROOT --> DC["docker-compose.yml\n(Windows 전용 5개 서비스)"]
    ROOT --> ENV[".env.template\n(환경변수 템플릿)"]
    ROOT --> CF["cloudflare/config.yml\n(Tunnel 서브도메인 라우팅)"]
    ROOT --> REQ["requirements.txt\n(fastapi, uvicorn, pandas...)"]

    ROOT --> SRC["src/"]
    SRC --> LIVE["live_engine/ (Windows :8000)"]
    LIVE --> LM["main.py\nGET /health\nGET /price/{ticker}\nPOST /order\nGET /balance"]
    LIVE --> LD["Dockerfile"]

    SRC --> BKT["backtest_engine/ (Mac Mini :8001)"]
    BKT --> BM["main.py\nGET /health\nPOST /backtest\n→ RSI 시뮬레이션\n→ Sharpe / MDD"]
    BKT --> BD["Dockerfile"]

    SRC --> STR["strategies/ (기존 전략 클래스)"]
    STR --> BS["base_strategy.py"]
    STR --> RS["rsi_strategy.py"]

    ROOT --> BE["backend/ (Spring Boot)"]
    BE --> APP["application.yml\n+ engine.live-url\n+ engine.backtest-url\n+ datasource 환경변수화"]
    BE --> POM["pom.xml\n+ websocket starter"]
    BE --> CFG["global/config/WebSocketConfig.java\n(STOMP /ws 엔드포인트)"]
    BE --> SVC["service/\nNotificationService.java\nLiveEngineFeignClient.java\nBacktestEngineFeignClient.java"]

    ROOT --> FE["frontend/ (Next.js)"]
    FE --> PKG["package.json\n@stomp/stompjs, recharts\nreactflow (firebase 없음)"]
    FE --> HOOK["src/hooks/useWebSocket.ts\nSTOMP 연결 + 구독 관리"]
    FE --> LIB["src/lib/api.ts\naxios 클라이언트\nrunBacktest / placeOrder"]
    FE --> FD["Dockerfile (standalone 빌드)"]
```

---

## 5. Python Engine 분리 설계

| 서비스 | 위치 | 역할 | 주요 엔드포인트 |
|---|---|---|---|
| `live-engine` | Windows :8000 | KIS 토큰 관리, 실시간 시세, 주문 실행 | `POST /order`, `GET /price/{ticker}`, `GET /balance` |
| `backtest-engine` | Mac Mini :8001 | 과거 데이터 시뮬레이션, 지표 계산 | `POST /backtest`, `GET /health` |

Backend(Spring Boot)가 요청 유형에 따라 라우팅:
- 백테스팅 → `${engine.backtest-url}` (Mac Mini)
- 실전 매매 → `${engine.live-url}` (Windows localhost)

---

## 6. 데이터베이스 설계 (ERD)

전략(Definition)과 실행(Instance)을 분리하여 확장성을 확보했습니다.

```mermaid
erDiagram
    STRATEGY_TEMPLATES {
        bigint id PK
        bigint user_id FK "작성자 ID (NULL=시스템)"
        varchar name "전략명"
        jsonb react_flow_data "React Flow (Nodes/Edges)"
    }

    USERS {
        bigint id PK
        varchar email "이메일"
        varchar password "암호화된 비밀번호"
        varchar name "이름"
        role enum "ROLE_USER, ROLE_ADMIN"
    }

    STRATEGY_INSTANCES {
        bigint id PK
        bigint user_id FK "사용자 ID"
        varchar template_code FK
        varchar name "설정 이름"
        jsonb params "파라미터"
        boolean is_active
    }

    STOCKS {
        varchar ticker PK "종목코드"
        varchar name "종목명"
        varchar market_type "시장구분"
    }

    DAILY_PRICES {
        bigint id PK
        varchar ticker FK
        date date
        decimal close
        decimal volume
    }

    MINUTE_PRICES {
        bigint id PK
        varchar ticker FK
        timestamp datetime
        decimal close
    }

    TRADE_ORDERS {
        bigint id PK
        bigint user_id FK "사용자 ID"
        bigint instance_id FK
        varchar ticker FK
        varchar type "BUY/SELL"
        decimal price
        varchar status
    }

    ACCOUNT_HISTORY {
        bigint id PK
        bigint user_id FK "사용자 ID"
        date date
        decimal total_balance
        jsonb holdings_snapshot
    }

    USERS ||--o{ STRATEGY_INSTANCES : "owns"
    USERS ||--o{ TRADE_ORDERS : "makes"
    USERS ||--o{ ACCOUNT_HISTORY : "has"
    STRATEGY_TEMPLATES ||--o{ STRATEGY_INSTANCES : "def"
    STRATEGY_INSTANCES ||--o{ TRADE_ORDERS : "exec"
    STOCKS ||--o{ DAILY_PRICES : "has"
    STOCKS ||--o{ MINUTE_PRICES : "has"
    STRATEGY_INSTANCES ||--o{ ACCOUNT_HISTORY : "affects"
```

### JSONB 컬럼 상세

**`strategy_templates.react_flow_data`** (UI Canvas 저장용)
```json
{
  "nodes": [
    { "id": "node-1", "type": "dataSource", "data": { "label": "Samsung Electronics" }, "position": { "x": 100, "y": 100 } },
    { "id": "node-2", "type": "indicator", "data": { "name": "RSI", "period": 14 }, "position": { "x": 300, "y": 100 } }
  ],
  "edges": [{ "id": "edge-1", "source": "node-1", "target": "node-2" }],
  "viewport": { "x": 0, "y": 0, "zoom": 1.5 }
}
```

**`strategy_instances.params`** (전략 실행 파라미터)
```json
{
  "target_tickers": ["005930", "000660"],
  "timeframe": "1D",
  "buy_threshold": 30,
  "sell_threshold": 70,
  "stop_loss_pct": 0.03
}
```

**`account_history.holdings_snapshot`** (일별 보유종목 스냅샷)
```json
[
  { "ticker": "005930", "qty": 10, "avg_price": 70500, "cur_price": 71000, "pnl_pct": 0.7 },
  { "ticker": "035420", "qty": 5, "avg_price": 210000, "cur_price": 205000, "pnl_pct": -2.3 }
]
```

---

## 7. 기술 스택

| 레이어 | 기술 |
|---|---|
| **Frontend** | Next.js 15, React 19, TypeScript, React Flow, recharts, @stomp/stompjs |
| **Backend** | Spring Boot 3.4, Java 21, Spring Security, OpenFeign, WebSocket(STOMP), Flyway |
| **Live Engine** | Python 3.12, FastAPI, uvicorn |
| **Backtest Engine** | Python 3.12, FastAPI, pandas 2.2, numpy |
| **Database** | PostgreSQL 17 (Docker) |
| **인프라** | Docker Compose (Windows), Cloudflare Tunnel, cloudflared |

---

## 8. 주요 기능

1. **사용자 인증** — JWT 기반 로그인/회원가입, ROLE_USER / ROLE_ADMIN 권한 분리
2. **전략 빌더** — React Flow 노드 기반 드래그앤드롭 전략 설계, 템플릿 선택
3. **백테스팅** — 과거 데이터 RSI 시뮬레이션 → 수익률/MDD/Sharpe 차트 (Mac Mini 처리)
4. **실전 매매** — KIS API 연동, 자동 주문 실행, STOMP WebSocket 실시간 체결 알림
5. **자산 관리** — 일별/월별 누적 수익금, 포지션 현황 대시보드

---

## 9. 실행 방법

### Windows (웹 + 매매 서버)
```bash
# 1. 환경변수 설정
cp .env.template .env
# .env 파일에서 KIS 키, DB 비밀번호, BACKTEST_ENGINE_URL(Mac Mini IP) 입력

# 2. 전체 서비스 기동
docker compose up -d

# 3. 헬스체크
curl http://localhost:8080/actuator/health
curl http://localhost:8000/health
```

### Mac Mini (백테스팅 서버)
```bash
pip install -r requirements.txt
uvicorn src.backtest_engine.main:app --host 0.0.0.0 --port 8001
```

### Cloudflare Tunnel 설정
```bash
# 1. Tunnel 생성
cloudflared tunnel create kis-trader

# 2. cloudflare/config.yml 에서 <tunnel-id> 교체

# 3. DNS 레코드 추가 (Cloudflare Dashboard)
#    app.도메인.com → tunnel
#    api.도메인.com → tunnel
#    ws.도메인.com  → tunnel
```

---

## 10. MVP 개발 순서

1. Windows `docker compose up -d` — postgres + backend 기동
2. Mac Mini backtest-engine 기동
3. Backend → Backtest Engine 통신 확인 (`GET /health`)
4. React Flow 전략 빌더 → `/backtest` API 연동
5. 백테스트 결과 차트 UI
6. WebSocket 실시간 알림
7. Live Trading Engine 기동 + KIS 가상계좌 연동 (최후)
