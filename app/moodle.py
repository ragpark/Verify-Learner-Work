import httpx, time
from sqlalchemy.orm import Session
from .platforms import get_user_token, set_user_token
from .moodle_oauth import refresh_access_token
from .models import Platform
from fastapi import HTTPException

async def moodle_call(db: Session, platform: Platform, user_sub: str, function: str, params: dict):
    # Ensure we have a fresh access token
    ut = get_user_token(db, platform.issuer, user_sub)
    if not ut:
        raise HTTPException(status_code=401, detail="No Moodle OAuth token. Start authorisation.")

    # Refresh if expiring
    if ut.expires_at.timestamp() - time.time() < 60:
        res = await refresh_access_token(platform, ut.refresh_token)
        set_user_token(db, platform.issuer, user_sub, res.get("access_token"), res.get("refresh_token") or ut.refresh_token, res.get("expires_in", 3600))
        ut = get_user_token(db, platform.issuer, user_sub)

    base = platform.issuer.rstrip('/')
    url = f"{base}/webservice/rest/server.php"
    q = {"moodlewsrestformat": "json", "wsfunction": function, **params}
    headers = {"Authorization": f"Bearer {ut.access_token}"}
    async with httpx.AsyncClient(timeout=None) as client:
        r = await client.post(url, data=q, headers=headers)
        r.raise_for_status()
        res = r.json()
        if isinstance(res, dict) and res.get("exception"):
            raise HTTPException(status_code=400, detail=res.get("message"))
        return res

async def list_course_files(db: Session, platform: Platform, user_sub: str, course_id: int):
    contents = await moodle_call(db, platform, user_sub, "core_course_get_contents", {"courseid": course_id})
    files = []
    for section in contents:
        for mod in section.get("modules", []):
            for content in (mod.get("contents") or []):
                if content.get("type") == "file" and content.get("fileurl"):
                    files.append({
                        "filename": content.get("filename"),
                        "filepath": content.get("filepath"),
                        "fileurl": content.get("fileurl"),
                        "filesize": content.get("filesize") or 0,
                        "timemodified": content.get("timemodified"),
                        "module": {"name": mod.get("name"), "modname": mod.get("modname")}
                    })
    return files

async def get_signed_download_url(db: Session, platform: Platform, user_sub: str, fileurl: str) -> str:
    # With OAuth bearer, Moodle generally allows direct download when Authorization header is present.
    # For simplicity, return the same URL; the downloader will attach Authorization header.
    return fileurl
