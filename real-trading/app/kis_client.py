"""
KIS REST API client for real-money trading.
Handles OAuth2 token management, order placement, balance/position queries.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

KIS_BASE_URL = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
KIS_ENCRYPT_KEY = os.getenv("KIS_ENCRYPT_KEY", "")


def _get_fernet() -> Fernet:
    return Fernet(KIS_ENCRYPT_KEY.encode())


def decrypt_value(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


class KISClient:
    def __init__(self, app_key: str, app_secret: str, account_no: str, access_token: str | None = None):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.access_token = access_token
        self._token_expires_at: datetime | None = None

    async def _ensure_token(self):
        """Get or refresh OAuth2 access token."""
        if self.access_token and self._token_expires_at and datetime.now(timezone.utc) < self._token_expires_at:
            return

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{KIS_BASE_URL}/oauth2/tokenP",
                json={
                    "grant_type": "client_credentials",
                    "appkey": self.app_key,
                    "appsecret": self.app_secret,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 86400)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 600)
            logger.info("KIS access token refreshed")

    def _headers(self) -> dict:
        """Standard KIS API request headers."""
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

    async def place_order(
        self,
        ticker: str,
        side: str,
        qty: int,
        price: int,
        order_type: str = "00",
    ) -> dict:
        """
        Place a real KIS order.
        order_type: "00" = limit, "01" = market
        """
        await self._ensure_token()

        if side == "BUY":
            tr_id = "TTTC0802U"
        else:
            tr_id = "TTTC0801U"

        cano = self.account_no[:8]
        acnt_prdt_cd = self.account_no[9:]

        headers = {**self._headers(), "tr_id": tr_id}
        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "PDNO": ticker,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price) if order_type == "00" else "0",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{KIS_BASE_URL}/uapi/domestic-stock/v1/trading/order-cash",
                headers=headers,
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("rt_cd") != "0":
                raise ValueError(f"KIS order failed: {data.get('msg1', 'Unknown error')}")

            order_no = data.get("output", {}).get("ODNO", "")
            logger.info(f"KIS order placed: {side} {ticker} x{qty} @ {price}, order_no={order_no}")
            return {"order_no": order_no, "data": data}

    async def get_balance(self) -> dict:
        """Get account balance and summary."""
        await self._ensure_token()

        cano = self.account_no[:8]
        acnt_prdt_cd = self.account_no[9:]

        headers = {**self._headers(), "tr_id": "TTTC8434R"}
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance",
                headers=headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("rt_cd") != "0":
                raise ValueError(f"KIS balance query failed: {data.get('msg1')}")

            output2 = data.get("output2", [{}])
            summary = output2[0] if output2 else {}

            return {
                "total_eval": int(summary.get("tot_evlu_amt", 0)),
                "cash_balance": int(summary.get("dnca_tot_amt", 0)),
                "stock_eval": int(summary.get("scts_evlu_amt", 0)),
                "daily_pnl": int(summary.get("evlu_pfls_smtl_amt", 0)),
            }

    async def get_positions(self) -> list[dict]:
        """Get current stock holdings."""
        await self._ensure_token()

        cano = self.account_no[:8]
        acnt_prdt_cd = self.account_no[9:]

        headers = {**self._headers(), "tr_id": "TTTC8434R"}
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance",
                headers=headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            positions = []
            for item in data.get("output1", []):
                qty = int(item.get("hldg_qty", 0))
                if qty > 0:
                    positions.append({
                        "ticker": item.get("pdno", ""),
                        "name": item.get("prdt_name", ""),
                        "qty": qty,
                        "avg_price": float(item.get("pchs_avg_pric", 0)),
                        "current_price": float(item.get("prpr", 0)),
                        "eval_amount": int(item.get("evlu_amt", 0)),
                        "pnl": int(item.get("evlu_pfls_amt", 0)),
                        "pnl_pct": float(item.get("evlu_pfls_rt", 0)),
                    })
            return positions

    async def get_current_price(self, ticker: str) -> dict:
        """Get real-time stock quote."""
        await self._ensure_token()

        headers = {**self._headers(), "tr_id": "FHKST01010100"}
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
                headers=headers,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            output = data.get("output", {})

            return {
                "ticker": ticker,
                "price": int(output.get("stck_prpr", 0)),
                "change": int(output.get("prdy_vrss", 0)),
                "change_pct": float(output.get("prdy_ctrt", 0)),
                "volume": int(output.get("acml_vol", 0)),
            }
