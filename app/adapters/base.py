from abc import ABC, abstractmethod
from typing import Callable, Optional
import asyncio
import random
import os
import logging
from pydantic import ValidationError
from ..models import Event

LOG = logging.getLogger(__name__)

class LiveFeedAdapter(ABC):
    """Abstract base class for all adapters.

    Required methods:
      - async start(): run polling/scrape loop until stopped
      - stop(): stop the adapter
      - is_healthy() -> bool: returns health state
      - on_event(data: dict) -> dict|None: normalize raw data into Event-like dict
    """

    def __init__(self, callback: Callable[[dict], None], config: Optional[dict] = None, poll_interval: int = 60):
        self.callback = callback
        self.config = config or {}
        self.poll_interval = int(self.config.get('poll_interval', poll_interval))
        self.jitter = float(self.config.get('jitter', 5.0))
        self._running = False
        self._healthy = True
        self.user_agents = self.config.get('user_agents', [os.getenv('CRICBUZZ_USER_AGENT', 'cricxJac/0.1 (+https://example.com)')])
        self.user_agent = random.choice(self.user_agents)

    @abstractmethod
    async def start(self):
        """Start the adapter's polling/stream loop."""
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        """Stop the adapter gracefully."""
        raise NotImplementedError

    @abstractmethod
    def on_event(self, data: dict) -> Optional[dict]:
        """Normalize raw provider data into our Event *dict* (or return None)."""
        raise NotImplementedError

    def is_healthy(self) -> bool:
        """Return the current health state for this adapter."""
        return bool(self._healthy)

    async def _sleep_with_jitter(self):
        interval = self.poll_interval + random.uniform(0, self.jitter)
        LOG.debug('sleeping for %s seconds (poll=%s jitter=%s)', interval, self.poll_interval, self.jitter)
        await asyncio.sleep(interval)

    def _validate_and_emit(self, evt: dict):
        """Validate event structure by constructing Event, then call callback with dict."""
        if not evt:
            return
        try:
            e = Event(**evt)
            # use model_dump for Pydantic v2
            try:
                payload = e.model_dump()
            except Exception:
                payload = e.dict()
            self.callback(payload)
        except ValidationError as ve:
            LOG.warning('Event validation error: %s', ve)
        except Exception as e:
            LOG.exception('Unknown error validating event: %s', e)

    def _pick_user_agent(self):
        self.user_agent = random.choice(self.user_agents)

    def mark_unhealthy(self):
        self._healthy = False

    def mark_healthy(self):
        self._healthy = True
