from collections import deque, defaultdict
from .models import Event, BallSummary, MatchState
from typing import Dict

class MatchStateManager:
    def __init__(self, recent_balls=24):
        # per match state
        self._states: Dict[str, Dict] = {}
        self.recent_balls = recent_balls

    def apply_event(self, event: Event):
        m = event.match_id
        st = self._states.setdefault(m, {
            'match_id': m,
            'inning': event.inning,
            'total_runs': 0,
            'wickets': 0,
            'balls': 0,
            'last_balls': deque(maxlen=self.recent_balls),
        })
        # update
        runs = event.runs + event.extras
        st['total_runs'] += runs
        if event.is_wicket:
            st['wickets'] += 1
        # count ball
        st['balls'] += 1
        st['last_balls'].append({
            'over': event.over,
            'ball': event.ball,
            'batsman': event.batsman,
            'bowler': event.bowler,
            'runs': event.runs,
            'extras': event.extras,
            'is_wicket': event.is_wicket,
        })
        return self.snapshot(m)

    def snapshot(self, match_id: str):
        st = self._states.get(match_id)
        if not st:
            return None
        overs = st['balls'] // 6 + (st['balls'] % 6) / 6.0
        return MatchState(
            match_id=st['match_id'],
            inning=st['inning'],
            total_runs=st['total_runs'],
            wickets=st['wickets'],
            overs=round(overs, 1),
            last_balls=[BallSummary(**b) for b in list(st['last_balls'])]
        )

    def get_raw_state(self, match_id: str):
        return self._states.get(match_id)
