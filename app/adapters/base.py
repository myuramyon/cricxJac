from abc import ABC, abstractmethod
from typing import Callable, Optional, List
import asyncio
import random
import os
from pydantic import ValidationError
from ..models import Event

class LiveFeedAdapter(ABC):
    """Abstract base class for all adapters.

    Subclasses must implement:
    - async start()
    - on_event(data: dict) -> dict | None  # should return normalized event dict matching app.models.Event
    - capabilities() -> dict

    The base class provides a small helper to run polling loops with jitter and
    basic validation. Use `self.callback` to forward validated events.
    """

    def __init__(self, callback: Callable[[dict], None], config: Optional[dict] = None, poll_interval: int = 60):
        self.callback = callback
        self.config = config or {}
        self.poll_interval = int(self.config.get('poll_interval', poll_interval))
        self.jitter = float(self.config.get('jitter', 5.0))
        self._running = False
        self.user_agent = os.getenv('CRICBUZZ_USER_AGENT', 'cricxJac/0.1 (+https://example.com)')

    @abstractmethod
    async def start(self):
        """Start the feed/loop/connection."""
        raise NotImplementedError

    @abstractmethod
    def on_event(self, data: dict) -> Optional[dict]:
        """Normalize raw provider data into our Event *dict* (or return None)."""
        raise NotImplementedError

    @abstractmethod
    def capabilities(self) -> dict:
        """Return adapter capabilities e.g. {'live': True, 'metadata': False} """
        raise NotImplementedError

    async def _sleep_with_jitter(self):
        interval = self.poll_interval + random.uniform(0, self.jitter)
        await asyncio.sleep(interval)

    def _validate_and_emit(self, evt: dict):
        """Validate event structure by attempting to construct Event, then call callback with dict."""
        if not evt:
            return
        try:
            e = Event(**evt)
            self.callback(e.dict())
        except ValidationError as ve:
            # Log error — in production use logger
            print(f"Event validation error: {ve}")
        except Exception as e:
            print(f"Unknown error validating event: {e}")

    def stop(self):
        self._running = False
