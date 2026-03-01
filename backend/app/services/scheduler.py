"""
APScheduler job definitions with idempotency locks.

Jobs:
- News fetch: every 30 minutes
- Stock refresh: every 5 min during market hours, 1h after
- Recommendation recalculation: every 1 hour
- Inspiration refresh: daily
"""


# TODO: Implement in Phase 7
# - create_scheduler() -> AsyncIOScheduler
# - Job definitions with idempotency via scheduler_locks table
