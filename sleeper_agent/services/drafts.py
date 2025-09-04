"""Draft management services."""

from typing import List, Optional
import pandas as pd
from rich.console import Console

from sleeper_agent.models.draft import Draft, DraftPick
from sleeper_agent.services.api import get_json, SleeperAPIError
from sleeper_agent.services.players import players_cache
from sleeper_agent.services.leagues import LeagueService

console = Console()


class DraftService:
    """Service for managing draft data."""
    
    def __init__(self, league_id: str):
        self.league_id = league_id
        self.league_service = LeagueService(league_id)
    
    def get_latest_draft_id(self) -> Optional[str]:
        """Get the ID of the most recent draft for the league."""
        try:
            data = get_json(f"league/{self.league_id}/drafts")
            
            if not data:
                return None
            
            drafts = [Draft.from_api_response(draft_data) for draft_data in data]
            
            # Find the most recent completed draft, or any draft if none completed
            completed_drafts = [d for d in drafts if d.status == "complete"]
            
            if completed_drafts:
                # Sort by start_time (most recent first)
                latest = max(completed_drafts, key=lambda d: d.start_time or 0)
            else:
                # No completed drafts, get the most recent one
                latest = max(drafts, key=lambda d: d.start_time or 0)
            
            console.print(f"[green]Found draft: {latest.draft_id} (status: {latest.status})[/green]")
            return latest.draft_id
            
        except SleeperAPIError as e:
            if e.status_code == 404:
                console.print(f"[yellow]No drafts found for league {self.league_id}[/yellow]")
                return None
            raise
    
    def get_picks(self, draft_id: str) -> List[DraftPick]:
        """Get all picks for a draft."""
        try:
            data = get_json(f"draft/{draft_id}/picks")
            
            if not data:
                return []
            
            picks = [DraftPick.from_api_response(pick_data) for pick_data in data]
            
            # Sort by pick number
            picks.sort(key=lambda p: p.pick_no)
            
            console.print(f"[green]Found {len(picks)} picks in draft {draft_id}[/green]")
            return picks
            
        except SleeperAPIError as e:
            if e.status_code == 404:
                console.print(f"[yellow]No picks found for draft {draft_id}[/yellow]")
                return []
            raise
    
    def build_draft_dataframe(self, draft_id: str) -> pd.DataFrame:
        """Build a comprehensive draft dataframe with hydrated player data."""
        picks = self.get_picks(draft_id)
        
        if not picks:
            return pd.DataFrame()
        
        # Ensure players cache is loaded
        console.print("[blue]Loading player information...[/blue]")
        players_cache.ensure_loaded()
        
        # Get league data for user mapping
        users = self.league_service.get_users()
        user_map = {user.user_id: user for user in users}
        
        # Build dataframe
        rows = []
        for pick in picks:
            # Get user info
            user = user_map.get(pick.picked_by)
            username = user.username if user else "Unknown"
            team_name = user.effective_name if user else "Unknown"
            
            # Get player info
            player_info = players_cache.get_player_info(pick.player_id or "")
            
            # Calculate overall pick number (for snake drafts)
            overall = pick.pick_no
            
            row = {
                "pick_number": pick.pick_no,
                "round": pick.round,
                "overall": overall,
                "draft_slot": pick.draft_slot,
                "user_id": pick.picked_by,
                "username": username,
                "team_name": team_name,
                "roster_id": pick.roster_id,
                "player_id": pick.player_id or "",
                "player_name": player_info["name"],
                "position": player_info["position"],
                "nfl_team": player_info["team"],
                "timestamp_utc": pick.timestamp_utc.isoformat() if pick.timestamp_utc else ""
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Ensure consistent column order
        columns = [
            "pick_number", "round", "overall", "draft_slot",
            "user_id", "username", "team_name", "roster_id",
            "player_id", "player_name", "position", "nfl_team", "timestamp_utc"
        ]
        
        return df[columns]
    
    def get_draft_summary(self, draft_id: str) -> str:
        """Get a summary of the draft."""
        picks = self.get_picks(draft_id)
        
        if not picks:
            return "No picks found in draft"
        
        total_picks = len(picks)
        max_round = max(pick.round for pick in picks) if picks else 0
        
        # Get some sample picks for display
        first_round_picks = [p for p in picks if p.round == 1][:3]
        sample_text = ""
        
        if first_round_picks:
            players_cache.ensure_loaded()
            sample_picks = []
            
            for pick in first_round_picks:
                player_info = players_cache.get_player_info(pick.player_id or "")
                sample_picks.append(f"Pick {pick.pick_no}: {player_info['name']} ({player_info['position']})")
            
            sample_text = f"\nFirst few picks:\n" + "\n".join(sample_picks)
        
        return f"Draft {draft_id}: {total_picks} picks, {max_round} rounds{sample_text}"