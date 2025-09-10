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
        menu_table.add_row("4", "week-recap - Export player-level week recap to CSV")
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
        """Handle week recap flow."""
        console.print("\n[bold blue]📊 Week Recap[/bold blue]")
        
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
            
            # Initialize week recap service
            week_recap_service = WeekRecapService(self.league_id)
            
            # Build week recap dataframe
            console.print("[blue]Building player-level week recap data...[/blue]")
            df = week_recap_service.build_week_recap_dataframe(week)
            
            if df.empty:
                console.print("[red]❌ No week recap data found for this week[/red]")
                return
            
            # Export to CSV
            output_path = CSVExporter.export_week_recap(df, self.league_id, week)
            
            # Show sample of data
            if len(df) > 0:
                console.print(f"\n[bold]📋 Week {week} Player Performance (first 5 players):[/bold]")
                sample_table = Table()
                sample_table.add_column("Player", style="green")
                sample_table.add_column("Team", style="blue")  
                sample_table.add_column("Position", style="cyan")
                sample_table.add_column("Fantasy Points", style="yellow")
                sample_table.add_column("Matchup", style="white")
                
                for _, row in df.head(5).iterrows():
                    team_name = row['side_display_name'] or row['side_username'] or f"Roster {row['side_roster_id']}"
                    opp_name = row['opp_username'] or f"Roster {row['opp_roster_id']}" if row['opp_roster_id'] else "BYE"
                    
                    # Format fantasy points
                    fantasy_points = f"{float(row['player_points']):.1f}" if row['player_points'] != "" else "N/A"
                    
                    # Format matchup info
                    if opp_name == "BYE":
                        matchup_info = f"{team_name} (BYE)"
                    else:
                        side_points = f"{float(row['side_total_points']):.1f}" if row['side_total_points'] != "" else "N/A"
                        opp_points = f"{float(row['opp_total_points']):.1f}" if row['opp_total_points'] != "" else "N/A"
                        matchup_info = f"{team_name} ({side_points}) vs {opp_name} ({opp_points})"
                    
                    sample_table.add_row(
                        row['player_name'],
                        row['nfl_team'] or "N/A",
                        row['position'] or "N/A", 
                        fantasy_points,
                        matchup_info
                    )
                
                console.print(sample_table)
            
            console.print(f"\n[bold green]✅ Week {week} recap exported to: {output_path}[/bold green]")
            
        except Exception as e:
            console.print(f"[red]❌ Error during week recap export: {e}[/red]")
    
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
    outdir: Path = typer.Option("out", dir_okay=True, file_okay=False, help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    league_id: Optional[str] = typer.Option(None, "--league-id", "-l", help="League ID to use")
) -> None:
    """Export a player-level CSV recap for all matchups in the given week.
    
    Includes team totals, winners/losers, and each starter's fantasy points
    when provided by Sleeper. Uses official endpoints only.
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
        
        # Initialize week recap service
        console.print(f"[blue]🏈 Generating week {week} recap for league {target_league_id}[/blue]")
        week_recap_service = WeekRecapService(target_league_id)
        
        # Build week recap dataframe
        df = week_recap_service.build_week_recap_dataframe(week)
        
        if df.empty:
            console.print("[red]❌ No week recap data found for this week[/red]")
            raise typer.Exit(1)
        
        # Ensure output directory exists
        outdir.mkdir(parents=True, exist_ok=True)
        
        # Export to CSV
        filename = f"week_recap_{target_league_id}_week{week}.csv"
        output_path = outdir / filename
        
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        console.print(f"[green]✅ Week {week} recap exported to: {output_path}[/green]")
        console.print(f"[blue]📊 {len(df)} player rows exported[/blue]")
        
        if verbose and len(df) > 0:
            unique_players = df['player_id'].nunique()
            unique_matchups = df['matchup_id'].nunique()
            players_with_points = df[df['player_points'] != ""].shape[0]
            
            console.print(f"[cyan]📈 Summary: {unique_players} unique players across {unique_matchups} matchups[/cyan]")
            console.print(f"[cyan]🎯 {players_with_points}/{len(df)} players have fantasy points data[/cyan]")
        
    except Exception as e:
        console.print(f"[red]❌ Error during week recap export: {e}[/red]")
        if verbose:
            raise
        raise typer.Exit(1)


if __name__ == "__main__":
    app()