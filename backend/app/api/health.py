"""
Health check and system status endpoints.
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from app.core.database import get_db, async_session_maker
from app.models.schemas_api import HealthCheck, QueueStatus
from app.workers.celery_app import celery_app

router = APIRouter()


@router.get("/", response_model=HealthCheck)
async def health_check():
    """Check overall system health."""
    db_connected = False
    redis_connected = False
    workers_available = 0
    
    # Check database
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
            db_connected = True
    except Exception:
        pass
    
    # Check Redis/Celery
    try:
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        if active_workers:
            redis_connected = True
            workers_available = len(active_workers)
    except Exception:
        pass
    
    return HealthCheck(
        status="healthy" if db_connected and redis_connected else "degraded",
        version="1.0.0",
        database_connected=db_connected,
        redis_connected=redis_connected,
        workers_available=workers_available,
        timestamp=datetime.utcnow(),
    )


@router.get("/queue", response_model=QueueStatus)
async def queue_status():
    """Get Celery queue status."""
    pending_tasks = 0
    active_tasks = 0
    scheduled_tasks = 0
    workers_online = 0
    workers_total = 0
    
    try:
        inspect = celery_app.control.inspect()
        
        # Get active workers
        active_workers = inspect.active()
        if active_workers:
            workers_online = len(active_workers)
            workers_total = workers_online
            
            # Count active tasks
            for worker, tasks in active_workers.items():
                active_tasks += len(tasks)
        
        # Get scheduled tasks
        scheduled = inspect.scheduled()
        if scheduled:
            for worker, tasks in scheduled.items():
                scheduled_tasks += len(tasks)
        
        # Get reserved (pending) tasks
        reserved = inspect.reserved()
        if reserved:
            for worker, tasks in reserved.items():
                pending_tasks += len(tasks)
                
    except Exception:
        pass
    
    return QueueStatus(
        pending_tasks=pending_tasks,
        active_tasks=active_tasks,
        scheduled_tasks=scheduled_tasks,
        workers_online=workers_online,
        workers_total=workers_total,
    )
