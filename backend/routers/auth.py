"""
Google OAuth 2.0 flow.

Steps:
  1. GET  /auth/google/login      → redirect to Google consent
  2. GET  /auth/google/callback   → exchange code for tokens, upsert user, issue session JWT
  3. GET  /auth/google/accounts   → list accessible Google Ads customer accounts
  4. POST /auth/google/select     → user selects which account to audit; we store encrypted refresh token
  5. POST /auth/logout            → clear session
"""

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Cookie
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import get_settings
from database import get_db
from models import User, ConnectedAccount
from services.google_ads import GoogleAdsService
from services.token_encryption import encrypt_token, decrypt_token

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/adwords",
]

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30


def create_session_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.secret_key,
        algorithm=JWT_ALGORITHM,
    )


def decode_session_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


async def get_current_user(
    session_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = decode_session_token(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/google/login")
async def google_login():
    """Redirect the browser to Google's OAuth consent page."""
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.backend_url}/auth/google/callback",
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",   # Required to receive a refresh_token
        "prompt": "consent",        # Always show consent so we get a fresh refresh_token
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """Exchange auth code for tokens, upsert user, set session cookie."""
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": f"{settings.backend_url}/auth/google/callback",
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()

    access_token: str = token_data["access_token"]
    refresh_token: str = token_data.get("refresh_token", "")

    if not refresh_token:
        # Google only issues refresh_token on first consent; if missing, revoke and re-auth
        raise HTTPException(
            status_code=400,
            detail="No refresh token returned. Please revoke app access at myaccount.google.com and try again.",
        )

    # Fetch user profile
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    google_id: str = userinfo["sub"]
    email: str = userinfo["email"]
    name: str = userinfo.get("name", "")

    # Upsert user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(google_id=google_id, email=email, name=name)
        db.add(user)
    else:
        user.email = email
        user.name = name
    await db.commit()
    await db.refresh(user)

    # Store the access token in session (short-lived) so the accounts listing step can use it
    # We store it in the JWT payload — it expires with the JWT (30 min for this step)
    account_selection_token = jwt.encode(
        {
            "sub": str(user.id),
            "access_token": access_token,
            "refresh_token": encrypt_token(refresh_token),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
        settings.secret_key,
        algorithm=JWT_ALGORITHM,
    )

    # Redirect to frontend account selection page
    redirect_url = (
        f"{settings.frontend_url}/auth/callback"
        f"?token={account_selection_token}"
    )
    return RedirectResponse(redirect_url)


@router.get("/google/accounts")
async def list_google_ads_accounts(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Decode the short-lived account-selection token, list accessible Google Ads
    customer IDs for the user, and return them for display.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    access_token: str = payload["access_token"]
    encrypted_refresh: str = payload["refresh_token"]
    user_id: str = payload["sub"]

    refresh_token = decrypt_token(encrypted_refresh)

    ads_service = GoogleAdsService(
        developer_token=settings.google_ads_developer_token,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        refresh_token=refresh_token,
    )

    try:
        accounts = await ads_service.list_accessible_customers()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Google Ads API error listing customers")
        raise HTTPException(
            status_code=502,
            detail=(
                f"Google Ads API error: {exc}. "
                "Check that your developer token is approved and that this Google account "
                "has access to at least one Google Ads account."
            ),
        )

    return {
        "accounts": accounts,
        "selection_token": token,
    }


@router.post("/google/select")
async def select_google_ads_account(
    body: dict,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    User selects which Google Ads account to connect. We store the encrypted
    refresh token and issue the final session cookie.
    """
    token: str = body.get("selection_token", "")
    customer_id: str = body.get("customer_id", "")
    account_name: str = body.get("account_name", "")

    if not token or not customer_id:
        raise HTTPException(status_code=400, detail="Missing selection_token or customer_id")

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id: str = payload["sub"]
    encrypted_refresh: str = payload["refresh_token"]

    # Upsert connected account
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.google_ads_customer_id == customer_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        account = ConnectedAccount(
            user_id=user_id,
            google_ads_customer_id=customer_id,
            account_name=account_name,
            encrypted_refresh_token=encrypted_refresh,
        )
        db.add(account)
    else:
        account.encrypted_refresh_token = encrypted_refresh
        account.account_name = account_name
        account.last_used_at = datetime.now(timezone.utc)

    await db.commit()

    # Issue long-lived session cookie
    session_token = create_session_token(user_id)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=settings.frontend_url.startswith("https"),
        max_age=60 * 60 * 24 * 30,  # 30 days
    )

    return {"ok": True, "user_id": user_id}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session_token")
    return {"ok": True}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
    }
