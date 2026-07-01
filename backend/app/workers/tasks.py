"""
Celery tasks for background processing.
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.core.database import async_session_maker, engine, Base
from app.models.schemas import Batch, Lead, ProcessingStatus, LeadStatus, ProcessingLog
from app.services.enrichment_service import BusinessEnrichmentService
from app.services.file_processor import FileProcessingService


@celery_app.task(bind=True, max_retries=3)
def process_batch_task(self, batch_id: int):
    """
    Process all leads in a batch asynchronously.
    
    This task:
    1. Updates batch status to PROCESSING
    2. Processes each lead through enrichment
    3. Updates progress after each lead
    4. Handles errors and retries
    5. Marks batch as complete when done
    """
    try:
        # Run the async processing
        asyncio.run(_process_batch_async(batch_id))
        return {'status': 'completed', 'batch_id': batch_id}
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


async def _process_batch_async(batch_id: int):
    """Async helper for batch processing."""
    async with async_session_maker() as db:
        # Get batch
        batch = await db.get(Batch, batch_id)
        if not batch:
            raise ValueError(f'Batch {batch_id} not found')
        
        # Update batch status
        batch.status = ProcessingStatus.PROCESSING
        batch.started_at = datetime.utcnow()
        await db.flush()
        
        # Log start
        log = ProcessingLog(
            batch_id=batch_id,
            action='batch_started',
            source='worker',
            status='success',
            message=f'Started processing batch {batch_id}',
        )
        db.add(log)
        await db.flush()
        
        # Get all pending leads for this batch
        result = await db.execute(
            select(Lead).where(
                Lead.batch_id == batch_id,
                Lead.status == LeadStatus.NEW,
            ).order_by(Lead.row_number)
        )
        leads = list(result.scalars().all())
        
        total = len(leads)
        processed = 0
        successful = 0
        failed = 0
        
        # Create enrichment service
        enrichment_service = BusinessEnrichmentService(db)
        
        # Process each lead
        for lead in leads:
            try:
                # Enrich the lead
                enriched_lead = await enrichment_service.enrich_lead(lead)
                
                if enriched_lead.status == LeadStatus.ENRICHED:
                    successful += 1
                else:
                    failed += 1
                
            except Exception as e:
                lead.status = LeadStatus.FAILED
                lead.error_message = str(e)
                failed += 1
                
                # Log error
                error_log = ProcessingLog(
                    batch_id=batch_id,
                    lead_id=lead.id,
                    action='enrich_lead',
                    source='worker',
                    status='error',
                    message=str(e),
                )
                db.add(error_log)
            
            processed += 1
            
            # Update batch progress periodically (every 10 leads or last one)
            if processed % 10 == 0 or processed == total:
                batch.processed_records = batch.processed_records + (processed - batch.processed_records)
                batch.successful_records = successful
                batch.failed_records = failed
                if total > 0:
                    batch.progress_percentage = (processed / total) * 100
                await db.flush()
        
        # Mark batch as completed
        batch.status = ProcessingStatus.COMPLETED
        batch.completed_at = datetime.utcnow()
        batch.progress_percentage = 100.0
        
        # Log completion
        completion_log = ProcessingLog(
            batch_id=batch_id,
            action='batch_completed',
            source='worker',
            status='success',
            message=f'Completed processing batch: {successful} successful, {failed} failed',
            metadata={'successful': successful, 'failed': failed},
        )
        db.add(completion_log)
        
        await db.commit()


@celery_app.task(bind=True)
def enrich_single_lead_task(self, lead_id: int):
    """Enrich a single lead."""
    try:
        asyncio.run(_enrich_lead_async(lead_id))
        return {'status': 'completed', 'lead_id': lead_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


async def _enrich_lead_async(lead_id: int):
    """Async helper for single lead enrichment."""
    async with async_session_maker() as db:
        lead = await db.get(Lead, lead_id)
        if not lead:
            raise ValueError(f'Lead {lead_id} not found')
        
        enrichment_service = BusinessEnrichmentService(db)
        await enrichment_service.enrich_lead(lead)
        
        await db.commit()


@celery_app.task
def cleanup_old_data_task(days: int = 30):
    """Clean up old processed data."""
    # Placeholder for cleanup task
    # Would delete logs older than specified days
    return {'status': 'completed', 'days': days}


@celery_app.task
def health_check_task():
    """Simple health check task."""
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
