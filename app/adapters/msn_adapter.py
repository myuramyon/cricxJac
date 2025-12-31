import os
import asyncio
import random
import logging
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from .base import LiveFeedAdapter

LOG = logging.getLogger(__name__)

class MSNAdapter(LiveFeedAdapter):
    """Adapter targeting MSN Cricket live sections (https://www.msn.com/en-in/sports/cricket/).

    It will try a configurable JSON endpoint if provided (config['url']), otherwise fetch
    the MSN cricket page and attempt to extract internal JSON blobs or simplified score info.

    Config options:
      - url: optional, direct JSON endpoint
      - poll_interval, jitter, user_agents
    """

    def __init__(self, callback, config: Optional[dict] = None, poll_interval: int = 60):
        super().__init__(callback, config=config, poll_interval=poll_interval)
        self.url = (config.get('url') if config and 'url' in config else os.getenv('MSN_CRICKET_URL', 'https://www.msn.com/en-in/sports/cricket'))
        self._client = httpx.AsyncClient(timeout=20)

    def capabilities(self):
        return {'live': True, 'fallback': True}

    async def start(self):
        self._running = True
        while self._running:
            try:
                self._pick_user_agent()
                headers = {'User-Agent': self.user_agent}
                r = await self._client.get(self.url, headers=headers)
                if r.status_code == 200:
                    # Attempt to parse JSON if content-type says so
                    ct = r.headers.get('content-type', '')
                    if 'application/json' in ct:
                        payload = r.json()
                        events = payload.get('events', []) if isinstance(payload, dict) else []
                    else:
                        # Parse HTML and try to extract score blocks
                        soup = BeautifulSoup(r.text, 'html.parser')
                        events = self._parse_html_for_events(soup)
                    for raw in events:
                        evt = None
                        try:
                            evt = self.on_event(raw)
                        except Exception as e:
                            LOG.exception('msn_adapter normalization error: %s', e)
                        if evt:
                            self._validate_and_emit(evt)
                        self.mark_healthy()
                else:
                    LOG.warning('msn_adapter got status %s', r.status_code)
                    self.mark_unhealthy()
            except Exception as e:
                LOG.exception('msn_adapter error: %s', e)
                self.mark_unhealthy()
            await self._sleep_with_jitter()

    def stop(self):
        self._running = False

    def _parse_html_for_events(self, soup: BeautifulSoup):
        # Best-effort parser: find matches or score items and produce simplified event dicts
        events = []
        # Example: look for elements with data attributes or score blocks
        for card in soup.select('.card, .match-card'):
            try:
                text = card.get_text(separator=' ', strip=True)
                # Simple heuristic: skip if it doesn't look like a live ball
                if 'over' in text.lower() or 'run' in text.lower():
                    # This is a simplification; real parsing would be more detailed
                    events.append({'match_id': card.get('id') or 'msn', 'timestamp': None, 'raw_text': text})
            except Exception:
                continue
        return events

    def on_event(self, data: dict) -> Optional[dict]:
        # Try to normalize minimal information. If it's just raw_text, skip emitting as Event
        if 'runs' in data or 'over' in data or 'ball' in data:
            try:
                return {
                    'match_id': str(data.get('match_id', 'msn')),
                    'timestamp': data.get('timestamp'),
                    'inning': int(data.get('inning', 1)),
                    'over': int(data.get('over', 0)),
                    'ball': int(data.get('ball', 1)),
                    'batsman': data.get('batsman', '') or data.get('striker', ''),
                    'non_striker': data.get('non_striker', ''),
                    'bowler': data.get('bowler', ''),
                    'runs': int(data.get('runs', 0)),
                    'extras': int(data.get('extras', 0)),
                    'is_wicket': bool(data.get('is_wicket', False)),
                    'wicket_type': data.get('wicket_type'),
                    'wicket_player': data.get('wicket_player'),
                    'notes': data.get('raw_text')
                }
            except Exception as e:
                LOG.exception('msn_adapter normalize error: %s', e)
                return None
        # Not parsable as ball event
        return None
