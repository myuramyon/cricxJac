import asyncio
import json
import os
from typing import Callable
from app.adapters.base import LiveFeedAdapter

class SampleFileAdapter(LiveFeedAdapter):
    def __init__(self, callback: Callable[[dict], None], path: str, delay: float = 1.0):
        super().__init__(callback, config={'poll_interval': delay})
        self.path = path
        self.delay = delay

    async def start(self):
        if not os.path.exists(self.path):
            return
        self._running = True
        with open(self.path) as fh:
            for line in fh:
                if not self._running:
                    break
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                evt = self.on_event(data)
                if evt:
                    self._validate_and_emit(evt)
                await asyncio.sleep(self.delay)

    def stop(self):
        self._running = False

    def on_event(self, data: dict) -> dict:
        # sample file already contains events matching our schema; return as-is
        return data

    def capabilities(self):
        return {'sample': True, 'live': False}

# placeholder for generic provider adapter — uses LiveFeedAdapter contract
class ProviderAdapter(LiveFeedAdapter):
    def __init__(self, callback: Callable[[dict], None], provider_cfg: dict):
        super().__init__(callback, config=provider_cfg)
        self.cfg = provider_cfg

    async def start(self):
        # Example: poll provider endpoint and call callback on new events
        import httpx
        url = self.cfg.get('url') or os.getenv('LIVE_FEED_URL')
        interval = float(self.cfg.get('interval', self.poll_interval))
        async with httpx.AsyncClient() as client:
            self._running = True
            while self._running:
                try:
                    r = await client.get(url, headers={'User-Agent': self.user_agent})
                    if r.status_code == 200:
                        payload = r.json()
                        for e in payload.get('events', []):
                            evt = self.on_event(e) if hasattr(self, 'on_event') else e
                            if evt:
                                self._validate_and_emit(evt)
                except Exception as e:
                    print('ProviderAdapter error', e)
                await asyncio.sleep(interval)

    def stop(self):
        self._running = False
