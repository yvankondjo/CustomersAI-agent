import os
import logging
import redis
from rq import Queue
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

REDIS_AVAILABLE = False
redis_conn = None
document_queue = None
website_queue = None

try:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_conn = redis.from_url(redis_url, socket_connect_timeout=2)
    redis_conn.ping()
    REDIS_AVAILABLE = True
    document_queue = Queue("documents", connection=redis_conn)
    website_queue = Queue("websites", connection=redis_conn)
    logger.info("Redis connection established for RQ queues")
except Exception as e:
    logger.warning(f"Redis not available, RQ queues disabled: {e}")
    REDIS_AVAILABLE = False

