"""Authentication and authorization for the governance API.

Human callers authenticate with Supabase access-token JWTs. Automated model
monitors use a separate server-only API key so they never need a human account
or the Supabase service-role key.
"""

import hmac
import os
from dataclasses import dataclass
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError, PyJWTError

load_dotenv()
load_dotenv(".env.auth")


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


AUTH_DISABLED = _enabled("AUTH_DISABLED")
SUPABASE_URL = (
    os.getenv("SUPABASE_URL")
    or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    or ""
).rstrip("/")
SUPABASE_AUDIENCE = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")
MONITOR_API_KEY = os.getenv("MONITOR_API_KEY", "")
MONITOR_ACTOR = os.getenv("MONITOR_ACTOR", "governance-monitor-service")
ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv("AUTH_ADMIN_EMAILS", "").split(",")
    if email.strip()
}

bearer_scheme = HTTPBearer(auto_error=False, description="Supabase access token")
monitor_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
_jwks_client = (
    PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json", cache_keys=True)
    if SUPABASE_URL
    else None
)


@dataclass(frozen=True)
class Actor:
    subject: str
    display_name: str
    email: str | None
    kind: str  # user, service, or development
    role: str

    @property
    def audit_label(self) -> str:
        return self.email or self.display_name or self.subject


def _actor_from_claims(claims: dict[str, Any]) -> Actor:
    metadata = claims.get("user_metadata") or {}
    app_metadata = claims.get("app_metadata") or {}
    email = claims.get("email")
    role = claims.get("user_role") or app_metadata.get("role") or "viewer"
    if email and email.lower() in ADMIN_EMAILS:
        role = "admin"

    display_name = (
        metadata.get("full_name")
        or metadata.get("name")
        or email
        or claims.get("sub")
        or "authenticated-user"
    )
    return Actor(
        subject=str(claims.get("sub", "unknown")),
        display_name=str(display_name),
        email=str(email) if email else None,
        kind="user",
        role=str(role),
    )


def require_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Depends(monitor_key_scheme),
) -> Actor:
    """Authenticate a Supabase user or the dedicated monitoring service."""
    if AUTH_DISABLED:
        return Actor("local-development", "local-development", None, "development", "admin")

    if api_key and MONITOR_API_KEY and hmac.compare_digest(api_key, MONITOR_API_KEY):
        return Actor(MONITOR_ACTOR, MONITOR_ACTOR, None, "service", "monitor")

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not SUPABASE_URL or _jwks_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase authentication is not configured on the API",
        )

    token = credentials.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["ES256", "RS256"],
            audience=SUPABASE_AUDIENCE,
            issuer=f"{SUPABASE_URL}/auth/v1",
        )
    except (PyJWTError, PyJWKClientError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return _actor_from_claims(claims)


def require_human_role(actor: Actor, *allowed_roles: str) -> None:
    """Reject service credentials and users without an allowed governance role."""
    if actor.kind == "development":
        return
    if actor.kind != "user" or actor.role not in set(allowed_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your authenticated identity does not have permission for this action. "
                f"Required role: {', '.join(allowed_roles)}."
            ),
        )


def audit_actor(actor: Actor, development_fallback: str | None = None) -> str:
    """Use legacy caller text only while tests explicitly disable authentication."""
    if actor.kind == "development" and development_fallback:
        return development_fallback
    return actor.audit_label
