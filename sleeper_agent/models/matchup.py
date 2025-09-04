"""Matchup data models."""

from typing import Optional
from pydantic import BaseModel


class Matchup(BaseModel):
    """Sleeper matchup model."""
    
    roster_id: int
    matchup_id: Optional[int] = None
    points: Optional[float] = None
    players_points: Optional[dict] = None
    starters: Optional[list[Optional[str]]] = None
    starters_points: Optional[list[Optional[float]]] = None
    custom_points: Optional[float] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> "Matchup":
        """Create Matchup from API response."""
        return cls(
            roster_id=data["roster_id"],
            matchup_id=data.get("matchup_id"),
            points=data.get("points"),
            players_points=data.get("players_points", {}),
            starters=data.get("starters", []),
            starters_points=data.get("starters_points", []),
            custom_points=data.get("custom_points")
        )
    
    @property
    def has_bye(self) -> bool:
        """Check if this is a bye week (no matchup_id)."""
        return self.matchup_id is None
    
    @property
    def projected_points(self) -> Optional[float]:
        """Get projected points (custom_points if available, otherwise None)."""
        return self.custom_points
    
    @property
    def actual_points(self) -> Optional[float]:
        """Get actual points scored."""
        return self.points
    
    def get_starters_list(self) -> list[str]:
        """Get list of starter player IDs, filtering out None and empty values."""
        if not self.starters:
            return []
        return [player_id for player_id in self.starters if player_id is not None and player_id != ""]