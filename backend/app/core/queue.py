from redis import Redis
from rq import Queue

from app.core.config import settings

redis_conn = Redis.from_url(settings.REDIS_URL)
generation_queue = Queue("generations", connection=redis_conn)
