"""League and roster management services."""

from typing import Dict, List, Optional, Tuple
from rich.console import Console

from sleeper_agent.models.league import League
from sleeper_agent.models.user import User
from sleeper_agent.models.roster import Roster
from sleeper_agent.services.api import get_json, SleeperAPIError

console = Console()


class LeagueService:
    """Service for managing league data."""
    
    def __init__(self, league_id: str):
        self.league_id = league_id
        self._league: Optional[League] = None
        self._users: Optional[List[User]] = None
        self._rosters: Optional[List[Roster]] = None
        self._user_map: Optional[Dict[str, User]] = None
        self._roster_map: Optional[Dict[str, Roster]] = None
    
    def get_league(self) -> League:
        """Get league information."""
        if self._league is None:
            try:
                data = get_json(f"league/{self.league_id}")
                self._league = League.from_api_response(data)
                console.print(f"[green]Found league: {self._league.name} ({self._league.season})[/green]")
            except SleeperAPIError as e:
                if e.status_code == 404:
                    raise ValueError(f"League {self.league_id} not found")
                raise
        
        return self._league
    
    def get_users(self) -> List[User]:
        """Get all users in the league."""
        if self._users is None:
            try:
                data = get_json(f"league/{self.league_id}/users")
                self._users = [User.from_api_response(user_data) for user_data in data]
                
                # Build user map for quick lookup
                self._user_map = {user.user_id: user for user in self._users}
                
                console.print(f"[green]Found {len(self._users)} users in league[/green]")
            except SleeperAPIError as e:
                if e.status_code == 404:
                    raise ValueError(f"Users not found for league {self.league_id}")
                raise
        
        return self._users
    
    def get_rosters(self) -> List[Roster]:
        """Get all rosters in the league."""
        if self._rosters is None:
            try:
                data = get_json(f"league/{self.league_id}/rosters")
                self._rosters = [Roster.from_api_response({**roster_data, "league_id": self.league_id}) 
                               for roster_data in data]
                
                # Build roster map for quick lookup
                self._roster_map = {roster.owner_id: roster for roster in self._rosters}
                
                console.print(f"[green]Found {len(self._rosters)} rosters in league[/green]")
            except SleeperAPIError as e:
                if e.status_code == 404:
                    raise ValueError(f"Rosters not found for league {self.league_id}")
                raise
        
        return self._rosters
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by user_id."""
        if self._user_map is None:
            self.get_users()
        return self._user_map.get(user_id)
    
    def get_roster_by_owner(self, owner_id: str) -> Optional[Roster]:
        """Get roster by owner_id."""
        if self._roster_map is None:
            self.get_rosters()
        return self._roster_map.get(owner_id)
    
    def username_to_owner_id(self, username: str) -> Optional[str]:
        """Convert username to owner_id."""
        users = self.get_users()
        
        for user in users:
            if (user.username.lower() == username.lower() or
                (user.display_name and user.display_name.lower() == username.lower()) or
                (user.team_name and user.team_name.lower() == username.lower())):
                return user.user_id
        
        return None
    
    def get_user_choices(self) -> List[Tuple[int, str, str]]:
        """Get numbered list of users for selection menu."""
        users = self.get_users()
        return [
            (i + 1, user.username, user.effective_name)
            for i, user in enumerate(users)
        ]
    
    def get_user_by_choice(self, choice: int) -> Optional[User]:
        """Get user by menu choice number (1-based)."""
        users = self.get_users()
        if 1 <= choice <= len(users):
            return users[choice - 1]
        return None
    
    def validate_league(self) -> Tuple[bool, str]:
        """Validate that league exists and is accessible."""
        try:
            league = self.get_league()
            return True, f"✓ League: {league.name} ({league.season})"
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Error accessing league: {e}"