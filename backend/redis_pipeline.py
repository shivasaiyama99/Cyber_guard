"""
Redis Pub/Sub Pipeline — publishes log rows to Redis for persistence and
cross-process distribution. Gracefully degrades to in-memory queues if Redis
is unavailable.
"""

import asyncio
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CHANNEL = "cyberguard:logs"
STREAM_KEY = "cyberguard:stream"
STREAM_MAXLEN = 50000  # cap Redis stream at 50k entries
TTL_SECONDS = 86400  # 24 hours


class LogPublisher:
    """Publishes log rows to Redis channel + stream. Falls back to no-op if Redis unavailable."""

    def __init__(self):
        self._redis = None
        self._available = False

    async def connect(self):
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(REDIS_URL, decode_responses=True)
            await self._redis.ping()
            self._available = True
            logger.info("redis_pipeline: connected to Redis at %s", REDIS_URL)
        except Exception as e:
            self._available = False
            self._redis = None
            logger.info("Redis unavailable — using in-memory fallback: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    async def publish(self, row: dict):
        """Publish a log row to Redis channel and stream."""
        if not self._available or self._redis is None:
            return

        try:
            payload = json.dumps(row, default=str)
            # Pub/Sub channel
            await self._redis.publish(CHANNEL, payload)
            # Redis Stream for persistence
            flat = {k: str(v) for k, v in row.items()}
            await self._redis.xadd(STREAM_KEY, flat, maxlen=STREAM_MAXLEN, approximate=True)
        except Exception as e:
            logger.debug("Redis publish error: %s", e)

    async def close(self):
        if self._redis:
            await self._redis.close()


class LogSubscriber:
    """Subscribes to Redis channel and forwards messages to an asyncio.Queue."""

    def __init__(self):
        self._redis = None
        self._pubsub = None
        self._available = False

    async def connect(self):
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(REDIS_URL, decode_responses=True)
            await self._redis.ping()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe(CHANNEL)
            self._available = True
            logger.info("redis_pipeline: subscriber connected")
        except Exception as e:
            self._available = False
            logger.warning("Redis subscriber unavailable: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    async def listen(self, queue: asyncio.Queue):
        """Forward Redis channel messages to the given queue."""
        if not self._available or self._pubsub is None:
            return

        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await queue.put(data)
                    except (json.JSONDecodeError, asyncio.QueueFull):
                        pass
        except Exception as e:
            logger.debug("Redis subscriber error: %s", e)

    async def close(self):
        if self._pubsub:
            await self._pubsub.unsubscribe(CHANNEL)
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()


# Singleton instances
publisher = LogPublisher()
subscriber = LogSubscriber()
