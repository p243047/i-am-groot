"""
Leads API endpoints for querying and managing enriched leads.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.models.schemas import Lead, Batch, LeadStatus
from app.models.schemas_api import LeadResponse, LeadFilter
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/batch/{batch_id}", response_model=List[LeadResponse])
async def list_leads(
    batch_id: int,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    lead_quality: Optional[str] = None,
    has_email: Optional[bool] = None,
    has_website: Optional[bool] = None,
    min_confidence_score: Optional[int] = None,
    search_query: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List leads for a batch with optional filtering."""
    # Verify batch ownership
    batch = await db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )
    
    if batch.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Build query
    query = select(Lead).where(Lead.batch_id == batch_id)
    
    # Apply filters
    if status_filter:
        try:
            status_enum = LeadStatus(status_filter)
            query = query.where(Lead.status == status_enum)
        except ValueError:
            pass
    
    if lead_quality:
        query = query.where(Lead.lead_quality == lead_quality)
    
    if has_email is True:
        query = query.where(Lead.primary_email.isnot(None))
    
    if has_website is True:
        query = query.where(Lead.website.isnot(None))
    
    if min_confidence_score:
        query = query.where(Lead.confidence_score >= min_confidence_score)
    
    if search_query:
        search_filter = or_(
            Lead.business_name.ilike(f"%{search_query}%"),
            Lead.domain.ilike(f"%{search_query}%"),
            Lead.primary_email.ilike(f"%{search_query}%"),
        )
        query = query.where(search_filter)
    
    # Pagination
    query = query.order_by(Lead.row_number).offset(skip).limit(limit)
    
    result = await db.execute(query)
    leads = list(result.scalars().all())
    
    return leads


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get a specific lead by ID."""
    lead = await db.get(Lead, lead_id)
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )
    
    # Verify batch ownership
    batch = await db.get(Batch, lead.batch_id)
    if not batch or batch.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return lead


@router.post("/{lead_id}/retry")
async def retry_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Retry processing a failed lead."""
    from app.workers.tasks import enrich_single_lead_task
    
    lead = await db.get(Lead, lead_id)
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )
    
    # Verify batch ownership
    batch = await db.get(Batch, lead.batch_id)
    if not batch or batch.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Reset lead status
    lead.status = LeadStatus.NEW
    lead.error_message = None
    lead.retry_count += 1
    
    # Queue for processing
    task = enrich_single_lead_task.delay(lead_id)
    
    await db.commit()
    
    return {"message": "Lead queued for retry", "task_id": task.id}


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Delete a lead."""
    lead = await db.get(Lead, lead_id)
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )
    
    # Verify batch ownership
    batch = await db.get(Batch, lead.batch_id)
    if not batch or batch.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    await db.delete(lead)
    await db.commit()
    
    return {"message": "Lead deleted successfully"}
