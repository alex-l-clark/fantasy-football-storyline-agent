"""CLI integration point for the recap orchestrator."""

import os
from pathlib import Path
from typing import Optional
from rich.console import Console

from .config import RecapConfig
from .pipeline import RecapOrchestrator

console = Console()

def run_weekly_recap(
    week: int,
    season: Optional[int] = None,
    league_id: Optional[str] = None,
    output_dir: Optional[Path] = None,
    timezone: str = "America/New_York",
    force: bool = False,
    verbose: bool = False
) -> Path:
    """Run the weekly recap orchestrator.
    
    Args:
        week: NFL week number (1-18)
        season: NFL season year (defaults to current)
        league_id: Sleeper league ID (defaults to env var)
        output_dir: Output directory (defaults to output/)
        timezone: Timezone for season calculation
        force: Force regeneration of all steps
        verbose: Enable verbose output
        
    Returns:
        Path to the generated recap file
    """
    # Validate week
    if not (1 <= week <= 18):
        raise ValueError(f"Week must be between 1 and 18, got {week}")
    
    # Require league_id to be provided
    if not league_id:
        raise ValueError("League ID is required - this should be provided by the CLI system")
    
    # Set up output directory
    if output_dir is None:
        output_dir = Path("out")
    
    # Create orchestrator and run pipeline
    orchestrator = RecapOrchestrator(league_id, output_dir)
    
    try:
        final_path = orchestrator.run_full_pipeline(
            week=week,
            season=season,
            timezone_str=timezone,
            force=force
        )
        
        console.print(f"\n[bold green]🎉 Weekly recap generated successfully![/bold green]")
        console.print(f"[green]📄 File location: {final_path}[/green]")
        
        # Show file preview if verbose
        if verbose and final_path.exists():
            with open(final_path, 'r', encoding='utf-8') as f:
                content = f.read()
                words = len(content.split())
                lines = len(content.splitlines())
                
            console.print(f"\n[cyan]📊 File stats: {words} words, {lines} lines[/cyan]")
            
            # Show first few lines
            with open(final_path, 'r', encoding='utf-8') as f:
                preview_lines = f.readlines()[:5]
                
            console.print("\n[bold]📖 Preview:[/bold]")
            for line in preview_lines:
                console.print(f"  {line.rstrip()}")
            
            if len(preview_lines) == 5:
                console.print("  ...")
        
        return final_path
        
    except Exception as e:
        console.print(f"\n[red]❌ Failed to generate weekly recap: {e}[/red]")
        
        if verbose:
            import traceback
            console.print("\n[red]Full traceback:[/red]")
            console.print(traceback.format_exc())
        
        raise