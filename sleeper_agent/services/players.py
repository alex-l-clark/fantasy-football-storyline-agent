"""Players data cache with JSON persistence."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from rich.console import Console
from rich.progress import track

from sleeper_agent.models.player import Player
from sleeper_agent.services.api import get_json
from sleeper_agent.io.files import file_manager

console = Console()


class PlayersCache:
    """Manages NFL players data with local caching."""
    
    def __init__(self, season: str = "2025"):
        self.season = season
        self.cache_file = file_manager.get_cache_path(
            file_manager.players_cache_filename(season)
        )
        self._players: Dict[str, Player] = {}
        self._loaded = False
    
    def _is_cache_fresh(self) -> bool:
        """Check if cache file is fresh (less than 7 days old)."""
        if not self.cache_file.exists():
            return False
        
        file_age = datetime.now() - datetime.fromtimestamp(self.cache_file.stat().st_mtime)
        return file_age < timedelta(days=7)
    
    def _load_from_cache(self) -> bool:
        """Load players from cache file."""
        if not self.cache_file.exists():
            return False
        
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                
            self._players = {
                player_id: Player.from_api_response(player_id, player_data)
                for player_id, player_data in data.items()
            }
            
            console.print(f"[green]Loaded {len(self._players)} players from cache[/green]")
            return True
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            console.print(f"[yellow]Invalid cache file, will refresh: {e}[/yellow]")
            return False
    
    def _fetch_from_api(self) -> None:
        """Fetch players data from Sleeper API."""
        console.print("[blue]Fetching NFL players database...[/blue]")
        
        try:
            api_data = get_json("players/nfl")
            
            if not isinstance(api_data, dict):
                raise ValueError("Invalid API response format")
            
            # Convert API data to Player objects with progress bar
            self._players = {}
            for player_id, player_data in track(
                api_data.items(), 
                description="Processing players..."
            ):
                if isinstance(player_data, dict):
                    self._players[player_id] = Player.from_api_response(player_id, player_data)
            
            console.print(f"[green]Loaded {len(self._players)} players from API[/green]")
            
        except Exception as e:
            console.print(f"[red]Failed to fetch players data: {e}[/red]")
            raise
    
    def _save_to_cache(self) -> None:
        """Save players data to cache file."""
        try:
            # Convert Player objects to dict for JSON serialization
            cache_data = {
                player_id: {
                    "first_name": player.first_name,
                    "last_name": player.last_name,
                    "position": player.position,
                    "team": player.team,
                    "number": player.number,
                    "age": player.age,
                    "fantasy_positions": player.fantasy_positions
                }
                for player_id, player in self._players.items()
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            console.print(f"[green]Cached {len(self._players)} players to {self.cache_file}[/green]")
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save players cache: {e}[/yellow]")
    
    def ensure_loaded(self) -> None:
        """Ensure players data is loaded, refreshing if necessary."""
        if self._loaded:
            return
        
        # Try to load from cache if it's fresh
        if self._is_cache_fresh() and self._load_from_cache():
            self._loaded = True
            return
        
        # Fetch from API and cache
        self._fetch_from_api()
        self._save_to_cache()
        self._loaded = True
    
    def lookup_player(self, player_id: str) -> Optional[Player]:
        """Look up a player by ID."""
        self.ensure_loaded()
        return self._players.get(player_id)
    
    def get_player_info(self, player_id: str) -> Dict[str, str]:
        """Get basic player info as dict (for backward compatibility)."""
        player = self.lookup_player(player_id)
        if player:
            return {
                "name": player.full_name,
                "position": player.display_position,
                "team": player.display_team
            }
        return {
            "name": "Unknown Player",
            "position": "N/A",
            "team": "N/A"
        }
    
    def get_total_players(self) -> int:
        """Get total number of cached players."""
        self.ensure_loaded()
        return len(self._players)


# Global players cache instance
players_cache = PlayersCache()