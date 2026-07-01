"""
Celery configuration and application setup.
"""
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    'leadgen',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.workers.tasks'],
)

# Configure Celery
celery_app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Task settings
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Rate limiting
    task_default_rate_limit='10/m',
    
    # Retries
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Result settings
    result_expires=3600 * 24,  # 24 hours
    result_persistent=True,
)


def get_celery_app():
    """Get the Celery application instance."""
    return celery_app
