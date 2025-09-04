"""Roster data models."""

from typing import Optional
from pydantic import BaseModel


class Roster(BaseModel):
    """Sleeper roster model."""
    
    roster_id: int
    owner_id: str
    league_id: str
    players: list[str]
    starters: list[str]
    reserve: Optional[list[str]] = None
    taxi: Optional[list[str]] = None
    settings: Optional[dict] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> "Roster":
        """Create Roster from API response."""
        return cls(
            roster_id=data["roster_id"],
            owner_id=data["owner_id"],
            league_id=data.get("league_id", ""),
            players=data.get("players", []),
            starters=data.get("starters", []),
            reserve=data.get("reserve"),
            taxi=data.get("taxi"),
            settings=data.get("settings")
        )
    
    def get_player_status(self, player_id: str) -> str:
        """Get status of a player on this roster."""
        if player_id in self.starters:
            return "starter"
        elif player_id in self.players:
            return "bench"
        else:
            return "active"