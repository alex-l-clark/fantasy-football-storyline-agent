"""CSV export utilities for dataframes."""

from pathlib import Path
from typing import List, Optional
import pandas as pd
from rich.console import Console

from sleeper_agent.io.files import file_manager
from sleeper_agent.services.leagues import LeagueService
from sleeper_agent.services.players import players_cache

console = Console()


class CSVExporter:
    """Handles CSV export operations."""
    
    @staticmethod
    def export_draft_recap(df: pd.DataFrame, league_id: str, draft_id: str) -> Path:
        """Export draft recap dataframe to CSV."""
        if df.empty:
            raise ValueError("No draft data to export")
        
        filename = file_manager.draft_recap_filename(league_id, draft_id)
        output_path = file_manager.get_output_path(filename)
        
        # Ensure output directory exists
        file_manager.ensure_output_dir()
        
        # Export with consistent formatting
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        console.print(f"[green]✅ Draft recap exported: {output_path}[/green]")
        console.print(f"[blue]📊 {len(df)} picks exported[/blue]")
        
        return output_path
    
    @staticmethod
    def export_team_roster(league_id: str, username: str, owner_id: str) -> Path:
        """Export team roster to CSV."""
        league_service = LeagueService(league_id)
        
        # Get roster for the user
        roster = league_service.get_roster_by_owner(owner_id)
        if not roster:
            raise ValueError(f"No roster found for user {username}")
        
        # Get user info
        user = league_service.get_user_by_id(owner_id)
        if not user:
            raise ValueError(f"User {username} not found")
        
        # Ensure players cache is loaded
        console.print("[blue]Loading player information...[/blue]")
        players_cache.ensure_loaded()
        
        # Build roster data
        rows = []
        for player_id in roster.players:
            if not player_id:  # Skip empty player IDs
                continue
                
            player_info = players_cache.get_player_info(player_id)
            status = roster.get_player_status(player_id)
            
            row = {
                "roster_id": roster.roster_id,
                "user_id": user.user_id,
                "username": user.username,
                "player_id": player_id,
                "player_name": player_info["name"],
                "position": player_info["position"],
                "nfl_team": player_info["team"],
                "status": status
            }
            rows.append(row)
        
        if not rows:
            raise ValueError(f"No players found on {username}'s roster")
        
        # Create dataframe with consistent column order
        df = pd.DataFrame(rows)
        columns = [
            "roster_id", "user_id", "username",
            "player_id", "player_name", "position", "nfl_team", "status"
        ]
        df = df[columns]
        
        # Export to CSV - use the actual user's username for filename
        actual_username = user.username
        filename = file_manager.team_roster_filename(league_id, actual_username)
        output_path = file_manager.get_output_path(filename)
        
        # Ensure output directory exists
        file_manager.ensure_output_dir()
        
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        console.print(f"[green]✅ Team roster exported: {output_path}[/green]")
        console.print(f"[blue]📊 {len(df)} players exported for {user.effective_name}[/blue]")
        
        return output_path
    
    @staticmethod
    def export_matchups(df: pd.DataFrame, league_id: str, week: int) -> Path:
        """Export week matchups dataframe to CSV."""
        if df.empty:
            raise ValueError("No matchup data to export")
        
        filename = file_manager.matchups_filename(league_id, week)
        output_path = file_manager.get_output_path(filename)
        
        # Ensure output directory exists
        file_manager.ensure_output_dir()
        
        # Export with consistent formatting
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        console.print(f"[green]✅ Week {week} matchups exported: {output_path}[/green]")
        console.print(f"[blue]📊 {len(df)} matchups exported[/blue]")
        
        return output_path
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> None:
        """Validate that dataframe has required columns and data."""
        if df.empty:
            raise ValueError("Dataframe is empty")
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Check for completely empty rows
        if df.isnull().all(axis=1).all():
            raise ValueError("All rows are empty")


class RosterExportHelper:
    """Helper for building roster export data."""
    
    def __init__(self, league_service: LeagueService):
        self.league_service = league_service
    
    def build_roster_dataframe(self, username: str) -> pd.DataFrame:
        """Build roster dataframe for a specific user."""
        # Find user by username
        owner_id = self.league_service.username_to_owner_id(username)
        if not owner_id:
            available_users = [user.username for user in self.league_service.get_users()]
            raise ValueError(f"User '{username}' not found. Available users: {', '.join(available_users)}")
        
        # Get roster
        roster = self.league_service.get_roster_by_owner(owner_id)
        if not roster:
            raise ValueError(f"No roster found for user {username}")
        
        # Get user info
        user = self.league_service.get_user_by_id(owner_id)
        
        # Ensure players cache is loaded
        players_cache.ensure_loaded()
        
        # Build roster rows
        rows = []
        for player_id in roster.players:
            if not player_id:
                continue
                
            player_info = players_cache.get_player_info(player_id)
            status = roster.get_player_status(player_id)
            
            row = {
                "roster_id": roster.roster_id,
                "user_id": user.user_id,
                "username": user.username,
                "player_id": player_id,
                "player_name": player_info["name"],
                "position": player_info["position"],
                "nfl_team": player_info["team"],
                "status": status
            }
            rows.append(row)
        
        if not rows:
            raise ValueError(f"No active players found on {username}'s roster")
        
        # Create dataframe with consistent column order
        df = pd.DataFrame(rows)
        columns = [
            "roster_id", "user_id", "username",
            "player_id", "player_name", "position", "nfl_team", "status"
        ]
        
        return df[columns]