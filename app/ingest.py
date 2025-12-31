import asyncio
import json
import os
from typing import Callable

class LiveFeedAdapter:
    """Base adapter interface. Implement `start` to push events to the callback.`"""
    def __init__(self, callback: Callable[[dict], None]):
        self.callback = callback

    async def start(self):
        raise NotImplementedError

class SampleFileAdapter(LiveFeedAdapter):
    def __init__(self, callback: Callable[[dict], None], path: str, delay: float = 1.0):
        super().__init__(callback)
        self.path = path
        self.delay = delay

    async def start(self):
        if not os.path.exists(self.path):
            return
        with open(self.path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                self.callback(data)
                await asyncio.sleep(self.delay)

# placeholder for provider adapter
class ProviderAdapter(LiveFeedAdapter):
    def __init__(self, callback: Callable[[dict], None], provider_cfg: dict):
        super().__init__(callback)
        self.cfg = provider_cfg

    async def start(self):
        # Example: poll provider endpoint and call callback on new events
        import httpx
        url = self.cfg.get('url')
        interval = float(self.cfg.get('interval', 2.0))
        async with httpx.AsyncClient() as client:
            while True:
                r = await client.get(url)
                if r.status_code == 200:
                    payload = r.json()
                    for e in payload.get('events', []):
                        self.callback(e)
                await asyncio.sleep(interval)
