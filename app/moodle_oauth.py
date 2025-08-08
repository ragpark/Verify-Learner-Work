import httpx, urllib.parse
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from .models import Platform, UserToken
from .platforms import get_user_token, set_user_token

def build_auth_url(platform: Platform, app_base_url: str, state: str, scope: str = "webservice"):
    redirect_uri = f"{app_base_url.rstrip('/')}/auth/moodle/callback"
    params = {
        "response_type": "code",
        "client_id": platform.oauth_client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
    }
    return f"{platform.oauth_auth_endpoint}?{urllib.parse.urlencode(params)}"

async def exchange_code_for_tokens(platform: Platform, app_base_url: str, code: str):
    redirect_uri = f"{app_base_url.rstrip('/')}/auth/moodle/callback"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": platform.oauth_client_id,
        "client_secret": platform.oauth_client_secret,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(platform.oauth_token_endpoint, data=data)
        if r.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {r.text}")
        return r.json()

async def refresh_access_token(platform: Platform, refresh_token: str):
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": platform.oauth_client_id,
        "client_secret": platform.oauth_client_secret,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(platform.oauth_token_endpoint, data=data)
        if r.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Refresh failed: {r.text}")
        return r.json()
