"""Draft data models."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class Draft(BaseModel):
    """Sleeper draft model."""
    
    draft_id: str
    league_id: str
    status: str
    type: str
    start_time: Optional[int] = None
    settings: Optional[dict] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> "Draft":
        """Create Draft from API response."""
        return cls(
            draft_id=data["draft_id"],
            league_id=data.get("league_id", ""),
            status=data.get("status", "unknown"),
            type=data.get("type", "unknown"),
            start_time=data.get("start_time"),
            settings=data.get("settings")
        )
    
    @property
    def start_datetime(self) -> Optional[datetime]:
        """Get draft start time as datetime."""
        if self.start_time:
            return datetime.fromtimestamp(self.start_time / 1000)
        return None


class DraftPick(BaseModel):
    """Sleeper draft pick model."""
    
    pick_no: int
    round: int
    draft_slot: int
    player_id: Optional[str] = None
    picked_by: str
    roster_id: int
    timestamp: Optional[int] = None
    metadata: Optional[dict] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> "DraftPick":
        """Create DraftPick from API response."""
        return cls(
            pick_no=data.get("pick_no", 0),
            round=data.get("round", 0),
            draft_slot=data.get("draft_slot", 0),
            player_id=data.get("player_id"),
            picked_by=data.get("picked_by", ""),
            roster_id=data.get("roster_id", 0),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata")
        )
    
    @property
    def timestamp_utc(self) -> Optional[datetime]:
        """Get pick timestamp as UTC datetime."""
        if self.timestamp:
            return datetime.fromtimestamp(self.timestamp / 1000)
        return None