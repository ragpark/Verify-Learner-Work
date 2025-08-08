from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Platform(Base):
    __tablename__ = "platforms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issuer: Mapped[str] = mapped_column(String(512), unique=True)  # e.g. https://moodle.example
    client_id_lti: Mapped[str] = mapped_column(String(255), default="")  # LTI client id seen in launch (aud)
    deployment_id: Mapped[str] = mapped_column(String(255), default="")

    # OAuth2 to call Moodle APIs (per issuer; admin provides these once)
    oauth_client_id: Mapped[str] = mapped_column(String(255), default="")
    oauth_client_secret: Mapped[str] = mapped_column(String(255), default="")
    oauth_auth_endpoint: Mapped[str] = mapped_column(String(512), default="")
    oauth_token_endpoint: Mapped[str] = mapped_column(String(512), default="")
    jwks_endpoint: Mapped[str] = mapped_column(String(512), default="")

class UserToken(Base):
    __tablename__ = "user_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issuer: Mapped[str] = mapped_column(String(512))
    user_sub: Mapped[str] = mapped_column(String(255))
    access_token: Mapped[str] = mapped_column(Text, default="")
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('issuer', 'user_sub', name='uq_issuer_user'),)

class TransferJob(Base):
    __tablename__ = "transfer_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issuer: Mapped[str] = mapped_column(String(512))  # so we know which platform this job is for
    requester_sub: Mapped[str] = mapped_column(String(255))
    course_id: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32))  # "moodle"
    destination: Mapped[str] = mapped_column(String(32))  # "azure"
    files: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    bytes_total: Mapped[int] = mapped_column(Integer, default=0)
    bytes_sent: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TransferEvent(Base):
    __tablename__ = "transfer_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("transfer_jobs.id"))
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    level: Mapped[str] = mapped_column(String(16), default="INFO")
    message: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSON, default={})
