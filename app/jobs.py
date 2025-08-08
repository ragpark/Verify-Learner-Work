import asyncio, os
from datetime import datetime
from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import TransferJob, TransferEvent, Platform
from .azure_dest import stream_copy_to_azure
from .moodle import get_signed_download_url

def log_event(db: Session, job_id: int, level: str, message: str, data=None):
    evt = TransferEvent(job_id=job_id, level=level, message=message, data=data or {})
    db.add(evt); db.commit()

def perform_transfer(job_id: int):
    db = SessionLocal()
    job = db.get(TransferJob, job_id)
    if not job:
        return
    try:
        job.status = "running"; job.updated_at = datetime.utcnow(); db.commit()
        total = sum((f.get("filesize") or 0) for f in job.files)
        job.bytes_total = total; db.commit()

        platform = db.query(Platform).filter_by(issuer=job.issuer).first()
        auth_header = None
        # In OAuth bearer mode, downloads require the Authorization header.
        from .platforms import get_user_token
        ut = get_user_token(db, job.issuer, job.requester_sub)
        if ut:
            auth_header = f"Bearer {ut.access_token}"

        sent = 0
        for f in job.files:
            fname = f["filename"]
            url = f["fileurl"]
            signed = asyncio.run(get_signed_download_url(db, platform, job.requester_sub, url))
            blob_name = f"{job.requester_sub}/{job.course_id}/{fname}"
            log_event(db, job.id, "INFO", f"Uploading {fname}")
            asyncio.run(stream_copy_to_azure(signed, blob_name, auth_header=auth_header))
            sent += f.get("filesize") or 0
            job.bytes_sent = sent; job.updated_at = datetime.utcnow(); db.commit()

        job.status = "completed"; job.updated_at = datetime.utcnow(); db.commit()
        log_event(db, job.id, "INFO", "Transfer complete")
    except Exception as e:
        job.status = "failed"; job.updated_at = datetime.utcnow(); db.commit()
        log_event(db, job.id, "ERROR", f"Transfer failed: {e}")
    finally:
        db.close()
