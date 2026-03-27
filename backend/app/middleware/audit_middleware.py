import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import text

from ..database import async_session_factory

logger = logging.getLogger(__name__)

AUDITED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
AUDITED_PATHS = {"/auth/", "/trading/", "/backtest/", "/strategies/", "/accounts/", "/admin/"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method not in AUDITED_METHODS:
            return await call_next(request)

        path = request.url.path
        should_audit = any(path.startswith(p) for p in AUDITED_PATHS)
        if not should_audit:
            return await call_next(request)

        # Read request body for audit (only JSON)
        body_data = None
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                raw_body = await request.body()
                body_data = json.loads(raw_body)
                # Redact sensitive fields
                for key in ("password", "totp_code", "refresh_token", "kis_app_secret"):
                    if key in body_data:
                        body_data[key] = "***REDACTED***"
            except Exception:
                body_data = None

        response = await call_next(request)

        # Extract user info from request state if available
        user_id = None
        user_email = None
        if hasattr(request.state, "user"):
            user_id = request.state.user.id
            user_email = request.state.user.email

        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500]

        try:
            async with async_session_factory() as session:
                await session.execute(
                    text(
                        "INSERT INTO audit_logs "
                        "(user_id, user_email, method, path, status_code, ip_address, user_agent, request_body) "
                        "VALUES (:uid, :email, :method, :path, :status, :ip, :ua, :body)"
                    ),
                    {
                        "uid": user_id,
                        "email": user_email,
                        "method": request.method,
                        "path": path,
                        "status": response.status_code,
                        "ip": ip_address,
                        "ua": user_agent,
                        "body": json.dumps(body_data) if body_data else None,
                    },
                )
                await session.commit()
        except Exception as e:
            logger.warning(f"Audit log insert failed: {e}")

        return response
