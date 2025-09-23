"""Main CLI application for Sleeper Agent."""

from typing import Optional
from pathlib import Path
import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel

from sleeper_agent.config import Config, ConfigManager
from sleeper_agent.services.leagues import LeagueService
from sleeper_agent.services.drafts import DraftService
from sleeper_agent.services.matchups import MatchupsService
from sleeper_agent.services.week_recap import WeekRecapService
from sleeper_agent.io.csv_export import CSVExporter, RosterExportHelper

app = typer.Typer(
    name="sleeper-agent",
    help="Sleeper Fantasy Football CLI Agent",
    add_completion=False
)
console = Console()


class SleeperCLI:
    """Main CLI application class."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.league_id: Optional[str] = None
        self.league_service: Optional[LeagueService] = None
    
    def setup_league(self) -> bool:
        """Setup and validate league ID."""
        # Check for cached league ID
        if self.config.league_id:
            console.print(f"[blue]Found cached league ID: {self.config.league_id}[/blue]")
            if Confirm.ask("Use cached league ID?"):
                self.league_id = self.config.league_id
                
                # Validate the cached league ID
                temp_service = LeagueService(self.league_id)
                is_valid, message = temp_service.validate_league()
                
                if not is_valid:
                    console.print(f"[red]❌ Cached league ID is invalid: {message}[/red]")
                    console.print("[yellow]Will prompt for new league ID...[/yellow]")
                    self.league_id = None
                else:
                    console.print(f"[green]{message}[/green]")
            else:
                self.league_id = None
        
        # Prompt for league ID if not cached or rejected
        if not self.league_id:
            console.print("\n[bold blue]🏈 Sleeper Agent[/bold blue]")
            console.print("Enter your Sleeper league ID to get started.\n")
            
            while True:
                league_id = Prompt.ask("Enter Sleeper league_id")
                
                if not league_id:
                    console.print("[red]League ID cannot be empty[/red]")
                    continue
                
                # Validate league
                temp_service = LeagueService(league_id)
                is_valid, message = temp_service.validate_league()
                
                if is_valid:
                    self.league_id = league_id
                    console.print(f"[green]{message}[/green]")
                    break
                else:
                    console.print(f"[red]❌ {message}[/red]")
                    if not Confirm.ask("Try again?"):
                        return False
        
        # Save league ID to config
        self.config.league_id = self.league_id
        self.config_manager.save_config(self.config)
        
        # Initialize league service
        self.league_service = LeagueService(self.league_id)
        
        return True
    
    def show_main_menu(self) -> Optional[str]:
        """Show main menu and get user choice."""
        console.print("\n" + "="*50)
        console.print("[bold blue]📋 Main Menu[/bold blue]")
        console.print("="*50)
        
        menu_table = Table(show_header=False, box=None, padding=(0, 2))
        menu_table.add_column("Option", style="bold cyan")
        menu_table.add_column("Description")
        
        menu_table.add_row("1", "draft-recap - Export latest draft to CSV")
        menu_table.add_row("2", "team-preview - Export a team's roster to CSV")
        menu_table.add_row("3", "week-matchups - Export weekly matchups to CSV")
        menu_table.add_row("4", "week-recap - Generate AI-powered groupchat recap")
        menu_table.add_row("q", "Quit")
        
        console.print(menu_table)
        console.print("="*50)
        
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "q"])
        
        if choice == "1":
            return "draft-recap"
        elif choice == "2":
            return "team-preview"
        elif choice == "3":
            return "week-matchups"
        elif choice == "4":
            return "week-recap"
        elif choice == "q":
            return "quit"
        
        return None
    
    def draft_recap_flow(self) -> None:
        """Handle draft recap flow."""
        console.print("\n[bold blue]📊 Draft Recap[/bold blue]")
        
        try:
            # Get draft service
            draft_service = DraftService(self.league_id)
            
            # Find latest draft
            console.print("[blue]Finding latest draft...[/blue]")
            draft_id = draft_service.get_latest_draft_id()
            
            if not draft_id:
                console.print("[red]❌ No drafts found for this league[/red]")
                return
            
            # Show draft summary
            summary = draft_service.get_draft_summary(draft_id)
            console.print(Panel(summary, title="Draft Summary", border_style="green"))
            
            # Build draft dataframe
            console.print("[blue]Building draft data...[/blue]")
            df = draft_service.build_draft_dataframe(draft_id)
            
            if df.empty:
                console.print("[red]❌ No pick data found in draft[/red]")
                return
            
            # Export to CSV
            output_path = CSVExporter.export_draft_recap(df, self.league_id, draft_id)
            
            # Show sample of first few picks
            if len(df) > 0:
                console.print("\n[bold]📋 First 5 picks:[/bold]")
                sample_table = Table()
                sample_table.add_column("Pick", style="cyan")
                sample_table.add_column("Player", style="green")
                sample_table.add_column("Team", style="blue")
                
                for _, row in df.head(5).iterrows():
                    sample_table.add_row(
                        str(row['pick_number']),
                        f"{row['player_name']} ({row['position']})",
                        row['team_name']
                    )
                
                console.print(sample_table)
            
            console.print(f"\n[bold green]✅ Draft recap exported to: {output_path}[/bold green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error during draft recap: {e}[/red]")
    
    def team_preview_flow(self) -> None:
        """Handle team preview flow."""
        console.print("\n[bold blue]👥 Team Preview[/bold blue]")
        
        try:
            # Get league users
            console.print("[blue]Loading league members...[/blue]")
            user_choices = self.league_service.get_user_choices()
            
            if not user_choices:
                console.print("[red]❌ No users found in league[/red]")
                return
            
            # Show user selection menu
            console.print("\n[bold]Select a team member:[/bold]")
            
            user_table = Table()
            user_table.add_column("Choice", style="cyan")
            user_table.add_column("Team Name", style="green")
            user_table.add_column("User ID", style="blue")
            
            for choice_num, username, display_name in user_choices:
                user_table.add_row(str(choice_num), display_name, username)
            
            console.print(user_table)
            
            # Get user choice
            max_choice = len(user_choices)
            while True:
                try:
                    choice_str = Prompt.ask(f"Enter choice (1-{max_choice})")
                    choice = int(choice_str)
                    
                    if 1 <= choice <= max_choice:
                        break
                    else:
                        console.print(f"[red]Please enter a number between 1 and {max_choice}[/red]")
                
                except ValueError:
                    console.print("[red]Please enter a valid number[/red]")
            
            # Get selected user
            selected_user = self.league_service.get_user_by_choice(choice)
            if not selected_user:
                console.print("[red]❌ Invalid user selection[/red]")
                return
            
            console.print(f"[green]Selected: {selected_user.effective_name} ({selected_user.username})[/green]")
            
            # Export roster
            console.print("[blue]Exporting roster...[/blue]")
            output_path = CSVExporter.export_team_roster(
                self.league_id, 
                selected_user.username, 
                selected_user.user_id
            )
            
            # Build and show sample of roster
            roster_helper = RosterExportHelper(self.league_service)
            df = roster_helper.build_roster_dataframe(selected_user.username)
            
            if len(df) > 0:
                console.print(f"\n[bold]📋 {selected_user.effective_name}'s Roster (first 10 players):[/bold]")
                sample_table = Table()
                sample_table.add_column("Player", style="green")
                sample_table.add_column("Position", style="cyan")
                sample_table.add_column("NFL Team", style="blue")
                sample_table.add_column("Status", style="yellow")
                
                for _, row in df.head(10).iterrows():
                    sample_table.add_row(
                        row['player_name'],
                        row['position'],
                        row['nfl_team'],
                        row['status']
                    )
                
                console.print(sample_table)
            
            console.print(f"\n[bold green]✅ Team roster exported to: {output_path}[/bold green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error during team preview: {e}[/red]")
    
    def week_matchups_flow(self) -> None:
        """Handle week matchups flow."""
        console.print("\n[bold blue]🏈 Week Matchups[/bold blue]")
        
        try:
            # Get week number from user
            while True:
                try:
                    week_str = Prompt.ask("Enter NFL week number (1–18)")
                    week = int(week_str)
                    
                    if 1 <= week <= 18:
                        break
                    else:
                        console.print("[red]Week must be between 1 and 18[/red]")
                        
                except ValueError:
                    console.print("[red]Please enter a valid number[/red]")
            
            console.print(f"[green]Selected week: {week}[/green]")
            
            # Initialize matchups service
            matchups_service = MatchupsService(self.league_id)
            
            # Build matchups dataframe
            console.print("[blue]Building matchups data...[/blue]")
            df = matchups_service.build_matchups_dataframe(week)
            
            if df.empty:
                console.print("[red]❌ No matchup data found for this week[/red]")
                return
            
            # Export to CSV
            output_path = CSVExporter.export_matchups(df, self.league_id, week)
            
            # Show sample of matchups
            if len(df) > 0:
                console.print(f"\n[bold]📋 Week {week} Matchups (first 3):[/bold]")
                sample_table = Table()
                sample_table.add_column("Matchup", style="cyan")
                sample_table.add_column("Side A", style="green")
                sample_table.add_column("Side B", style="blue")
                sample_table.add_column("Records", style="yellow")
                
                for _, row in df.head(3).iterrows():
                    side_a_name = row['side_a_display_name'] or row['side_a_username'] or f"Roster {row['side_a_roster_id']}"
                    side_b_name = row['side_b_display_name'] or row['side_b_username'] or f"Roster {row['side_b_roster_id']}" if row['side_b_roster_id'] else "BYE"
                    
                    # Format points
                    side_a_points = f"{float(row['side_a_actual_points']):.1f}" if row['side_a_actual_points'] else "TBD"
                    side_b_points = f"{float(row['side_b_actual_points']):.1f}" if row['side_b_actual_points'] else "TBD"
                    
                    if side_b_name == "BYE":
                        matchup_display = f"{side_a_name} vs BYE"
                        records_display = f"{row['side_a_record_pre']}"
                    else:
                        matchup_display = f"#{row['matchup_id']}"
                        records_display = f"{row['side_a_record_pre']} vs {row['side_b_record_pre']}"
                    
                    sample_table.add_row(
                        matchup_display,
                        f"{side_a_name} ({side_a_points})",
                        f"{side_b_name} ({side_b_points})" if side_b_name != "BYE" else "BYE",
                        records_display
                    )
                
                console.print(sample_table)
            
            console.print(f"\n[bold green]✅ Week {week} matchups exported to: {output_path}[/bold green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error during week matchups export: {e}[/red]")
    
    def week_recap_flow(self) -> None:
        """Handle AI-powered week recap flow."""
        console.print("\n[bold blue]🤖 AI-Powered Week Recap[/bold blue]")
        
        try:
            # Get week number from user
            while True:
                try:
                    week_str = Prompt.ask("Enter NFL week number (1–18)")
                    week = int(week_str)
                    
                    if 1 <= week <= 18:
                        break
                    else:
                        console.print("[red]Week must be between 1 and 18[/red]")
                        
                except ValueError:
                    console.print("[red]Please enter a valid number[/red]")
            
            console.print(f"[green]Selected week: {week}[/green]")
            
            # Check for required environment variables
            from sleeper_agent.recap_orchestrator.config import RecapConfig
            try:
                RecapConfig.validate()
            except ValueError as e:
                console.print(f"[red]❌ Configuration error: {e}[/red]")
                console.print("[yellow]💡 Please set the required environment variables:[/yellow]")
                console.print("   • OPENAI_API_KEY")
                console.print("   • PERPLEXITY_API_KEY")
                return
            
            # Ask about forcing regeneration
            force_regenerate = False
            if Confirm.ask("Force regenerate all steps (ignore cached data)?", default=False):
                force_regenerate = True
            
            # Run the orchestrator
            from sleeper_agent.recap_orchestrator.main import run_weekly_recap
            
            console.print("\n[bold blue]🚀 Starting AI Weekly Recap Pipeline...[/bold blue]")
            console.print("[yellow]⏱️  This may take 2-5 minutes depending on API response times[/yellow]")
            
            try:
                final_path = run_weekly_recap(
                    week=week,
                    league_id=self.league_id,
                    force=force_regenerate,
                    verbose=True
                )
                
                console.print(f"\n[bold green]🎉 AI Weekly Recap completed![/bold green]")
                console.print(f"[green]📄 Generated recap: {final_path}[/green]")
                
                # Show file stats
                if final_path.exists():
                    with open(final_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        word_count = len(content.split())
                        
                    console.print(f"[cyan]📊 Final recap: {word_count} words[/cyan]")
                    
                    # Ask if user wants to see a preview
                    if Confirm.ask("Show preview of the recap?", default=True):
                        lines = content.splitlines()
                        preview_lines = lines[:10] if len(lines) > 10 else lines
                        
                        console.print("\n[bold]📖 Preview:[/bold]")
                        for line in preview_lines:
                            console.print(f"  {line}")
                        
                        if len(lines) > 10:
                            console.print(f"  ... ({len(lines) - 10} more lines)")
                
            except Exception as e:
                console.print(f"[red]❌ AI recap generation failed: {e}[/red]")
                
                if "Configuration error" in str(e):
                    console.print("\n[yellow]💡 Setup help:[/yellow]")
                    console.print("1. Get an OpenAI API key: https://platform.openai.com/")
                    console.print("2. Get a Perplexity API key: https://www.perplexity.ai/settings/api")
                    console.print("3. Set environment variables:")
                    console.print("   export OPENAI_API_KEY='your-key'")
                    console.print("   export PERPLEXITY_API_KEY='your-key'")
                    
        except Exception as e:
            console.print(f"[red]❌ Error during week recap: {e}[/red]")
    
    def run(self) -> None:
        """Run the main CLI application."""
        try:
            # Setup league
            if not self.setup_league():
                console.print("[red]❌ Setup cancelled[/red]")
                return
            
            # Main loop
            while True:
                choice = self.show_main_menu()
                
                if choice == "draft-recap":
                    self.draft_recap_flow()
                elif choice == "team-preview":
                    self.team_preview_flow()
                elif choice == "week-matchups":
                    self.week_matchups_flow()
                elif choice == "week-recap":
                    self.week_recap_flow()
                elif choice == "quit":
                    console.print("[blue]👋 Goodbye![/blue]")
                    break
                
                # Ask to continue
                if choice != "quit":
                    console.print()
                    if not Confirm.ask("Return to main menu?"):
                        console.print("[blue]👋 Goodbye![/blue]")
                        break
        
        except KeyboardInterrupt:
            console.print("\n[yellow]❌ Interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Unexpected error: {e}[/red]")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    league_id: Optional[str] = typer.Option(None, "--league-id", "-l", help="League ID to use")
) -> None:
    """Run the Sleeper Agent CLI."""
    # If a subcommand is invoked, don't run the interactive mode
    if ctx.invoked_subcommand is not None:
        return
    
    cli = SleeperCLI()
    
    # Override league ID if provided
    if league_id:
        cli.league_id = league_id
        cli.config.league_id = league_id
    
    cli.run()


@app.command("week-recap")
def week_recap(
    week: int = typer.Option(..., help="NFL week number (1–18)"),
    season: Optional[int] = typer.Option(None, help="NFL season year (defaults to current)"),
    outdir: Path = typer.Option("out", dir_okay=True, file_okay=False, help="Output directory"),
    force: bool = typer.Option(False, "--force", help="Force regeneration of all steps"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    league_id: Optional[str] = typer.Option(None, "--league-id", "-l", help="League ID to use")
) -> None:
    """Generate an AI-powered groupchat-ready weekly fantasy recap.
    
    Uses a 5-step pipeline to create comprehensive recaps with research,
    analysis, and proper citations. Requires OPENAI_API_KEY and 
    PERPLEXITY_API_KEY environment variables.
    """
    # Validate week range
    if not (1 <= week <= 18):
        console.print(f"[red]❌ Week must be between 1 and 18, got {week}[/red]")
        raise typer.Exit(1)
    
    try:
        # Setup configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Determine league_id
        target_league_id = league_id or config.league_id
        
        if not target_league_id:
            console.print("[red]❌ No league ID provided. Use --league-id or run interactive mode first.[/red]")
            raise typer.Exit(1)
        
        # Validate league
        league_service = LeagueService(target_league_id)
        is_valid, message = league_service.validate_league()
        
        if not is_valid:
            console.print(f"[red]❌ {message}[/red]")
            raise typer.Exit(1)
        
        if verbose:
            console.print(f"[green]{message}[/green]")
        
        # Check for required environment variables
        from sleeper_agent.recap_orchestrator.config import RecapConfig
        try:
            RecapConfig.validate()
        except ValueError as e:
            console.print(f"[red]❌ Configuration error: {e}[/red]")
            console.print("[yellow]💡 Please set the required environment variables:[/yellow]")
            console.print("   • OPENAI_API_KEY")
            console.print("   • PERPLEXITY_API_KEY")
            raise typer.Exit(1)
        
        # Run the orchestrator
        from sleeper_agent.recap_orchestrator.main import run_weekly_recap
        
        console.print(f"\n[bold blue]🚀 Generating AI Weekly Recap for Week {week}[/bold blue]")
        if verbose:
            console.print("[yellow]⏱️  This may take 2-5 minutes depending on API response times[/yellow]")
        
        try:
            final_path = run_weekly_recap(
                week=week,
                season=season,
                league_id=target_league_id,
                output_dir=outdir,
                force=force,
                verbose=verbose
            )
            
            console.print(f"\n[bold green]🎉 AI Weekly Recap completed![/bold green]")
            console.print(f"[green]📄 Generated recap: {final_path}[/green]")
            
            # Show file stats
            if final_path.exists() and verbose:
                with open(final_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    word_count = len(content.split())
                    
                console.print(f"[cyan]📊 Final recap: {word_count} words[/cyan]")
        
        except Exception as e:
            console.print(f"[red]❌ AI recap generation failed: {e}[/red]")
            
            if "Configuration error" in str(e):
                console.print("\n[yellow]💡 Setup help:[/yellow]")
                console.print("1. Get an OpenAI API key: https://platform.openai.com/")
                console.print("2. Get a Perplexity API key: https://www.perplexity.ai/settings/api")
                console.print("3. Set environment variables:")
                console.print("   export OPENAI_API_KEY='your-key'")
                console.print("   export PERPLEXITY_API_KEY='your-key'")
            
            if verbose:
                raise
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]❌ Error during week recap: {e}[/red]")
        if verbose:
            raise
        raise typer.Exit(1)


if __name__ == "__main__":
    app()