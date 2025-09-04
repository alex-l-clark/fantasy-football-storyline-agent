"""Player data models."""

from typing import Optional
from pydantic import BaseModel


class Player(BaseModel):
    """NFL player model."""
    
    player_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    team: Optional[str] = None
    number: Optional[int] = None
    age: Optional[int] = None
    fantasy_positions: Optional[list[str]] = None
    
    @classmethod
    def from_api_response(cls, player_id: str, data: dict) -> "Player":
        """Create Player from API response."""
        return cls(
            player_id=player_id,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            position=data.get("position"),
            team=data.get("team"),
            number=data.get("number"),
            age=data.get("age"),
            fantasy_positions=data.get("fantasy_positions")
        )
    
    @property
    def full_name(self) -> str:
        """Get player's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.last_name:
            return self.last_name
        elif self.first_name:
            return self.first_name
        else:
            return "Unknown Player"
    
    @property
    def display_position(self) -> str:
        """Get display-friendly position."""
        return self.position or "N/A"
    
    @property
    def display_team(self) -> str:
        """Get display-friendly team."""
        return self.team or "N/A"