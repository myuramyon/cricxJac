from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Event(BaseModel):
    match_id: str
    timestamp: datetime
    inning: int
    over: int
    ball: int
    batsman: str
    non_striker: str
    bowler: str
    runs: int = Field(ge=0)
    extras: int = Field(ge=0)
    is_wicket: bool = False
    wicket_type: Optional[str] = None
    wicket_player: Optional[str] = None
    notes: Optional[str] = None

class BallSummary(BaseModel):
    over: int
    ball: int
    batsman: str
    bowler: str
    runs: int
    extras: int
    is_wicket: bool

class MatchState(BaseModel):
    match_id: str
    inning: int
    total_runs: int
    wickets: int
    overs: float
    last_balls: list[BallSummary] = []
