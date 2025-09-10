"""Week recap service for player-level matchup analysis."""

from typing import Dict, List, Optional, Tuple
import pandas as pd
from rich.console import Console

from sleeper_agent.models.matchup import Matchup
from sleeper_agent.services.api import get_json, SleeperAPIError
from sleeper_agent.services.leagues import LeagueService
from sleeper_agent.services.players import players_cache

console = Console()


class WeekRecapService:
    """Service for generating player-level week recap data."""
    
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
    
    def group_by_matchup_id(self, matchups: List[Matchup]) -> Dict[int, List[Matchup]]:
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
        
        # Add byes as individual "matchups" with unique negative IDs
        bye_id = -1
        for bye in byes:
            grouped[bye_id] = [bye]
            bye_id -= 1
            
        return grouped
    
    def assign_sides(self, pair: List[Matchup]) -> Tuple[Matchup, Optional[Matchup]]:
        """Assign sides A and B based on roster_id ordering."""
        if len(pair) == 1:
            return pair[0], None
        elif len(pair) == 2:
            # Side A = lower roster_id, Side B = higher roster_id
            if pair[0].roster_id <= pair[1].roster_id:
                return pair[0], pair[1]
            else:
                return pair[1], pair[0]
        else:
            raise ValueError(f"Invalid matchup pair length: {len(pair)}")
    
    def resolve_users_and_rosters(self, league_id: str, week: int) -> Tuple[Dict[str, Dict], Dict[int, str]]:
        """Resolve user mappings. Roster composition now comes from matchup data directly."""
        users = self.league_service.get_users()
        rosters = self.league_service.get_rosters()
        
        # Build user lookup by user_id
        user_by_user_id = {}
        for user in users:
            user_by_user_id[user.user_id] = {
                'username': user.username,
                'display_name': user.display_name,
                'team_name': user.team_name
            }
        
        # Build roster_id to user_id mapping (owner relationships don't change)
        user_id_by_roster_id = {}
        for roster in rosters:
            user_id_by_roster_id[roster.roster_id] = roster.owner_id
            
        return user_by_user_id, user_id_by_roster_id
    
    def extract_starters(self, matchup: Matchup) -> List[str]:
        """Extract starter player IDs, filtering out None and empty values."""
        return matchup.get_starters_list()
    
    def extract_player_points(self, matchup: Matchup) -> Dict[str, float]:
        """Extract per-player fantasy points from matchup data."""
        player_points = {}
        starters = self.extract_starters(matchup)
        
        # Prefer starters_points array when available
        if (matchup.starters_points and 
            isinstance(matchup.starters_points, list) and 
            len(matchup.starters_points) >= len(starters)):
            
            for i, player_id in enumerate(starters):
                if i < len(matchup.starters_points) and matchup.starters_points[i] is not None:
                    player_points[player_id] = float(matchup.starters_points[i])
        
        # Fallback to players_points dict filtered to starters
        elif matchup.players_points and isinstance(matchup.players_points, dict):
            for player_id in starters:
                if player_id in matchup.players_points and matchup.players_points[player_id] is not None:
                    player_points[player_id] = float(matchup.players_points[player_id])
        
        return player_points
    
    def get_week_specific_roster_from_matchup(self, matchup: Matchup) -> set[str]:
        """Get the actual roster for that week from matchup data.
        
        The matchup.players_points dictionary is the authoritative source
        for which players were on the roster that week.
        """
        if matchup.players_points:
            return set(matchup.players_points.keys())
        return set()
    
    def determine_week_specific_player_status(self, player_id: str, matchup: Matchup) -> Optional[str]:
        """Determine if a player was a starter or bench player for this specific week.
        
        Uses matchup data as the authoritative source for roster composition.
        
        Args:
            player_id: The player ID to check
            matchup: The matchup data containing actual roster and starters for that week
            
        Returns:
            "starter" if player started that week, "bench" if on roster but not starting, None if not on roster
        """
        # Get actual roster from matchup data
        week_roster = self.get_week_specific_roster_from_matchup(matchup)
        
        # First check if player was actually on the roster that week
        if player_id not in week_roster:
            return None  # Player wasn't on the roster that week
        
        # Check if player was in the starting lineup that week
        actual_starters = matchup.get_starters_list()
        if player_id in actual_starters:
            return "starter"
        else:
            return "bench"
    
    def build_rows_for_matchup(
        self, 
        matchup_id: int,
        week: int,
        side_a: Matchup, 
        side_b: Optional[Matchup],
        user_by_user_id: Dict[str, Dict],
        user_id_by_roster_id: Dict[int, str]
    ) -> List[Dict]:
        """Build CSV rows for a single matchup (one row per rostered player)."""
        rows = []
        
        # Determine winner and tie status
        winner_roster_id = ""
        is_tie = False
        
        if side_b is not None:
            side_a_points = side_a.actual_points or 0.0
            side_b_points = side_b.actual_points or 0.0
            
            if abs(side_a_points - side_b_points) < 1e-6:  # Tie
                is_tie = True
                winner_roster_id = ""
            elif side_a_points > side_b_points:
                winner_roster_id = side_a.roster_id
            else:
                winner_roster_id = side_b.roster_id
        
        # Process side A
        side_a_user_id = user_id_by_roster_id.get(side_a.roster_id, "")
        side_a_user = user_by_user_id.get(side_a_user_id, {})
        side_a_starters = self.extract_starters(side_a)
        side_a_player_points = self.extract_player_points(side_a)
        
        # Get all player points from players_points dict (includes bench players)
        side_a_all_player_points = {}
        if side_a.players_points and isinstance(side_a.players_points, dict):
            for player_id, points in side_a.players_points.items():
                if points is not None:
                    side_a_all_player_points[player_id] = float(points)
        
        # Opponent info for side A
        opp_roster_id = side_b.roster_id if side_b else ""
        opp_user_id = user_id_by_roster_id.get(opp_roster_id, "") if side_b else ""
        opp_user = user_by_user_id.get(opp_user_id, {}) if side_b else {}
        opp_total_points = side_b.actual_points if side_b else ""
        
        # Process all players who were actually on roster that week (from matchup data)
        week_roster_players = self.get_week_specific_roster_from_matchup(side_a)
        for player_id in week_roster_players:
            if not player_id:  # Skip empty player IDs
                continue
                
            # Determine week-specific player status using matchup data
            player_status = self.determine_week_specific_player_status(player_id, side_a)
            if player_status is None:  # Shouldn't happen since we got players from matchup
                continue
            
            row = self._build_player_row(
                league_id=self.league_id,
                week=week,
                matchup_id=matchup_id,
                winner_roster_id=winner_roster_id,
                is_tie=is_tie,
                side="A",
                side_roster_id=side_a.roster_id,
                side_user_id=side_a_user_id,
                side_user=side_a_user,
                side_total_points=side_a.actual_points,
                opp_roster_id=opp_roster_id,
                opp_username=opp_user.get('username', ''),
                opp_total_points=opp_total_points,
                player_id=player_id,
                player_points=side_a_all_player_points.get(player_id, ""),
                player_status=player_status
            )
            rows.append(row)
        
        # Process side B if exists
        if side_b:
            side_b_user_id = user_id_by_roster_id.get(side_b.roster_id, "")
            side_b_user = user_by_user_id.get(side_b_user_id, {})
            side_b_starters = self.extract_starters(side_b)
            side_b_player_points = self.extract_player_points(side_b)
            
            # Get all player points from players_points dict (includes bench players)
            side_b_all_player_points = {}
            if side_b.players_points and isinstance(side_b.players_points, dict):
                for player_id, points in side_b.players_points.items():
                    if points is not None:
                        side_b_all_player_points[player_id] = float(points)
            
            # Process all players who were actually on roster that week (from matchup data)
            week_roster_players_b = self.get_week_specific_roster_from_matchup(side_b)
            for player_id in week_roster_players_b:
                if not player_id:  # Skip empty player IDs
                    continue
                    
                # Determine week-specific player status using matchup data
                player_status = self.determine_week_specific_player_status(player_id, side_b)
                if player_status is None:  # Shouldn't happen since we got players from matchup
                    continue
                
                row = self._build_player_row(
                    league_id=self.league_id,
                    week=week,
                    matchup_id=matchup_id,
                    winner_roster_id=winner_roster_id,
                    is_tie=is_tie,
                    side="B",
                    side_roster_id=side_b.roster_id,
                    side_user_id=side_b_user_id,
                    side_user=side_b_user,
                    side_total_points=side_b.actual_points,
                    opp_roster_id=side_a.roster_id,
                    opp_username=side_a_user.get('username', ''),
                    opp_total_points=side_a.actual_points,
                    player_id=player_id,
                    player_points=side_b_all_player_points.get(player_id, ""),
                    player_status=player_status
                )
                rows.append(row)
        
        return rows
    
    def _build_player_row(
        self,
        league_id: str,
        week: int,
        matchup_id: int,
        winner_roster_id: str,
        is_tie: bool,
        side: str,
        side_roster_id: int,
        side_user_id: str,
        side_user: Dict,
        side_total_points: Optional[float],
        opp_roster_id: str,
        opp_username: str,
        opp_total_points: Optional[float],
        player_id: str,
        player_points: Optional[float],
        player_status: str
    ) -> Dict:
        """Build a single player row for the CSV."""
        # Get player info from cache
        players_cache.ensure_loaded()
        player = players_cache.lookup_player(player_id)
        
        if player:
            player_name = player.full_name
            position = player.display_position
            nfl_team = player.display_team
        else:
            player_name = f"Unknown {player_id}"
            position = ""
            nfl_team = ""
            console.print(f"[yellow]Warning: Unknown player ID {player_id}[/yellow]")
        
        return {
            "league_id": league_id,
            "week": week,
            "matchup_id": matchup_id,
            "winner_roster_id": winner_roster_id,
            "is_tie": is_tie,
            "side": side,
            "side_roster_id": side_roster_id,
            "side_user_id": side_user_id,
            "side_username": side_user.get('username', ''),
            "side_display_name": side_user.get('display_name', ''),
            "side_team_name": side_user.get('team_name', ''),
            "side_total_points": side_total_points or "",
            "opp_roster_id": opp_roster_id,
            "opp_username": opp_username,
            "opp_total_points": opp_total_points or "",
            "player_id": player_id,
            "player_name": player_name,
            "position": position,
            "nfl_team": nfl_team,
            "player_points": player_points if player_points != "" else "",
            "player_status": player_status
        }
    
    def build_week_recap_dataframe(self, week: int) -> pd.DataFrame:
        """Build complete week recap dataframe."""
        console.print(f"[blue]Building week recap data for week {week}...[/blue]")
        
        # Fetch all necessary data
        matchups = self.fetch_week_matchups(week)
        if not matchups:
            console.print("[yellow]No matchups found for this week[/yellow]")
            return pd.DataFrame()
        
        grouped = self.group_by_matchup_id(matchups)
        user_by_user_id, user_id_by_roster_id = self.resolve_users_and_rosters(self.league_id, week)
        
        # Build all rows
        all_rows = []
        
        for matchup_id, matchup_list in grouped.items():
            side_a, side_b = self.assign_sides(matchup_list)
            
            rows = self.build_rows_for_matchup(
                matchup_id=matchup_id,
                week=week,
                side_a=side_a,
                side_b=side_b,
                user_by_user_id=user_by_user_id,
                user_id_by_roster_id=user_id_by_roster_id
            )
            
            all_rows.extend(rows)
        
        if not all_rows:
            console.print("[yellow]No player data found for this week[/yellow]")
            return pd.DataFrame()
        
        # Create DataFrame with exact column order
        df = pd.DataFrame(all_rows)
        
        # Define stable column order
        columns = [
            "league_id", "week", "matchup_id", "winner_roster_id", "is_tie",
            "side", "side_roster_id", "side_user_id", "side_username", 
            "side_display_name", "side_team_name", "side_total_points",
            "opp_roster_id", "opp_username", "opp_total_points",
            "player_id", "player_name", "position", "nfl_team", "player_points", "player_status"
        ]
        
        # Sort by matchup_id, side, player_status (starters first), position, player_name for consistent output
        df = df[columns].sort_values(['matchup_id', 'side', 'player_status', 'position', 'player_name']).reset_index(drop=True)
        
        console.print(f"[green]Built week recap dataframe with {len(df)} player rows[/green]")
        
        return df