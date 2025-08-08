from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session
from redis import Redis
from rq import Queue
from typing import Dict, Any
from .config import settings
from .db import init_db, SessionLocal
from .lti import validate_lti_id_token
from .models import Platform, TransferJob
from .platforms import get_or_create_platform, get_user_token, set_user_token
from .moodle_oauth import build_auth_url, exchange_code_for_tokens
from .moodle import list_course_files
from .schemas import CreateTransfer
from .jobs import perform_transfer

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# remove this line near the top:
# init_db()

from fastapi import FastAPI
app = FastAPI()

@app.on_event("startup")
def _startup():
    # Try to init DB but never crash the server if it fails
    try:
        init_db()
        print("[INFO] DB init ok")
    except Exception as e:
        print(f"[WARN] DB init failed at startup: {e}")
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def require_session(request: Request) -> Dict[str, Any]:
    if not request.session.get("lti"):
        raise HTTPException(status_code=401, detail="LTI launch required")
    return request.session["lti"]

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.post("/lti/launch")
async def lti_launch(request: Request, id_token: str = Form(...), state: str = Form(None), db: Session = Depends(get_db)):
    claims = await validate_lti_id_token(id_token)
    issuer = claims.get("iss")
    deployment_id = claims.get("https://purl.imsglobal.org/spec/lti/claim/deployment_id", "")
    aud = claims.get("aud")
    client_id_lti = aud if isinstance(aud, str) else (aud[0] if aud else "")

    # Ensure platform exists
    platform = get_or_create_platform(db, issuer, client_id_lti, deployment_id)

    request.session["lti"] = {
        "issuer": issuer,
        "user_sub": claims.get("sub"),
        "name": claims.get("name") or "",
    }
    # If platform missing OAuth client creds, send to setup UI
    if not platform.oauth_client_id or not platform.oauth_client_secret:
        return RedirectResponse(url="/platform/setup", status_code=303)

    # If no user token, start OAuth auth code flow
    ut = get_user_token(db, issuer, claims.get("sub"))
    if not ut:
        return RedirectResponse(url="/auth/moodle/start", status_code=303)

    return RedirectResponse(url="/ui", status_code=303)

@app.get("/platform/setup", response_class=HTMLResponse)
async def platform_setup(request: Request, db: Session = Depends(get_db)):
    ctx = request.session.get("lti")
    if not ctx: return HTMLResponse("<p>LTI launch required</p>", status_code=401)
    platform = db.query(Platform).filter_by(issuer=ctx["issuer"]).first()
    return templates.TemplateResponse("platform_setup.html", {"request": request, "platform": platform})

@app.post("/platform/setup")
async def platform_setup_post(request: Request, db: Session = Depends(get_db),
                              oauth_client_id: str = Form(...),
                              oauth_client_secret: str = Form(...),
                              oauth_auth_endpoint: str = Form(...),
                              oauth_token_endpoint: str = Form(...)):
    ctx = request.session.get("lti")
    if not ctx: raise HTTPException(status_code=401, detail="LTI launch required")
    p = db.query(Platform).filter_by(issuer=ctx["issuer"]).first()
    if not p: raise HTTPException(400, "Platform not found")
    p.oauth_client_id = oauth_client_id.strip()
    p.oauth_client_secret = oauth_client_secret.strip()
    p.oauth_auth_endpoint = oauth_auth_endpoint.strip()
    p.oauth_token_endpoint = oauth_token_endpoint.strip()
    db.commit()
    return RedirectResponse(url="/auth/moodle/start", status_code=303)

@app.get("/auth/moodle/start")
async def moodle_auth_start(request: Request, db: Session = Depends(get_db)):
    ctx = request.session.get("lti")
    if not ctx: raise HTTPException(status_code=401, detail="LTI launch required")
    platform = db.query(Platform).filter_by(issuer=ctx["issuer"]).first()
    state = f"{ctx['issuer']}|{ctx['user_sub']}"
    url = build_auth_url(platform, settings.APP_BASE_URL, state=state, scope="webservice")
    return RedirectResponse(url, status_code=303)

@app.get("/auth/moodle/callback")
async def moodle_auth_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    ctx = request.session.get("lti")
    if not ctx: raise HTTPException(status_code=401, detail="LTI launch required")
    platform = db.query(Platform).filter_by(issuer=ctx["issuer"]).first()
    tokens = await exchange_code_for_tokens(platform, settings.APP_BASE_URL, code)
    set_user_token(db, platform.issuer, ctx["user_sub"], tokens.get("access_token"), tokens.get("refresh_token"), tokens.get("expires_in", 3600))
    return RedirectResponse(url="/ui", status_code=303)

@app.get("/ui", response_class=HTMLResponse)
async def ui(request: Request, db: Session = Depends(get_db)):
    ctx = request.session.get("lti")
    if not ctx: return HTMLResponse("<h2>Launch Required</h2><p>Please launch this tool from your LMS as an admin.</p>")
    platform = db.query(Platform).filter_by(issuer=ctx["issuer"]).first()
    return templates.TemplateResponse("picker.html", {"request": request, "user": {"name": ctx["name"] or ctx["user_sub"]}, "platform": platform})

@app.get("/moodle/files")
async def moodle_files(course_id: int, request: Request, db: Session = Depends(get_db)):
    ctx = require_session(request)
    platform = db.query(Platform).filter_by(issuer=ctx["issuer"]).first()
    files = await list_course_files(db, platform, ctx["user_sub"], course_id)
    return {"files": files[:200]}

@app.post("/transfers")
async def create_transfer(payload: CreateTransfer, request: Request, db: Session = Depends(get_db)):
    ctx = require_session(request)
    job = TransferJob(
        issuer=ctx["issuer"],
        requester_sub=ctx["user_sub"],
        course_id=str(payload.course_id),
        source="moodle",
        destination="azure",
        files=[{"filename": f["filename"], "fileurl": f["fileurl"], "filesize": f.get("filesize", 0)} for f in payload.files],
        status="queued",
    )
    db.add(job); db.commit(); db.refresh(job)
    q = Queue('transfers', connection=Redis.from_url(os.getenv("REDIS_URL")))
    q.enqueue(perform_transfer, job.id)
    return {"job_id": job.id, "status": job.status}

@app.get("/transfers/{job_id}")
async def get_transfer(job_id: int, request: Request, db: Session = Depends(get_db)):
    ctx = require_session(request)
    job = db.get(TransferJob, job_id)
    if not job or job.issuer != ctx["issuer"]:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": job.id, "status": job.status, "bytes_total": job.bytes_total, "bytes_sent": job.bytes_sent}
