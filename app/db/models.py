from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="admin")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    api_key_hash = Column(String, unique=True, index=True, nullable=False)
    organization_name = Column(String, nullable=False)
    tier = Column(String, default="standard")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VerificationLog(Base):
    __tablename__ = "verification_logs"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    transaction_reference = Column(String, index=True)
    score = Column(Float)
    verdict = Column(String)
    human_reviewed_verdict = Column(String, nullable=True)
    processing_time_ms = Column(Integer)
    http_status_code = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class ErrorTelemetry(Base):
    __tablename__ = "error_telemetry"
    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(Integer, ForeignKey("verification_logs.id"), nullable=True)
    provider_used = Column(String)
    error_type = Column(String)
    stack_trace = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
