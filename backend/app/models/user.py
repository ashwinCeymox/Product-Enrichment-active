"""
User model — simple role-based auth.

Two roles to start:
  - ADMIN: full control, billing, infrastructure, credential management
  - NORMAL: create job, downloads only — restricted from credentials/settings
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, JSON, String
from passlib.context import CryptContext

from app.database import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="NORMALUSER")  # SUPERADMIN / ADMIN / NORMALUSER
    access_flags = Column(JSON, default=list)  # e.g. ["create_job", "downloads"]

    # ── Timestamps ───────────────────────────────────
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # ── Password helpers ─────────────────────────────
    def set_password(self, password: str):
        self.hashed_password = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)

    def __repr__(self):
        return f"<User {self.email} [{self.role}]>"
