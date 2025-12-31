import os
import asyncio
import httpx
from typing import Optional
from .base import LiveFeedAdapter

class CricketAPIAdapter(LiveFeedAdapter):
    """Adapter for sanwebinfo/cricket-api or similar provider.

    Config:
    - CRICKETAPI_URL (base url)
    - CRICKETAPI_KEY (optional)

    The adapter will poll a "live" endpoint and emit events if available; it also fetches
    match metadata and player/venue profiles for enrichment (but those are not emitted as Event objects).
    """

    def __init__(self, callback, config: Optional[dict] = None, poll_interval: int = 60):
        super().__init__(callback, config=config, poll_interval=poll_interval)
        self.base_url = (config.get('url') if config and 'url' in config else os.getenv('CRICKETAPI_URL'))
        self.api_key = (config.get('api_key') if config and 'api_key' in config else os.getenv('CRICKETAPI_KEY'))
        if not self.base_url:
            raise ValueError('CricketAPIAdapter requires CRICKETAPI_URL')

    def capabilities(self):
        return {'live': True, 'metadata': True, 'player_profiles': True}

    async def start(self):
        async with httpx.AsyncClient(timeout=20) as client:
            self._running = True
            while self._running:
                try:
                    url = f"{self.base_url.rstrip('/')}/live"
                    headers = {}
                    if self.api_key:
                        headers['Authorization'] = f"Bearer {self.api_key}"
                    r = await client.get(url, headers=headers)
                    if r.status_code == 200:
                        payload = r.json()
                        events = payload.get('events', []) or payload.get('data', [])
                        for e in events:
                            try:
                                evt = self.on_event(e)
                                if evt:
                                    self._validate_and_emit(evt)
                            except Exception as ee:
                                print('cricketapi_adapter event error', ee)
                    else:
                        print('cricketapi_adapter bad status', r.status_code)
                except Exception as e:
                    print('cricketapi_adapter error', e)
                await self._sleep_with_jitter()

    def on_event(self, data: dict) -> Optional[dict]:
        # Normalize provider event to our Event schema when ball-by-ball info exists
        try:
            if 'ball' not in data and 'over' not in data and 'runs' not in data:
                # Not a ball-by-ball payload — skip emitting an Event
                return None
            match_id = data.get('match_id') or data.get('match') or data.get('mid')
            timestamp = data.get('timestamp') or data.get('time')
            inning = int(data.get('inning', 1))
            over = int(data.get('over', 0))
            ball = int(data.get('ball', 1))
            batsman = data.get('batsman') or data.get('striker') or ''
            non_striker = data.get('non_striker') or ''
            bowler = data.get('bowler') or ''
            runs = int(data.get('runs', 0))
            extras = int(data.get('extras', 0))
            is_wicket = bool(data.get('is_wicket', data.get('wicket', False)))
            wicket_type = data.get('wicket_type')
            wicket_player = data.get('wicket_player')

            return {
                'match_id': str(match_id),
                'timestamp': timestamp,
                'inning': inning,
                'over': over,
                'ball': ball,
                'batsman': batsman,
                'non_striker': non_striker,
                'bowler': bowler,
                'runs': runs,
                'extras': extras,
                'is_wicket': is_wicket,
                'wicket_type': wicket_type,
                'wicket_player': wicket_player,
                'notes': data.get('note') or None,
            }
        except Exception as e:
            print('cricketapi_adapter normalize error', e)
            return None
