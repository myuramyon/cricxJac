import os
import asyncio
import random
from typing import Optional
import httpx
from .base import LiveFeedAdapter

class CricbuzzAdapter(LiveFeedAdapter):
    """Adapter that polls a Cricbuzz-compatible live endpoint (or a local ekamid/cricbuzz-live service).

    Config options (env or config dict):
    - LIVE_CRICBUZZ_URL: endpoint returning JSON {events: [...]}
    - poll_interval (seconds)
    - jitter (seconds)
    - CRICBUZZ_USER_AGENT: custom user agent

    NOTE: Scraping Cricbuzz directly may violate Terms of Service. Prefer an approved API or a local
    instance of ekamid/cricbuzz-live you control. The adapter uses a User-Agent header and randomized
    jitter between polls to reduce scraping impact.
    """

    def __init__(self, callback, config: Optional[dict] = None, poll_interval: int = 60):
        super().__init__(callback, config=config, poll_interval=poll_interval)
        self.url = config.get('url') if config and 'url' in config else os.getenv('LIVE_CRICBUZZ_URL')
        if not self.url:
            raise ValueError('CricbuzzAdapter requires LIVE_CRICBUZZ_URL in config or env')
        # Allow overriding user agent via env
        self.user_agent = os.getenv('CRICBUZZ_USER_AGENT', self.user_agent)

    def capabilities(self):
        return {'live': True, 'ball_by_ball': True}

    async def start(self):
        async with httpx.AsyncClient(timeout=30) as client:
            self._running = True
            while self._running:
                try:
                    headers = {'User-Agent': self.user_agent}
                    r = await client.get(self.url, headers=headers)
                    if r.status_code == 200:
                        ct = r.headers.get('content-type', '')
                        if 'application/json' in ct:
                            payload = r.json()
                            events = payload.get('events') or payload.get('data') or []
                            for raw in events:
                                try:
                                    evt = self.on_event(raw)
                                    if evt:
                                        self._validate_and_emit(evt)
                                except Exception as e:
                                    print('cricbuzz_adapter on_event error', e)
                        else:
                            # Non-JSON responses (HTML) are ignored by default to avoid scraping complexity
                            print('cricbuzz_adapter: non-json response, skipping')
                    else:
                        print('cricbuzz_adapter: bad status', r.status_code)
                except Exception as e:
                    print('cricbuzz_adapter error', e)
                await self._sleep_with_jitter()

    def on_event(self, data: dict) -> Optional[dict]:
        # Map likely keys from cricbuzz/ekamid feed into our Event schema
        try:
            match_id = data.get('match_id') or data.get('mid') or data.get('match')
            timestamp = data.get('timestamp') or data.get('time')
            inning = int(data.get('inning', 1))
            over = int(data.get('over', data.get('over_num', 0)))
            ball = int(data.get('ball', data.get('ball_num', 1)))
            batsman = data.get('batsman') or data.get('striker') or ''
            non_striker = data.get('non_striker') or data.get('nonStriker') or ''
            bowler = data.get('bowler') or data.get('bowling') or ''
            runs = int(data.get('runs', 0))
            extras = int(data.get('extras', 0))
            is_wicket = bool(data.get('is_wicket', data.get('wicket', False)))
            wicket_type = data.get('wicket_type') or data.get('how')
            wicket_player = data.get('wicket_player') or data.get('player_out')
            notes = data.get('note') or data.get('desc')

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
                'notes': notes,
            }
        except Exception as e:
            print('cricbuzz_adapter normalize error', e)
            return None
