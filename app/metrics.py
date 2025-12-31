from .engine import MatchStateManager
import math

# Simple metrics implementation

def batsman_dominance(last_balls):
    # returns runs and balls per batsman in last_balls
    stats = {}
    for b in last_balls:
        name = b['batsman']
        stats.setdefault(name, {'runs': 0, 'balls': 0})
        stats[name]['runs'] += b['runs']
        stats[name]['balls'] += 1
    # convert to strike rates
    out = {k: (v['runs'], (v['runs'] / v['balls'] * 100) if v['balls'] else 0) for k, v in stats.items()}
    return out


def momentum_score(last_balls):
    # weighted runs over last 6/12/24 balls
    weights = [1.0, 0.8, 0.6, 0.4, 0.2, 0.1]
    s = 0.0
    for i, b in enumerate(reversed(last_balls)):
        w = weights[i] if i < len(weights) else 0.05
        s += (b['runs'] - 0) * w
    return round(s, 2)


def win_probability_simple(state):
    # Simple heuristic: more runs and fewer wickets increases chance;
    # Not a real predictor — placeholder for MVP
    runs = state['total_runs']
    wickets = state['wickets']
    balls = state['balls']
    # normalize
    score = runs - (wickets * 10) - (balls / 10.0)
    prob = 1 / (1 + math.exp(-score / 50.0))
    return round(prob, 3)


def compute_metrics(raw_state):
    if not raw_state:
        return None
    last = list(raw_state.get('last_balls', []))
    return {
        'batsman_dominance': batsman_dominance(last),
        'momentum': momentum_score(last),
        'win_probability': win_probability_simple(raw_state)
    }