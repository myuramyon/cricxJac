import pytest
from app.adapters.cricbuzz_adapter import CricbuzzAdapter
from app.adapters.cricketapi_adapter import CricketAPIAdapter
from app.adapters.ipl_adapter import IPLAdapter
from app.adapters.pycricket_adapter import PyCricketAdapter
from app.models import Event
from datetime import datetime


def test_cricbuzz_on_event_normalization():
    cb = lambda e: None
    # Minimal config with dummy URL (we won't call start())
    adapter = CricbuzzAdapter(cb, config={'url': 'http://example.local/feed', 'poll_interval': 60})
    raw = {
        'match_id': 'M1',
        'timestamp': '2025-12-31T10:00:00Z',
        'inning': 1,
        'over': 0,
        'ball': 2,
        'batsman': 'A',
        'non_striker': 'B',
        'bowler': 'X',
        'runs': 4,
        'extras': 0,
        'is_wicket': False
    }
    out = adapter.on_event(raw)
    assert out is not None
    ev = Event(**out)
    assert ev.runs == 4
    assert ev.batsman == 'A'


def test_cricketapi_on_event_filters_non_ball_payload():
    cb = lambda e: None
    adapter = CricketAPIAdapter(cb, config={'url': 'http://example.local', 'api_key': 'k', 'poll_interval': 60})
    # Non ball payload (metadata only) should return None
    raw_meta = {'match_id': 'M1', 'status': 'scheduled'}
    assert adapter.on_event(raw_meta) is None
    # Ball payload
    raw_ball = {'match_id': 'M1', 'timestamp': '2025-12-31T10:00:00Z', 'over': 1, 'ball': 1, 'runs': 2, 'batsman': 'A', 'bowler': 'X'}
    out = adapter.on_event(raw_ball)
    assert out is not None
    Event(**out)


def test_ipl_on_event_emits_ball_event():
    cb = lambda e: None
    adapter = IPLAdapter(cb, config={'url': 'http://example.local/ipl', 'poll_interval': 3600})
    raw = {'match_id': 'IPL1', 'timestamp': '2025-12-31T10:00:00Z', 'over': 3, 'ball': 2, 'runs': 1, 'batsman': 'C', 'bowler': 'Y'}
    out = adapter.on_event(raw)
    assert out is not None
    Event(**out)


def test_pycricket_adapter_no_lib_returns_none():
    cb = lambda e: None
    adapter = PyCricketAdapter(cb, config={'poll_interval': 60})
    # With no pycricket library installed, on_event should safely return None
    assert adapter.on_event({'some': 'data'}) is None
