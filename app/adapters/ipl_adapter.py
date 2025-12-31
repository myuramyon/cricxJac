import os
import asyncio
import httpx
from typing import Optional
from .base import LiveFeedAdapter

class IPLAdapter(LiveFeedAdapter):
    """Adapter to poll IPL-2025 stats repository endpoints to enrich IPL matches.

    This adapter is intended to provide team/player baseline stats (not necessarily ball-by-ball).
    When ball-by-ball data is present, it will emit Event objects; otherwise it updates cache via callbacks
    in the form of enrichment events (which may be consumed by other parts of the system).

    Config:
    - IPL_STATS_URL
    - IPL_STATS_UPDATE_FREQUENCY (seconds)
    """

    def __init__(self, callback, config: Optional[dict] = None, poll_interval: int = None):
        interval = int(config.get('poll_interval', int(os.getenv('IPL_STATS_UPDATE_FREQUENCY', '3600')))) if config else int(os.getenv('IPL_STATS_UPDATE_FREQUENCY', '3600'))
        super().__init__(callback, config=config, poll_interval=interval)
        self.base_url = (config.get('url') if config and 'url' in config else os.getenv('IPL_STATS_URL'))
        if not self.base_url:
            raise ValueError('IPLAdapter requires IPL_STATS_URL')

    def capabilities(self):
        return {'live': False, 'metadata': True, 'ipl_stats': True}

    async def start(self):
        async with httpx.AsyncClient(timeout=30) as client:
            self._running = True
            while self._running:
                try:
                    self._pick_user_agent()
                    r = await client.get(self.base_url, headers={'User-Agent': self.user_agent})
                    if r.status_code == 200:
                        payload = r.json()
                        # If provider contains events, emit them; else skip
                        for item in payload.get('events', []) or []:
                            evt = self.on_event(item)
                            if evt:
                                self._validate_and_emit(evt)
                        self.mark_healthy()
                    else:
                        LOG.warning('ipl_adapter bad status %s', r.status_code)
                        self.mark_unhealthy()
                except Exception as e:
                    LOG.exception('ipl_adapter error: %s', e)
                    self.mark_unhealthy()
                await self._sleep_with_jitter()

    def stop(self):
        self._running = False

    def on_event(self, data: dict) -> Optional[dict]:
        # If event is ball-by-ball, normalize; else skip emit
        if 'runs' in data and ('ball' in data or 'over' in data):
            try:
                return {
                    'match_id': str(data.get('match_id') or data.get('match')),
                    'timestamp': data.get('timestamp'),
                    'inning': int(data.get('inning', 1)),
                    'over': int(data.get('over', 0)),
                    'ball': int(data.get('ball', 1)),
                    'batsman': data.get('batsman', ''),
                    'non_striker': data.get('non_striker', ''),
                    'bowler': data.get('bowler', ''),
                    'runs': int(data.get('runs', 0)),
                    'extras': int(data.get('extras', 0)),
                    'is_wicket': bool(data.get('is_wicket', False)),
                    'wicket_type': data.get('wicket_type'),
                    'wicket_player': data.get('wicket_player'),
                    'notes': data.get('note')
                }
            except Exception as e:
                LOG.exception('ipl_adapter normalize error: %s', e)
                return None
        # Not a ball event; skip for Event emission
        return None
