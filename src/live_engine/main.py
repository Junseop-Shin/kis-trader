"""
Live Trading Engine — FastAPI server (Windows only)
Wraps KIS API for real/virtual order execution and real-time price queries.
"""
import os
import datetime
import requests
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="KIS Live Trading Engine")

# ---------------------------------------------------------------------------
# Configuration — loaded from environment variables at startup
# ---------------------------------------------------------------------------

KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"
KIS_VIRTUAL_BASE_URL = "https://openapivts.koreainvestment.com:29443"

APPKEY = os.environ["KIS_APPKEY"]
APPSECRET = os.environ["KIS_APPSECRET"]
ACCOUNT_NO = os.environ["KIS_ACCOUNT_NO"]           # e.g. "12345678-01"
IS_REAL = os.environ.get("KIS_IS_REAL_TRADING", "false").lower() == "true"

BASE_URL = KIS_BASE_URL if IS_REAL else KIS_VIRTUAL_BASE_URL

# ---------------------------------------------------------------------------
# Token cache (module-level singleton)
# ---------------------------------------------------------------------------

_access_token: str | None = None
_token_expires_at: datetime.datetime | None = None


def _issue_token() -> str:
    global _access_token, _token_expires_at
    res = requests.post(
        f"{BASE_URL}/oauth2/tokenP",
        headers={"content-type": "application/json"},
        json={"grant_type": "client_credentials", "appkey": APPKEY, "appsecret": APPSECRET},
        timeout=10,
    )
    res.raise_for_status()
    data = res.json()
    _access_token = data["access_token"]
    _token_expires_at = datetime.datetime.now() + datetime.timedelta(seconds=data.get("expires_in", 86400))
    return _access_token


def get_token() -> str:
    if _access_token is None or _token_expires_at is None or _token_expires_at <= datetime.datetime.now():
        return _issue_token()
    return _access_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_headers(tr_id: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_token()}",
        "appkey": APPKEY,
        "appsecret": APPSECRET,
        "tr_id": tr_id,
    }


def _account_parts() -> tuple[str, str]:
    parts = ACCOUNT_NO.split("-")
    return parts[0], parts[1]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class OrderRequest(BaseModel):
    side: str       # "buy" or "sell"
    ticker: str     # e.g. "005930"
    quantity: int
    price: float = 0   # 0 = market order


class OrderResponse(BaseModel):
    success: bool
    message: str
    data: dict | None = None


class PriceResponse(BaseModel):
    ticker: str
    price: float
    change_rate: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "mode": "real" if IS_REAL else "virtual"}


@app.get("/price/{ticker}", response_model=PriceResponse)
def get_price(ticker: str):
    tr_id = "FHKST01010100"
    headers = _base_headers(tr_id)
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": ticker,
        "FID_INPUT_DATE_1": "",
        "FID_INPUT_DATE_2": "",
        "FID_PERIOD_DIV_CODE": "D",
        "FID_ORG_ADJ_PRC": "0",
    }
    res = requests.get(
        f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-price",
        headers=headers,
        params=params,
        timeout=10,
    )
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail=f"KIS API error: {res.text}")
    body = res.json()
    if body.get("rt_cd") != "0":
        raise HTTPException(status_code=502, detail=body.get("msg1", "KIS API returned error"))
    output = body["output"][0]
    return PriceResponse(
        ticker=ticker,
        price=float(output.get("stck_clpr", 0)),
        change_rate=float(output.get("prdy_ctrt", 0)),
    )


@app.post("/order", response_model=OrderResponse)
def place_order(req: OrderRequest):
    cano, acnt_prdt_cd = _account_parts()
    if req.side == "buy":
        tr_id = "TTTC0802U" if IS_REAL else "VTTC0802U"
    else:
        tr_id = "TTTC0801U" if IS_REAL else "VTTC0801U"

    headers = _base_headers(tr_id)
    data = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": req.ticker,
        "ORD_DVSN": "01",           # market order
        "ORD_QTY": str(req.quantity),
        "ORD_UNPR": str(int(req.price)),
        "CTRT_EXP_DT": "",
        "PDNO_FLG": "",
        "PRCS_DVSN": "",
        "IVRS_PRCS_DVSN": "",
    }
    res = requests.post(
        f"{BASE_URL}/uapi/domestic-stock/v1/trading/order-cash",
        headers=headers,
        json=data,
        timeout=10,
    )
    if res.status_code != 200:
        return OrderResponse(success=False, message=res.text)
    body = res.json()
    if body.get("rt_cd") != "0":
        return OrderResponse(success=False, message=body.get("msg1", "Order failed"))
    return OrderResponse(success=True, message="Order placed", data=body.get("output"))


@app.get("/balance")
def get_balance():
    cano, acnt_prdt_cd = _account_parts()
    tr_id = "TTTC8434R" if IS_REAL else "VTTC8434R"
    headers = _base_headers(tr_id)
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "01",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    res = requests.get(
        f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance",
        headers=headers,
        params=params,
        timeout=10,
    )
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail=res.text)
    return res.json()
