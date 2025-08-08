from jose import jwt
import httpx
from fastapi import HTTPException, status
from typing import Dict, Any

ADMIN_ROLE_URIS = {
    "http://purl.imsglobal.org/vocab/lis/v2/membership#Administrator",
    "http://purl.imsglobal.org/vocab/lis/v2/membership#ContentDeveloper",
    "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor",
}

async def fetch_jwks(issuer: str) -> Dict[str, Any]:
    # Moodle typically exposes JWKS at /mod/lti/certs.php
    url = issuer.rstrip("/") + "/mod/lti/certs.php"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()

async def validate_lti_id_token(id_token: str) -> Dict[str, Any]:
    # Decode using issuer-derived JWKS. For PoC we do NOT verify 'aud' to avoid per-issuer client_id config.
    unverified = jwt.get_unverified_claims(id_token)
    issuer = unverified.get("iss")
    if not issuer:
        raise HTTPException(status_code=401, detail="Missing issuer in id_token")

    jwks = await fetch_jwks(issuer)
    try:
        claims = jwt.decode(
            id_token,
            jwks,
            options={"verify_aud": False, "verify_at_hash": False},
            issuer=issuer,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"LTI id_token invalid: {e}")

    roles = set(claims.get("https://purl.imsglobal.org/spec/lti/claim/roles") or [])
    if not roles.intersection(ADMIN_ROLE_URIS):
        raise HTTPException(status_code=403, detail="Admin/Instructor roles required")

    return claims
