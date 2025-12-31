import asyncio
import tempfile
import json
import os

from app.ingest import SampleFileAdapter


def test_sample_file_adapter_emits_events(tmp_path):
    # create temp sample file
    p = tmp_path / "test_feed.jsonl"
    lines = [
        json.dumps({"match_id":"T1","timestamp":"2025-12-31T10:00:00Z","inning":1,"over":0,"ball":1,"batsman":"A","non_striker":"B","bowler":"X","runs":0,"extras":0,"is_wicket":False}),
        json.dumps({"match_id":"T1","timestamp":"2025-12-31T10:00:10Z","inning":1,"over":0,"ball":2,"batsman":"A","non_striker":"B","bowler":"X","runs":4,"extras":0,"is_wicket":False}),
    ]
    p.write_text('\n'.join(lines))

    collected = []
    def cb(e):
        collected.append(e)

    adapter = SampleFileAdapter(cb, path=str(p), delay=0.01)

    asyncio.run(adapter.start())

    assert len(collected) == 2
    # Ensure keys present
    assert 'match_id' in collected[0]
    assert 'runs' in collected[1]
