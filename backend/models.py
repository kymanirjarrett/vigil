import uuid
from sqlalchemy import Column, Integer, String, DateTime, Boolean, UniqueConstraint, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    family_id  = Column(UUID(as_uuid=True), nullable=False, index=True)
    is_revoked = Column(Boolean, nullable=False, default=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role          = Column(String, nullable=False, default="analyst")
    is_active     = Column(Boolean, nullable=False, default=True)
    demo_mode     = Column(Boolean, nullable=False, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    locked_until  = Column(DateTime(timezone=True), nullable=True)


class AuthEvent(Base):
    __tablename__ = "auth_events"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email      = Column(String, nullable=False, index=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String, nullable=False, index=True)  # login_success | login_failure | signup
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action        = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=True)
    resource_id   = Column(String, nullable=True)
    meta          = Column("metadata", JSON, nullable=True)
    ip_address    = Column(String, nullable=True)
    user_agent    = Column(String, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id          = Column(Integer, primary_key=True, index=True)
    job_name    = Column(String, nullable=False, index=True)
    run_id      = Column(String, nullable=False)
    type        = Column(String, nullable=False)    # DURATION_SPIKE | CONSECUTIVE_FAILURES
    severity    = Column(String, nullable=False)    # warning | critical
    message     = Column(String, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("run_id", "type", name="uq_anomaly_run_type"),
    )


class AlertLog(Base):
    __tablename__ = "alert_log"

    id              = Column(Integer, primary_key=True, index=True)
    recipient       = Column(String, nullable=False)
    job_name        = Column(String, nullable=False)
    anomaly_count   = Column(Integer, nullable=False)
    sent_at         = Column(DateTime(timezone=True), server_default=func.now())
    sendgrid_status = Column(Integer, nullable=True)


class Role(Base):
    __tablename__ = "roles"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class Permission(Base):
    __tablename__ = "permissions"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id       = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
