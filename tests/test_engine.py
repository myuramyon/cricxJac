import pytest
from app.engine import MatchStateManager
from app.models import Event
from datetime import datetime

def test_apply_event():
    m = MatchStateManager()
    ev = Event(match_id='T1', timestamp=datetime.utcnow(), inning=1, over=0, ball=1, batsman='A', non_striker='B', bowler='X', runs=4, extras=0, is_wicket=False)
    snap = m.apply_event(ev)
    assert snap.total_runs == 4
    assert snap.wickets == 0
    ev2 = Event(match_id='T1', timestamp=datetime.utcnow(), inning=1, over=0, ball=2, batsman='A', non_striker='B', bowler='X', runs=0, extras=0, is_wicket=True, wicket_player='A')
    snap2 = m.apply_event(ev2)
    assert snap2.wickets == 1
