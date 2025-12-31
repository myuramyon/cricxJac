import os
from fastapi.testclient import TestClient
from app.main import app


def test_health_endpoint_sample_primary(monkeypatch):
    monkeypatch.setenv('LIVE_FEED_PROVIDERS', 'sample')
    monkeypatch.setenv('LIVE_FEED_PRIMARY_PROVIDERS', 'sample')
    monkeypatch.setenv('SAMPLE_FEED_PATH', 'samples/sample_feed.jsonl')
    with TestClient(app) as client:
        r = client.get('/health')
        assert r.status_code == 200
        assert r.json().get('status') == 'ok'
