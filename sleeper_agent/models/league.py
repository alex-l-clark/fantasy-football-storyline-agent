"""League data models."""

from typing import Optional
from pydantic import BaseModel


class League(BaseModel):
    """Sleeper league model."""
    
    league_id: str
    name: str
    season: str
    status: str
    total_rosters: int
    scoring_settings: Optional[dict] = None
    roster_positions: Optional[list[str]] = None
    settings: Optional[dict] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> "League":
        """Create League from API response."""
        return cls(
            league_id=data["league_id"],
            name=data.get("name", "Unknown League"),
            season=data.get("season", "2025"),
            status=data.get("status", "unknown"),
            total_rosters=data.get("total_rosters", 0),
            scoring_settings=data.get("scoring_settings"),
            roster_positions=data.get("roster_positions"),
            settings=data.get("settings")
        )