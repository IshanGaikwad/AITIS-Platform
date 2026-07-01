"""Execution Queue — Redis-backed job queue for Playwright automation.

Provides:
- Job submission with priority support
- Job status tracking via Redis hashes
- Pub/sub for cancellation signals
- Worker heartbeat monitoring
- Concurrency-limited dequeue with atomic operations
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from redis import asyncio as aioredis

logger = logging.getLogger("aitis.execution_queue")

# ── Redis key patterns ────────────────────────────────────────────────
QUEUE_KEY = "automation:execution_queue"           # List — FIFO job queue
PRIORITY_QUEUE_KEY = "automation:priority_queue"   # Sorted set — priority jobs
JOB_STATUS_PREFIX = "automation:job:"               # Hash — job metadata
CANCEL_CHANNEL = "automation:cancel"                # Pub/sub — cancel signals
WORKER_HEARTBEAT_PREFIX = "automation:worker:"     # String — worker heartbeats
CONCURRENCY_SEMAPHORE = "automation:concurrency"    # String — running count


class ExecutionQueue:
    """Redis-backed execution queue with priority, cancellation, and concurrency."""

    def __init__(self, redis: aioredis.Redis, max_concurrent: int = 4):
        self.redis = redis
        self.max_concurrent = max_concurrent

    # ── Job Submission ─────────────────────────────────────────────

    async def submit_job(
        self,
        job_id: uuid.UUID,
        script_id: uuid.UUID,
        script_version_id: uuid.UUID,
        organization_id: uuid.UUID,
        project_id: uuid.UUID,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Submit a job to the execution queue.

        Args:
            job_id: ExecutionJob UUID
            script_id: AutomationScript UUID
            script_version_id: ScriptVersion UUID
            organization_id: Tenant org ID
            project_id: Tenant project ID
            priority: Higher = runs sooner (default 0)
            metadata: Extra job metadata dict
        """
        payload = json.dumps({
            "job_id": str(job_id),
            "script_id": str(script_id),
            "script_version_id": str(script_version_id),
            "organization_id": str(organization_id),
            "project_id": str(project_id),
            "priority": priority,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        })

        # Store job metadata in Redis hash for fast lookups
        await self.redis.hset(
            f"{JOB_STATUS_PREFIX}{job_id}",
            mapping={
                "status": "queued",
                "payload": payload,
                "queued_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        if priority > 0:
            # Priority queue — sorted by score (higher = sooner)
            await self.redis.zadd(PRIORITY_QUEUE_KEY, {str(job_id): priority})
        else:
            # Standard FIFO queue
            await self.redis.rpush(QUEUE_KEY, payload)

        logger.info("Job %s submitted to execution queue (priority=%s)", job_id, priority)

    # ── Job Dequeue ────────────────────────────────────────────────

    async def dequeue_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Atomically dequeue the next job for a worker.

        Priority queue is checked first, then the standard FIFO queue.
        Returns the job payload dict or None if queue is empty.
        """
        # Check concurrency limit
        running = await self._running_count()
        if running >= self.max_concurrent:
            logger.debug("Worker %s: concurrency limit reached (%d/%d)",
                         worker_id, running, self.max_concurrent)
            return None

        # Try priority queue first (highest score)
        priority_result = await self.redis.zpopmax(PRIORITY_QUEUE_KEY)
        if priority_result:
            job_id_bytes, _ = priority_result[0]
            job_key = f"{JOB_STATUS_PREFIX}{job_id_bytes.decode()}"
            payload_str = await self.redis.hget(job_key, "payload")
            if payload_str:
                payload = json.loads(payload_str)
                await self._mark_picked_up(job_id_bytes.decode(), worker_id)
                return payload

        # Fall back to standard FIFO queue (blocking pop with 1s timeout)
        result = await self.redis.blpop(QUEUE_KEY, timeout=1)
        if result:
            _, payload_bytes = result
            payload = json.loads(payload_bytes)
            await self._mark_picked_up(payload["job_id"], worker_id)
            return payload

        return None

    async def _mark_picked_up(self, job_id: str, worker_id: str) -> None:
        """Mark a job as picked up by a worker."""
        job_key = f"{JOB_STATUS_PREFIX}{job_id}"
        await self.redis.hset(job_key, mapping={
            "status": "provisioning",
            "worker_id": worker_id,
            "picked_up_at": datetime.now(timezone.utc).isoformat(),
        })
        # Increment running count
        await self.redis.incr(CONCURRENCY_SEMAPHORE)

    # ── Job Status Updates ─────────────────────────────────────────

    async def update_job_status(
        self,
        job_id: uuid.UUID,
        status: str,
        extra: Optional[Dict[str, str]] = None,
    ) -> None:
        """Update job status in Redis hash."""
        job_key = f"{JOB_STATUS_PREFIX}{job_id}"
        mapping: Dict[str, str] = {"status": status}
        if extra:
            mapping.update(extra)
        await self.redis.hset(job_key, mapping=mapping)

        # If job is terminal, decrement concurrency
        if status in ("passed", "failed", "cancelled", "timed_out", "infrastructure_error"):
            await self.redis.decr(CONCURRENCY_SEMAPHORE)

    async def get_job_status(self, job_id: uuid.UUID) -> Optional[Dict[str, str]]:
        """Get job status from Redis hash."""
        job_key = f"{JOB_STATUS_PREFIX}{job_id}"
        return await self.redis.hgetall(job_key)

    # ── Cancellation ───────────────────────────────────────────────

    async def cancel_job(self, job_id: uuid.UUID) -> bool:
        """Publish a cancellation signal for a running job.

        Workers subscribed to the cancel channel will receive the signal
        and terminate the container.
        """
        await self.redis.publish(
            CANCEL_CHANNEL,
            json.dumps({"job_id": str(job_id), "action": "cancel"}),
        )
        # Also update Redis status so dequeue doesn't pick it up
        await self.update_job_status(job_id, "cancelled", {
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Cancellation signal published for job %s", job_id)
        return True

    # ── Worker Heartbeat ───────────────────────────────────────────

    async def worker_heartbeat(self, worker_id: str, metadata: Optional[Dict] = None) -> None:
        """Register a worker heartbeat (TTL-based liveness)."""
        key = f"{WORKER_HEARTBEAT_PREFIX}{worker_id}"
        payload = json.dumps({
            "worker_id": worker_id,
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        })
        # 30-second TTL — worker must re-heartbeat within this window
        await self.redis.set(key, payload, ex=30)

    async def get_active_workers(self) -> list[Dict[str, Any]]:
        """List all workers with active heartbeats."""
        pattern = f"{WORKER_HEARTBEAT_PREFIX}*"
        keys = []
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)
        workers = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                workers.append(json.loads(data))
        return workers

    # ── Concurrency ────────────────────────────────────────────────

    async def _running_count(self) -> int:
        """Get the current number of running jobs."""
        val = await self.redis.get(CONCURRENCY_SEMAPHORE)
        return int(val) if val else 0

    async def available_slots(self) -> int:
        """Get the number of available execution slots."""
        running = await self._running_count()
        return max(0, self.max_concurrent - running)

    # ── Cleanup ────────────────────────────────────────────────────

    async def cleanup_job(self, job_id: uuid.UUID) -> None:
        """Remove job metadata from Redis after completion."""
        job_key = f"{JOB_STATUS_PREFIX}{job_id}"
        await self.redis.delete(job_key)


def get_queue(redis: aioredis.Redis, max_concurrent: int = 4) -> ExecutionQueue:
    """Factory: create an ExecutionQueue bound to a Redis connection."""
    return ExecutionQueue(redis=redis, max_concurrent=max_concurrent)
