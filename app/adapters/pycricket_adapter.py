import os
import asyncio
from typing import Optional
from .base import LiveFeedAdapter

try:
    # `py-cricket` library; if available, we'll use it for parsing/enriching
    import pycricket
except Exception:
    pycricket = None

class PyCricketAdapter(LiveFeedAdapter):
    """Adapter that leverages roanuz/py-cricket utilities to parse and enrich events.

    This adapter is primarily utility-focused: it can subscribe to raw events (via callback)
    and emit normalized events after parsing/deriving additional fields using pycricket.
    """

    def __init__(self, callback, config: Optional[dict] = None, poll_interval: int = 60):
        super().__init__(callback, config=config, poll_interval=poll_interval)
        self._running = False

    def capabilities(self):
        return {'utilities': True, 'parsing': True, 'derived_stats': True}

    async def start(self):
        # Nothing to poll by default; adapter functions are used programmatically by other adapters.
        # We keep a sleeping loop so the lifecycle is consistent.
        self._running = True
        while self._running:
            await self._sleep_with_jitter()

    def stop(self):
        self._running = False

    def on_event(self, data: dict) -> Optional[dict]:
        # If pycricket is present, attempt to parse and enrich
        try:
            if not pycricket:
                # library not available — no-op (could return data as-is if already normalized)
                return None
            # Example: use pycricket to parse a ball summary (details depend on library API)
            # This is a best-effort placeholder; adapt if specific pycricket APIs are known.
            if hasattr(pycricket, 'parse_ball'):
                parsed = pycricket.parse_ball(data)
                # Expect parsed dict to contain keys compatible with our Event schema
                return parsed
            # If library doesn't have parse_ball, just return None
            return None
        except Exception as e:
            LOG.exception('pycricket_adapter error: %s', e)
            return None
