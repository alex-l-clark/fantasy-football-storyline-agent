"""Matchups service for weekly head-to-head data."""

from typing import Dict, List, Optional, Tuple
import pandas as pd
from rich.console import Console

from sleeper_agent.models.matchup import Matchup
from sleeper_agent.services.api import get_json, SleeperAPIError
from sleeper_agent.services.leagues import LeagueService
from sleeper_agent.services.players import players_cache

console = Console()


class MatchupsService:
    """Service for managing weekly matchup data."""
    
    def __init__(self, league_id: str):
        self.league_id = league_id
        self.league_service = LeagueService(league_id)
        
    def fetch_week_matchups(self, week: int) -> List[Matchup]:
        """Fetch matchups for a specific week."""
        if not (1 <= week <= 18):
            raise ValueError(f"Week must be between 1 and 18, got {week}")
            
        try:
            console.print(f"[blue]Fetching matchups for week {week}...[/blue]")
            data = get_json(f"league/{self.league_id}/matchups/{week}")
            
            if not isinstance(data, list):
                raise ValueError(f"Invalid API response format for week {week}")
                
            matchups = [Matchup.from_api_response(item) for item in data]
            console.print(f"[green]Found {len(matchups)} matchup entries for week {week}[/green]")
            
            return matchups
            
        except SleeperAPIError as e:
            if e.status_code == 404:
                console.print(f"[yellow]No matchup data found for week {week}[/yellow]")
                return []
            raise
            
    def group_matchups_by_id(self, matchups: List[Matchup]) -> Dict[int, List[Matchup]]:
        """Group matchups by matchup_id."""
        grouped = {}
        byes = []
        
        for matchup in matchups:
            if matchup.has_bye:
                byes.append(matchup)
            else:
                matchup_id = matchup.matchup_id
                if matchup_id not in grouped:
                    grouped[matchup_id] = []
                grouped[matchup_id].append(matchup)
        
        # Add byes as individual "matchups" with unique IDs
        bye_id = -1
        for bye in byes:
            grouped[bye_id] = [bye]
            bye_id -= 1
            
        return grouped
        
    def compute_records_through_week(self, week: int) -> Dict[int, Tuple[int, int, int]]:
        """Compute win-loss-tie records through the specified week (exclusive)."""
        records = {}
        
        if week <= 1:
            # No previous weeks to compute records from
            rosters = self.league_service.get_rosters()
            return {roster.roster_id: (0, 0, 0) for roster in rosters}
            
        console.print(f"[blue]Computing records through week {week-1}...[/blue]")
        
        # Initialize records for all rosters
        rosters = self.league_service.get_rosters()
        for roster in rosters:
            records[roster.roster_id] = [0, 0, 0]  # [wins, losses, ties]
            
        # Iterate through weeks 1 to week-1
        for w in range(1, week):
            try:
                week_matchups = self.fetch_week_matchups(w)
                grouped = self.group_matchups_by_id(week_matchups)
                
                for matchup_id, matchup_list in grouped.items():
                    if len(matchup_list) == 2:
                        # Regular head-to-head matchup
                        team1, team2 = matchup_list[0], matchup_list[1]
                        
                        # Skip if either team doesn't have points recorded
                        if (team1.actual_points is None or 
                            team2.actual_points is None):
                            continue
                            
                        points1 = float(team1.actual_points)
                        points2 = float(team2.actual_points)
                        
                        # Determine winner/loser/tie
                        if abs(points1 - points2) < 1e-6:  # Tie
                            records[team1.roster_id][2] += 1  # tie
                            records[team2.roster_id][2] += 1  # tie
                        elif points1 > points2:
                            records[team1.roster_id][0] += 1  # win
                            records[team2.roster_id][1] += 1  # loss
                        else:
                            records[team1.roster_id][1] += 1  # loss
                            records[team2.roster_id][0] += 1  # win
                            
                    # Byes don't affect records
                    
            except Exception as e:
                console.print(f"[yellow]Warning: Could not process week {w} for records: {e}[/yellow]")
                continue
                
        # Convert to tuples
        return {roster_id: tuple(record) for roster_id, record in records.items()}
        
    def format_record(self, record: Tuple[int, int, int]) -> str:
        """Format a win-loss-tie record as string."""
        wins, losses, ties = record
        if ties > 0:
            return f"{wins}-{losses}-{ties}"
        else:
            return f"{wins}-{losses}"
            
    def hydrate_starters(self, starter_ids: List[str]) -> str:
        """Convert list of player IDs to formatted string of player names."""
        if not starter_ids:
            return ""
            
        players_cache.ensure_loaded()
        starter_names = []
        
        for player_id in starter_ids:
            if not player_id:
                continue
                
            player = players_cache.lookup_player(player_id)
            if player:
                # Format: "Player Name (POS, NFL)"
                name_str = f"{player.full_name} ({player.display_position}, {player.display_team})"
            else:
                name_str = f"Unknown Player ({player_id}) (N/A, N/A)"
                
            starter_names.append(name_str)
            
        return "; ".join(starter_names)
        
    def build_matchups_dataframe(self, week: int) -> pd.DataFrame:
        """Build complete matchups dataframe for the specified week."""
        console.print(f"[blue]Building matchups data for week {week}...[/blue]")
        
        # Fetch all necessary data
        matchups = self.fetch_week_matchups(week)
        if not matchups:
            console.print("[yellow]No matchups found for this week[/yellow]")
            return pd.DataFrame()
            
        grouped = self.group_matchups_by_id(matchups)
        records = self.compute_records_through_week(week)
        
        # Get users and rosters for lookup
        users = self.league_service.get_users()
        rosters = self.league_service.get_rosters()
        
        # Build lookup maps
        roster_to_user = {}
        for roster in rosters:
            roster_to_user[roster.roster_id] = roster.owner_id
            
        user_map = {user.user_id: user for user in users}
        
        # Build DataFrame rows
        rows = []
        
        for matchup_id, matchup_list in grouped.items():
            if len(matchup_list) == 1:
                # Bye week - single team
                team = matchup_list[0]
                
                # Get user info
                user_id = roster_to_user.get(team.roster_id)
                user = user_map.get(user_id) if user_id else None
                
                record = records.get(team.roster_id, (0, 0, 0))
                starters = self.hydrate_starters(team.get_starters_list())
                
                row = {
                    "league_id": self.league_id,
                    "week": week,
                    "matchup_id": matchup_id,
                    "side_a_roster_id": team.roster_id,
                    "side_a_username": user.username if user else "",
                    "side_a_display_name": user.display_name if user else "",
                    "side_a_team_name": user.team_name if user else "",
                    "side_a_record_pre": self.format_record(record),
                    "side_a_projected_points": team.projected_points or "",
                    "side_a_actual_points": team.actual_points or "",
                    "side_a_starters": starters,
                    "side_b_roster_id": "",
                    "side_b_username": "",
                    "side_b_display_name": "",
                    "side_b_team_name": "",
                    "side_b_record_pre": "",
                    "side_b_projected_points": "",
                    "side_b_actual_points": "",
                    "side_b_starters": ""
                }
                rows.append(row)
                
            elif len(matchup_list) == 2:
                # Regular head-to-head matchup
                team1, team2 = matchup_list[0], matchup_list[1]
                
                # Assign sides deterministically (lower roster_id = side A)
                if team1.roster_id <= team2.roster_id:
                    side_a, side_b = team1, team2
                else:
                    side_a, side_b = team2, team1
                
                # Get user info for both sides
                user_a_id = roster_to_user.get(side_a.roster_id)
                user_a = user_map.get(user_a_id) if user_a_id else None
                
                user_b_id = roster_to_user.get(side_b.roster_id)
                user_b = user_map.get(user_b_id) if user_b_id else None
                
                # Get records and starters
                record_a = records.get(side_a.roster_id, (0, 0, 0))
                record_b = records.get(side_b.roster_id, (0, 0, 0))
                
                starters_a = self.hydrate_starters(side_a.get_starters_list())
                starters_b = self.hydrate_starters(side_b.get_starters_list())
                
                row = {
                    "league_id": self.league_id,
                    "week": week,
                    "matchup_id": matchup_id,
                    "side_a_roster_id": side_a.roster_id,
                    "side_a_username": user_a.username if user_a else "",
                    "side_a_display_name": user_a.display_name if user_a else "",
                    "side_a_team_name": user_a.team_name if user_a else "",
                    "side_a_record_pre": self.format_record(record_a),
                    "side_a_projected_points": side_a.projected_points or "",
                    "side_a_actual_points": side_a.actual_points or "",
                    "side_a_starters": starters_a,
                    "side_b_roster_id": side_b.roster_id,
                    "side_b_username": user_b.username if user_b else "",
                    "side_b_display_name": user_b.display_name if user_b else "",
                    "side_b_team_name": user_b.team_name if user_b else "",
                    "side_b_record_pre": self.format_record(record_b),
                    "side_b_projected_points": side_b.projected_points or "",
                    "side_b_actual_points": side_b.actual_points or "",
                    "side_b_starters": starters_b
                }
                rows.append(row)
                
        if not rows:
            console.print("[yellow]No valid matchups to export[/yellow]")
            return pd.DataFrame()
            
        # Create DataFrame with consistent column order
        df = pd.DataFrame(rows)
        
        # Define column order
        columns = [
            "league_id", "week", "matchup_id",
            "side_a_roster_id", "side_a_username", "side_a_display_name", 
            "side_a_team_name", "side_a_record_pre", "side_a_projected_points", 
            "side_a_actual_points", "side_a_starters",
            "side_b_roster_id", "side_b_username", "side_b_display_name",
            "side_b_team_name", "side_b_record_pre", "side_b_projected_points",
            "side_b_actual_points", "side_b_starters"
        ]
        
        # Sort by matchup_id
        df = df[columns].sort_values('matchup_id').reset_index(drop=True)
        
        console.print(f"[green]Built matchups dataframe with {len(df)} rows[/green]")
        
        return df