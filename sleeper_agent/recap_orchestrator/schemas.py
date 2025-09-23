"""Pydantic schemas for the recap orchestrator."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Union, Any

class PlayerDetail(BaseModel):
    player_id: str
    player_name: Optional[str] = None
    position: Optional[str] = None
    nfl_team: Optional[str] = None
    fantasy_points: Optional[float] = None
    is_starter: bool = False

class TeamRoster(BaseModel):
    team_name: str
    roster: List[str]  # Keep for backward compatibility
    starters: Optional[List[str]] = None  # Keep for backward compatibility
    bench: Optional[List[str]] = None  # Keep for backward compatibility
    players: Optional[List[PlayerDetail]] = None  # New detailed player info

class Matchup(BaseModel):
    week: int
    team_a: str
    team_b: str
    team_a_score: float
    team_b_score: float
    winner: str
    loser: str

class Record(BaseModel):
    team_name: str
    record: str  # e.g., "1-0", "0-1", "1-1", etc.
    points_for: Optional[float] = None  # Total points scored through this week
    points_against: Optional[float] = None  # Total points allowed through this week

class Step0Truth(BaseModel):
    league_name: Optional[str] = None
    season: int
    week: int
    teams: List[TeamRoster]
    matchups: List[Matchup]
    records_after_week: List[Record]
    issues: Optional[List[str]] = None

class SeasonOutlook(BaseModel):
    trajectory: Optional[str] = None                # trending up/down, usage changes
    role_security: Optional[str] = None             # snap share, depth chart position
    boom_bust_profile: Optional[str] = None         # ceiling vs floor, volatility
    ros_projection: Optional[str] = None            # rest of season outlook
    breakout_potential: Optional[str] = None        # upside assessment
    schedule_analysis: Optional[str] = None         # upcoming matchups, playoff schedule
    advanced_metrics: Optional[str] = None          # target share, air yards, etc.

class PlayerEvidence(BaseModel):
    player: str
    team_name: str               # fantasy team name from Step 0
    is_starter: Optional[bool] = None
    week_stats: Dict[str, Union[float, int]] = Field(default_factory=dict)
    projection_context: Optional[str] = None
    season_outlook: Optional[SeasonOutlook] = None
    injury: Optional[Dict[str, str]] = None
    opportunity_notes: Optional[str] = None         # role changes, situational upside
    handcuff_value: Optional[str] = None            # backup/depth value analysis
    expert_analysis: Optional[str] = None           # analyst consensus and predictions
    advanced_notes: Optional[str] = None
    quotes: Optional[List[Dict[str, str]]] = None   # multiple expert quotes
    quote: Optional[str] = None                     # legacy single quote support
    quote_source_id: Optional[int] = None
    kickoff_window: Optional[Literal["TNF","Sun Early","Sun Late","SNF","MNF"]] = None

class Step1Evidence(BaseModel):
    player_evidence: List[PlayerEvidence]
    references: List[Dict[str, Any]]   # {id, title, url, publisher, date} - id can be int or str

class Step4Issue(BaseModel):
    type: str
    location_snippet: str
    fix_instruction: str

class Step4Audit(BaseModel):
    status: Literal["PASS","FAIL"]
    issues: Optional[List[Step4Issue]] = None