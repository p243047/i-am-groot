"""
Database Models for LeadGen AI Platform
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Float, ForeignKey, Enum, Index,
    UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY
import enum

from app.core.database import Base


class ProcessingStatus(enum.Enum):
    """Status of batch processing job."""
    PENDING = "pending"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LeadStatus(enum.Enum):
    """Status of individual lead."""
    NEW = "new"
    ENRICHING = "enriching"
    ENRICHED = "enriched"
    FAILED = "failed"
    SKIPPED = "skipped"


class EmailVerificationStatus(enum.Enum):
    """Email verification status."""
    VERIFIED = "verified"
    LIKELY_VALID = "likely_valid"
    CATCH_ALL = "catch_all"
    RISKY = "risky"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    batches = relationship("Batch", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )


class APIKey(Base):
    """API keys for external services configured by users."""
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)  # google, bing, linkedin, etc.
    key_value: Mapped[str] = mapped_column(String(500), nullable=False)  # Encrypted
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    __table_args__ = (
        UniqueConstraint("user_id", "service_name", name="uq_user_service"),
    )


class Batch(Base):
    """Batch processing job for uploaded files."""
    __tablename__ = "batches"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    processed_records: Mapped[int] = mapped_column(Integer, default=0)
    successful_records: Mapped[int] = mapped_column(Integer, default=0)
    failed_records: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        index=True
    )
    
    # Progress tracking
    progress_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_time_remaining: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # seconds
    
    # Celery task tracking
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="batches")
    leads = relationship("Lead", back_populates="batch", cascade="all, delete-orphan")
    logs = relationship("ProcessingLog", back_populates="batch", cascade="all, delete-orphan")


class Lead(Base):
    """Individual business lead record."""
    __tablename__ = "leads"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    
    # Original Data
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_data: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Business Information
    business_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    dba_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Industry & Category
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Website & Domain
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Business Details
    founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_employees: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estimated_revenue: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    business_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Contact Information
    primary_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    secondary_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    support_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sales_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    office_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fax: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Address
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Social Media
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    facebook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instagram_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    twitter_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    youtube_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tiktok_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pinterest_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Website Technical Info
    https_enabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ssl_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    website_technologies: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    cms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    server: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hosting_provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page_speed_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mobile_friendly: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    seo_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title_tag: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    google_analytics_detected: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    facebook_pixel_detected: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    schema_markup_detected: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    broken_images_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    broken_links_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    website_age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    domain_expiration: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Lead Intelligence
    lead_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    lead_quality: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # hot, warm, cold
    confidence_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    email_verification_status: Mapped[Optional[EmailVerificationStatus]] = mapped_column(
        Enum(EmailVerificationStatus), nullable=True
    )
    email_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sales_opportunity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_services: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    ai_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Sources used for enrichment
    sources_used: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Status
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus),
        default=LeadStatus.NEW,
        index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    batch = relationship("Batch", back_populates="leads")
    
    __table_args__ = (
        Index("ix_leads_batch_status", "batch_id", "status"),
        Index("ix_leads_business_name", "business_name"),
        Index("ix_leads_domain", "domain"),
    )


class ProcessingLog(Base):
    """Detailed logs for processing actions."""
    __tablename__ = "processing_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    lead_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    
    # Log details
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # success, error, retry, skipped
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    log_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    batch = relationship("Batch", back_populates="logs")
    lead = relationship("Lead", backref="logs")
    
    __table_args__ = (
        Index("ix_logs_batch_created", "batch_id", "created_at"),
    )
