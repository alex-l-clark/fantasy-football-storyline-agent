"""User data models."""

from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    """Sleeper user model."""
    
    user_id: str
    username: str
    display_name: Optional[str] = None
    team_name: Optional[str] = None
    avatar: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> "User":
        """Create User from API response."""
        # Use display_name as username if username is not available
        username = data.get("username")
        if not username:
            username = data.get("display_name") or f"User_{data['user_id'][-8:]}"
        
        return cls(
            user_id=data["user_id"],
            username=username,
            display_name=data.get("display_name"),
            team_name=data.get("team_name"),
            avatar=data.get("avatar")
        )
    
    @property
    def effective_name(self) -> str:
        """Get the most appropriate display name."""
        return self.display_name or self.team_name or self.username