from sqlalchemy.orm import Session
from .models import Platform, UserToken
from datetime import datetime, timedelta

def derive_endpoints_from_issuer(issuer: str):
    issuer = issuer.rstrip('/')
    # Reasonable defaults; admins can override in setup UI
    return {
        "jwks_endpoint": f"{issuer}/mod/lti/certs.php",
        "oauth_auth_endpoint": f"{issuer}/oauth2/authorize.php",
        "oauth_token_endpoint": f"{issuer}/oauth2/token.php",
    }

def get_or_create_platform(db: Session, issuer: str, client_id_lti: str, deployment_id: str):
    p = db.query(Platform).filter_by(issuer=issuer).first()
    if not p:
        eps = derive_endpoints_from_issuer(issuer)
        p = Platform(
            issuer=issuer,
            client_id_lti=client_id_lti or "",
            deployment_id=deployment_id or "",
            jwks_endpoint=eps["jwks_endpoint"],
            oauth_auth_endpoint=eps["oauth_auth_endpoint"],
            oauth_token_endpoint=eps["oauth_token_endpoint"],
            oauth_client_id="",
            oauth_client_secret="",
        )
        db.add(p); db.commit(); db.refresh(p)
    else:
        # Update latest seen client_id/deployment
        changed = False
        if client_id_lti and p.client_id_lti != client_id_lti:
            p.client_id_lti = client_id_lti; changed = True
        if deployment_id and p.deployment_id != deployment_id:
            p.deployment_id = deployment_id; changed = True
        if changed:
            db.commit()
    return p

def get_user_token(db: Session, issuer: str, user_sub: str):
    return db.query(UserToken).filter_by(issuer=issuer, user_sub=user_sub).first()

def set_user_token(db: Session, issuer: str, user_sub: str, access_token: str, refresh_token: str, expires_in: int):
    ut = get_user_token(db, issuer, user_sub)
    exp = datetime.utcnow() + timedelta(seconds=max(expires_in-30, 30))
    if not ut:
        ut = UserToken(issuer=issuer, user_sub=user_sub, access_token=access_token, refresh_token=refresh_token, expires_at=exp)
        db.add(ut)
    else:
        ut.access_token = access_token
        ut.refresh_token = refresh_token or ut.refresh_token
        ut.expires_at = exp
    db.commit()
    return ut
