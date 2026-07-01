"""
Batches API endpoints for managing processing jobs.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.schemas import Batch, Lead, ProcessingStatus, LeadStatus
from app.models.schemas_api import BatchResponse, BatchProgressResponse, BatchCreate
from app.api.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=BatchResponse)
async def create_batch(
    batch_data: BatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Create a new empty batch."""
    batch = Batch(
        user_id=current_user.id,
        name=batch_data.name or "Untitled Batch",
        original_filename="manual",
        file_path="",
        total_records=0,
        status=ProcessingStatus.PENDING,
    )
    
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    
    return batch


@router.get("/", response_model=List[BatchResponse])
async def list_batches(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List all batches for the current user."""
    query = select(Batch).where(Batch.user_id == current_user.id)
    
    if status_filter:
        try:
            status_enum = ProcessingStatus(status_filter)
            query = query.where(Batch.status == status_enum)
        except ValueError:
            pass
    
    query = query.order_by(Batch.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    batches = list(result.scalars().all())
    
    return batches


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get a specific batch by ID."""
    batch = await db.get(Batch, batch_id)
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )
    
    # Check ownership
    if batch.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    return batch


@router.get("/{batch_id}/progress", response_model=BatchProgressResponse)
async def get_batch_progress(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get detailed progress for a batch."""
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
    
    # Calculate ETA if processing
    eta_completion = None
    if batch.status == ProcessingStatus.PROCESSING and batch.processed_records > 0:
        # Estimate based on current rate
        remaining = batch.total_records - batch.processed_records
        if batch.started_at:
            from datetime import datetime, timedelta
            elapsed = (datetime.utcnow() - batch.started_at).total_seconds()
            if elapsed > 0 and batch.processed_records > 0:
                rate = batch.processed_records / elapsed
                estimated_remaining_seconds = remaining / rate
                from datetime import datetime
                eta_completion = datetime.utcnow() + timedelta(seconds=estimated_remaining_seconds)
    
    return BatchProgressResponse(
        batch_id=batch.id,
        status=batch.status.value,
        total_records=batch.total_records,
        processed_records=batch.processed_records,
        successful_records=batch.successful_records,
        failed_records=batch.failed_records,
        progress_percentage=batch.progress_percentage,
        estimated_time_remaining=int((100 - batch.progress_percentage) / 100 * 3600) if batch.progress_percentage < 100 else 0,
        eta_completion=eta_completion,
    )


@router.post("/{batch_id}/start")
async def start_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Start processing a batch."""
    from app.workers.tasks import process_batch_task
    
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
    
    if batch.status not in [ProcessingStatus.PENDING, ProcessingStatus.PAUSED, ProcessingStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start batch with status: {batch.status.value}",
        )
    
    # Start Celery task
    task = process_batch_task.delay(batch_id)
    batch.celery_task_id = task.id
    batch.status = ProcessingStatus.PROCESSING
    
    await db.commit()
    
    return {"message": "Batch processing started", "task_id": task.id}


@router.post("/{batch_id}/pause")
async def pause_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Pause a processing batch."""
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
    
    if batch.status != ProcessingStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch is not currently processing",
        )
    
    batch.status = ProcessingStatus.PAUSED
    
    # Revoke Celery task
    if batch.celery_task_id:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(batch.celery_task_id, terminate=True)
    
    await db.commit()
    
    return {"message": "Batch processing paused"}


@router.post("/{batch_id}/cancel")
async def cancel_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Cancel a batch."""
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
    
    batch.status = ProcessingStatus.CANCELLED
    
    # Revoke Celery task
    if batch.celery_task_id:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(batch.celery_task_id, terminate=True)
    
    await db.commit()
    
    return {"message": "Batch cancelled"}


@router.delete("/{batch_id}")
async def delete_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Delete a batch and all its leads."""
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
    
    # Delete associated records (cascade will handle leads and logs)
    await db.delete(batch)
    await db.commit()
    
    return {"message": "Batch deleted successfully"}
