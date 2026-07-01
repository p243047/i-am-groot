"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
import re


# ============== Authentication Schemas ==============

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    role: str
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request schema."""
    refresh_token: str


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


# ============== API Key Schemas ==============

class APIKeyBase(BaseModel):
    """Base API key schema."""
    service_name: str
    is_active: bool = True


class APIKeyCreate(APIKeyBase):
    """Schema for creating an API key."""
    key_value: str


class APIKeyResponse(APIKeyBase):
    """Schema for API key response (without actual key value)."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============== Batch Processing Schemas ==============

class BatchBase(BaseModel):
    """Base batch schema."""
    name: str


class BatchCreate(BaseModel):
    """Schema for creating a batch."""
    name: Optional[str] = None


class BatchStatusUpdate(BaseModel):
    """Schema for updating batch status."""
    status: str  # pending, processing, paused, completed, failed, cancelled


class BatchResponse(BatchBase):
    """Schema for batch response."""
    id: int
    user_id: int
    original_filename: str
    file_path: str
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    status: str
    progress_percentage: float
    estimated_time_remaining: Optional[int]
    celery_task_id: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class BatchProgressResponse(BaseModel):
    """Schema for batch progress response."""
    batch_id: int
    status: str
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    progress_percentage: float
    estimated_time_remaining: Optional[int]
    eta_completion: Optional[datetime]


# ============== Lead Schemas ==============

class LeadBase(BaseModel):
    """Base lead schema."""
    business_name: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class LeadCreate(LeadBase):
    """Schema for creating a lead."""
    row_number: int
    original_data: Dict[str, Any] = Field(default_factory=dict)


class LeadEnriched(BaseModel):
    """Schema for enriched lead data."""
    # Business Info
    legal_name: Optional[str] = None
    dba_name: Optional[str] = None
    industry: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    founded_year: Optional[int] = None
    estimated_employees: Optional[str] = None
    estimated_revenue: Optional[str] = None
    business_status: Optional[str] = None
    
    # Contact Info
    primary_email: Optional[str] = None
    secondary_email: Optional[str] = None
    support_email: Optional[str] = None
    sales_email: Optional[str] = None
    owner_email: Optional[str] = None
    office_email: Optional[str] = None
    mobile: Optional[str] = None
    whatsapp: Optional[str] = None
    fax: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Social Media
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    youtube_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    pinterest_url: Optional[str] = None
    
    # Website Tech
    https_enabled: Optional[bool] = None
    ssl_valid: Optional[bool] = None
    website_technologies: Optional[List[str]] = None
    cms: Optional[str] = None
    server: Optional[str] = None
    hosting_provider: Optional[str] = None
    page_speed_score: Optional[int] = None
    mobile_friendly: Optional[bool] = None
    seo_score: Optional[int] = None
    meta_description: Optional[str] = None
    title_tag: Optional[str] = None
    google_analytics_detected: Optional[bool] = None
    facebook_pixel_detected: Optional[bool] = None
    schema_markup_detected: Optional[bool] = None
    broken_images_count: Optional[int] = None
    broken_links_count: Optional[int] = None
    website_age_days: Optional[int] = None
    domain_expiration: Optional[datetime] = None
    
    # Lead Intelligence
    lead_score: Optional[int] = None
    lead_quality: Optional[str] = None
    confidence_score: Optional[int] = None
    email_verification_status: Optional[str] = None
    email_source: Optional[str] = None
    sales_opportunity: Optional[str] = None
    recommended_services: Optional[List[str]] = None
    ai_notes: Optional[str] = None
    sources_used: Optional[List[str]] = None


class LeadResponse(LeadBase, LeadEnriched):
    """Schema for lead response."""
    id: int
    batch_id: int
    row_number: int
    original_data: Dict[str, Any]
    status: str
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime
    enriched_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class LeadFilter(BaseModel):
    """Schema for filtering leads."""
    status: Optional[str] = None
    lead_quality: Optional[str] = None
    has_email: Optional[bool] = None
    has_website: Optional[bool] = None
    min_confidence_score: Optional[int] = None
    search_query: Optional[str] = None


# ============== Processing Log Schemas ==============

class ProcessingLogBase(BaseModel):
    """Base log schema."""
    action: str
    source: Optional[str] = None
    status: str
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProcessingLogResponse(ProcessingLogBase):
    """Schema for log response."""
    id: int
    batch_id: int
    lead_id: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============== File Upload Schemas ==============

class FileUploadResponse(BaseModel):
    """Schema for file upload response."""
    batch_id: int
    filename: str
    total_records: int
    message: str


# ============== Export Schemas ==============

class ExportRequest(BaseModel):
    """Schema for export request."""
    format: str = Field("xlsx", pattern="^(xlsx|csv|json)$")
    include_fields: Optional[List[str]] = None
    filters: Optional[LeadFilter] = None


class ExportResponse(BaseModel):
    """Schema for export response."""
    download_url: str
    filename: str
    total_records: int
    expires_at: datetime


# ============== Dashboard Stats Schemas ==============

class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""
    total_batches: int
    total_leads: int
    total_enriched: int
    success_rate: float
    processing_jobs: int
    pending_jobs: int
    failed_jobs: int
    recent_activity: List[Dict[str, Any]]


# ============== Worker Status Schemas ==============

class WorkerStatus(BaseModel):
    """Schema for worker status."""
    worker_id: str
    status: str  # idle, busy, offline
    current_task: Optional[str]
    tasks_completed: int
    last_seen: datetime


class QueueStatus(BaseModel):
    """Schema for queue status."""
    pending_tasks: int
    active_tasks: int
    scheduled_tasks: int
    workers_online: int
    workers_total: int


# ============== Health Check Schemas ==============

class HealthCheck(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    database_connected: bool
    redis_connected: bool
    workers_available: int
    timestamp: datetime
