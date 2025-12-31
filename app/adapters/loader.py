import os
from typing import List
from app.ingest import SampleFileAdapter, ProviderAdapter
from app.adapters.cricbuzz_adapter import CricbuzzAdapter
from app.adapters.cricketapi_adapter import CricketAPIAdapter
from app.adapters.ipl_adapter import IPLAdapter
from app.adapters.pycricket_adapter import PyCricketAdapter


def load_adapters(callback) -> List:
    """Create adapter instances based on environment configuration.

    Environment variables:
    - LIVE_FEED_PROVIDERS: comma-separated providers (sample,cricbuzz,cricketapi,ipl,pycricket)
    - SAMPLE_FEED_PATH
    - LIVE_FEED_POLL_INTERVAL
    - LIVE_CRICBUZZ_URL
    - CRICKETAPI_URL / CRICKETAPI_KEY
    - IPL_STATS_URL / IPL_STATS_UPDATE_FREQUENCY
    """
    providers = os.getenv('LIVE_FEED_PROVIDERS', 'sample')
    providers = [p.strip().lower() for p in providers.split(',') if p.strip()]
    adapters = []

    for p in providers:
        if p == 'sample':
            path = os.getenv('SAMPLE_FEED_PATH', 'samples/sample_feed.jsonl')
            interval = float(os.getenv('LIVE_FEED_POLL_INTERVAL', '1'))
            adapters.append(SampleFileAdapter(callback, path=path, delay=interval))
        elif p == 'cricbuzz':
            url = os.getenv('LIVE_CRICBUZZ_URL')
            cfg = {'url': url, 'poll_interval': int(os.getenv('LIVE_FEED_POLL_INTERVAL', '60'))}
            adapters.append(CricbuzzAdapter(callback, config=cfg))
        elif p == 'cricketapi':
            cfg = {'url': os.getenv('CRICKETAPI_URL'), 'api_key': os.getenv('CRICKETAPI_KEY'), 'poll_interval': int(os.getenv('LIVE_FEED_POLL_INTERVAL', '60'))}
            adapters.append(CricketAPIAdapter(callback, config=cfg))
        elif p == 'ipl':
            cfg = {'url': os.getenv('IPL_STATS_URL'), 'poll_interval': int(os.getenv('IPL_STATS_UPDATE_FREQUENCY', '3600'))}
            adapters.append(IPLAdapter(callback, config=cfg))
        elif p == 'pycricket':
            adapters.append(PyCricketAdapter(callback, config={'poll_interval': int(os.getenv('LIVE_FEED_POLL_INTERVAL', '60'))}))
        else:
            print(f"Unknown provider in LIVE_FEED_PROVIDERS: {p}")
    return adapters
