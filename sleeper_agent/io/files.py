"""File management utilities."""

from pathlib import Path
from typing import Union
from sleeper_agent.config import ConfigManager


class FileManager:
    """Manages file paths and directories."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
    
    def get_output_path(self, filename: str) -> Path:
        """Get output file path."""
        output_dir = self.config_manager.get_output_dir()
        return output_dir / filename
    
    def get_cache_path(self, filename: str) -> Path:
        """Get cache file path."""
        cache_dir = self.config_manager.get_cache_dir()
        return cache_dir / filename
    
    def draft_recap_filename(self, league_id: str, draft_id: str) -> str:
        """Generate draft recap CSV filename."""
        return f"draft_{league_id}_{draft_id}.csv"
    
    def team_roster_filename(self, league_id: str, username: str) -> str:
        """Generate team roster CSV filename."""
        from datetime import datetime
        # Sanitize username for filename
        safe_username = "".join(c for c in username if c.isalnum() or c in "._-")
        # Add timestamp to make filename unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"roster_{league_id}_{safe_username}_{timestamp}.csv"
    
    def players_cache_filename(self, season: str = "2025") -> str:
        """Generate players cache filename."""
        return f"players_{season}.json"
    
    def matchups_filename(self, league_id: str, week: int) -> str:
        """Generate matchups CSV filename."""
        return f"matchups_{league_id}_week{week}.csv"
    
    def ensure_output_dir(self) -> Path:
        """Ensure output directory exists and return path."""
        return self.config_manager.get_output_dir()


# Global file manager instance
file_manager = FileManager()