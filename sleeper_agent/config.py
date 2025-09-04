"""Configuration management for Sleeper Agent."""

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from rich.console import Console

console = Console()


class Config(BaseModel):
    """Application configuration."""
    
    league_id: Optional[str] = None
    last_used: Optional[str] = None


class ConfigManager:
    """Manages application configuration persistence."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".sleeper_agent"
        self.config_file = self.config_dir / "config.json"
        self._ensure_config_dir()
    
    def _ensure_config_dir(self) -> None:
        """Ensure config directory exists."""
        self.config_dir.mkdir(exist_ok=True)
    
    def load_config(self) -> Config:
        """Load configuration from file."""
        if not self.config_file.exists():
            return Config()
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                return Config(**data)
        except (json.JSONDecodeError, ValueError) as e:
            console.print(f"[yellow]Warning: Invalid config file, using defaults: {e}[/yellow]")
            return Config()
    
    def save_config(self, config: Config) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config.dict(), f, indent=2)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save config: {e}[/yellow]")
    
    def get_cache_dir(self) -> Path:
        """Get cache directory path."""
        cache_dir = self.config_dir / "cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir
    
    def get_output_dir(self) -> Path:
        """Get output directory path."""
        output_dir = Path("out")
        output_dir.mkdir(exist_ok=True)
        return output_dir