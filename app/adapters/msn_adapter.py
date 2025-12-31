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
        allow_scrape = bool(self.config.get('allow_scrape', os.getenv('ALLOW_SCRAPE_MSN', 'false').lower() in ('1','true','yes')))
        while self._running:
            try:
                self._pick_user_agent()
                headers = {'User-Agent': self.user_agent}
                r = await self._client.get(self.url, headers=headers)
                if r.status_code == 200:
                    # Attempt to parse JSON if content-type says so
                    ct = r.headers.get('content-type', '')
                    events = []
                    if 'application/json' in ct:
                        payload = r.json()
                        events = payload.get('events', []) if isinstance(payload, dict) else []
                        self.mark_healthy()
                    else:
                        if not allow_scrape:
                            LOG.warning('msn_adapter received HTML but scraping is disabled; set ALLOW_SCRAPE_MSN to enable')
                            self.mark_unhealthy()
                            await self._sleep_with_jitter()
                            continue
                        # Parse HTML and try to extract JSON blobs for events
                        json_blobs = self._extract_json_from_html(r.text)
                        for blob in json_blobs:
                            if isinstance(blob, dict) and blob.get('events'):
                                events.extend(blob.get('events'))
                            elif isinstance(blob, list):
                                events.extend(blob)
                        # fallback to simple HTML heuristics too
                        events.extend(self._parse_html_for_events(BeautifulSoup(r.text, 'html.parser')))
                        if events:
                            self.mark_healthy()
                        else:
                            self.mark_unhealthy()
                    for raw in events:
                        evt = None
                        try:
                            evt = self.on_event(raw)
                        except Exception as e:
                            LOG.exception('msn_adapter normalization error: %s', e)
                        if evt:
                            self._validate_and_emit(evt)
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
        for card in soup.select('.card, .match-card, .score-block'):
            try:
                text = card.get_text(separator=' ', strip=True)
                # Simple heuristic: skip if it doesn't look like a live ball
                if 'over' in text.lower() or 'run' in text.lower() or 'wicket' in text.lower():
                    # This is a simplification; real parsing would be more detailed
                    events.append({'match_id': card.get('id') or 'msn', 'timestamp': None, 'raw_text': text})
            except Exception:
                continue
        return events

    def _extract_json_from_html(self, html: str):
        """Try to extract embedded JSON blobs from MSN pages.

        Strategies:
        - Look for <script type="application/ld+json"> blocks and parse their JSON
        - Search for JS assignment patterns like `window.__DATA__ = {...}` or `initialState = {...}`
        Returns list of parsed JSON objects (dict or list)
        """
        import re
        import json
        blobs = []
        # parse type=application/ld+json
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup.find_all('script', type='application/ld+json'):
                try:
                    parsed = json.loads(tag.string)
                    blobs.append(parsed)
                except Exception:
                    continue
        except Exception:
            pass

        # search for JS assignment patterns
        patterns = [r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', r'window\.__DATA__\s*=\s*(\{.*?\});', r'initialState\s*=\s*(\{.*?\});']
        for pat in patterns:
            try:
                m = re.search(pat, html, flags=re.S)
                if m:
                    j = m.group(1)
                    try:
                        parsed = json.loads(j)
                        blobs.append(parsed)
                    except Exception:
                        # try to fix trailing semicolon or JS-style object
                        try:
                            j2 = j.rstrip(';')
                            parsed = json.loads(j2)
                            blobs.append(parsed)
                        except Exception:
                            continue
            except Exception:
                continue
        return blobs

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
