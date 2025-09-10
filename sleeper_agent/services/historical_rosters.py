"""Historical roster service for week-specific roster reconstruction."""

from typing import Dict, List, Optional, Set
from rich.console import Console
from copy import deepcopy

from sleeper_agent.models.roster import Roster
from sleeper_agent.models.transaction import Transaction
from sleeper_agent.services.api import get_json, SleeperAPIError
from sleeper_agent.services.leagues import LeagueService

console = Console()


class HistoricalRosterService:
    """Service for reconstructing historical roster states."""
    
    def __init__(self, league_id: str):
        self.league_id = league_id
        self.league_service = LeagueService(league_id)
        
        # Caches
        self._transactions_cache: Dict[int, List[Transaction]] = {}
        self._historical_rosters_cache: Dict[str, Roster] = {}  # key: "{roster_id}_{week}"
        self._current_week: Optional[int] = None
        
    def get_current_week(self) -> int:
        """Get current NFL week by finding the latest week with matchup data."""
        if self._current_week is not None:
            return self._current_week
            
        try:
            # Try to find the latest week with matchup data by checking backwards from week 18
            for week in range(18, 0, -1):
                try:
                    matchup_data = get_json(f"league/{self.league_id}/matchups/{week}")
                    if matchup_data and isinstance(matchup_data, list) and len(matchup_data) > 0:
                        console.print(f"[green]Detected current week: {week}[/green]")
                        self._current_week = week
                        return week
                except SleeperAPIError:
                    continue
            
            # Fallback to week 18 if we can't determine
            console.print("[yellow]Could not determine current week, defaulting to 18[/yellow]")
            self._current_week = 18
            return self._current_week
            
        except Exception as e:
            console.print(f"[yellow]Error determining current week: {e}, defaulting to 18[/yellow]")
            self._current_week = 18
            return self._current_week
    
    def fetch_transactions_for_week(self, week: int) -> List[Transaction]:
        """Fetch all transactions for a specific week."""
        if week in self._transactions_cache:
            return self._transactions_cache[week]
        
        try:
            console.print(f"[blue]Fetching transactions for week {week}...[/blue]")
            data = get_json(f"league/{self.league_id}/transactions/{week}")
            
            if not isinstance(data, list):
                console.print(f"[yellow]No transaction data found for week {week}[/yellow]")
                transactions = []
            else:
                transactions = [Transaction.from_api_response(tx) for tx in data if tx.get('status') == 'complete']
                console.print(f"[green]Found {len(transactions)} completed transactions for week {week}[/green]")
            
            self._transactions_cache[week] = transactions
            return transactions
            
        except SleeperAPIError as e:
            if e.status_code == 404:
                console.print(f"[yellow]No transactions found for week {week}[/yellow]")
                self._transactions_cache[week] = []
                return []
            raise
    
    def get_roster_for_week(self, roster_id: int, target_week: int) -> Optional[Roster]:
        """Get roster state for a specific week by reconstructing from transactions."""
        cache_key = f"{roster_id}_{target_week}"
        
        if cache_key in self._historical_rosters_cache:
            return self._historical_rosters_cache[cache_key]
        
        # Get current rosters as starting point
        current_rosters = self.league_service.get_rosters()
        current_roster = None
        
        for roster in current_rosters:
            if roster.roster_id == roster_id:
                current_roster = roster
                break
        
        if not current_roster:
            console.print(f"[red]Roster {roster_id} not found[/red]")
            return None
        
        # If requesting current week, return current roster
        current_week = self.get_current_week()
        if target_week >= current_week:
            self._historical_rosters_cache[cache_key] = current_roster
            return current_roster
        
        try:
            historical_roster = self._reconstruct_roster_for_week(current_roster, target_week, current_week)
            self._historical_rosters_cache[cache_key] = historical_roster
            return historical_roster
            
        except Exception as e:
            console.print(f"[red]Failed to reconstruct roster for week {target_week}: {e}[/red]")
            console.print(f"[yellow]Falling back to current roster data[/yellow]")
            return current_roster
    
    def _reconstruct_roster_for_week(self, current_roster: Roster, target_week: int, current_week: int) -> Roster:
        """Reconstruct historical roster by reversing transactions."""
        console.print(f"[blue]Reconstructing roster {current_roster.roster_id} for week {target_week}[/blue]")
        
        # Start with a copy of current roster
        historical_roster = deepcopy(current_roster)
        historical_players = set(historical_roster.players)
        historical_starters = set(historical_roster.starters)
        
        # Work backwards from current week to target week
        for week in range(current_week, target_week, -1):
            transactions = self.fetch_transactions_for_week(week)
            
            # Reverse each transaction that affects this roster
            for transaction in transactions:
                if transaction.affects_roster(current_roster.roster_id):
                    changes = transaction.get_player_changes_for_roster(current_roster.roster_id)
                    
                    # Reverse the transaction:
                    # - Players that were added in this week should be removed from historical roster
                    # - Players that were dropped in this week should be added back to historical roster
                    
                    for player_id in changes["added"]:
                        if player_id in historical_players:
                            historical_players.remove(player_id)
                            if player_id in historical_starters:
                                historical_starters.remove(player_id)
                            console.print(f"[dim]  Week {week}: Removing {player_id} (was added)[/dim]")
                    
                    for player_id in changes["dropped"]:
                        historical_players.add(player_id)
                        console.print(f"[dim]  Week {week}: Adding back {player_id} (was dropped)[/dim]")
        
        # Update the historical roster with reconstructed player lists
        historical_roster.players = list(historical_players)
        
        # For starters, we can only reconstruct what we know about
        # If a starter was dropped/added, remove from starters list
        # The exact starting lineup for historical weeks is not perfectly reconstructable
        # without matchup data, but we can at least ensure starters are on the roster
        historical_roster.starters = [p for p in historical_roster.starters if p in historical_players]
        
        console.print(f"[green]Reconstructed roster {current_roster.roster_id} for week {target_week}: "
                     f"{len(historical_roster.players)} players[/green]")
        
        return historical_roster
    
    def get_all_historical_rosters_for_week(self, target_week: int) -> Dict[int, Roster]:
        """Get all rosters for a specific week."""
        current_rosters = self.league_service.get_rosters()
        historical_rosters = {}
        
        for roster in current_rosters:
            historical_roster = self.get_roster_for_week(roster.roster_id, target_week)
            if historical_roster:
                historical_rosters[roster.roster_id] = historical_roster
        
        return historical_rosters
    
    def clear_cache(self):
        """Clear all cached data."""
        self._transactions_cache.clear()
        self._historical_rosters_cache.clear()
        console.print("[blue]Historical roster cache cleared[/blue]")