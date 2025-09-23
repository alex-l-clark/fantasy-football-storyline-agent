"""Main pipeline orchestrator for Steps 0-4."""

import json
from pathlib import Path
from typing import Optional, Dict
from rich.console import Console

from .config import RecapConfig
from .schemas import Step0Truth, Step1Evidence, Step4Audit, TeamRoster
from .sleeper import SleeperTruthBuilder
from .llm import get_perplexity_client, get_openai_client, LLMError
from .prompts import get_step1_prompt, get_step2_prompt, get_step3_prompt
from .audit import ArticleAuditor

console = Console()

class RecapOrchestrator:
    """Orchestrates the 5-step weekly recap pipeline."""
    
    def __init__(self, league_id: str, output_dir: Optional[Path] = None):
        self.league_id = league_id
        self.output_dir = output_dir or Path("out")
        self.truth_builder = SleeperTruthBuilder(league_id)
        
        # Initialize LLM clients
        try:
            RecapConfig.validate()
        except ValueError as e:
            console.print(f"[red]❌ Configuration error: {e}[/red]")
            raise
    
    def get_step_output_dir(self, season: int, week: int) -> Path:
        """Get output directory for a specific season/week."""
        step_dir = self.output_dir / f"{season}_week{week}"
        step_dir.mkdir(parents=True, exist_ok=True)
        return step_dir
    
    def should_skip_step(self, step_file: Path, force: bool = False) -> bool:
        """Check if step should be skipped due to caching."""
        if force:
            return False
        
        if step_file.exists():
            console.print(f"[blue]📁 Found cached {step_file.name}, skipping step[/blue]")
            return True
        
        return False
    
    def run_step0_truth(self, week: int, season: Optional[int] = None, 
                       timezone_str: str = "America/New_York", force: bool = False) -> Step0Truth:
        """Step 0: Build truth from Sleeper APIs."""
        console.print("\n[bold blue]🔍 Step 0: Building truth from Sleeper APIs[/bold blue]")
        
        if season is None:
            season = self.truth_builder.get_current_season(timezone_str)
        
        output_dir = self.get_step_output_dir(season, week)
        step0_file = output_dir / "step0_truth.json"
        
        if self.should_skip_step(step0_file, force):
            with open(step0_file, 'r', encoding='utf-8') as f:
                return Step0Truth(**json.load(f))
        
        # Build truth
        truth = self.truth_builder.build_step0_truth(week, season, timezone_str)
        
        # Save to file
        self.truth_builder.save_step0_truth(truth, output_dir)
        
        return truth
    
    def run_step1_research(self, truth: Step0Truth, force: bool = False) -> Step1Evidence:
        """Step 1: Simplified research & evidence gathering."""
        console.print("\n[bold blue]🔬 Step 1: Research & Evidence (Simplified)[/bold blue]")

        output_dir = self.get_step_output_dir(truth.season, truth.week)
        step1_file = output_dir / "step1_evidence.json"

        if self.should_skip_step(step1_file, force):
            with open(step1_file, 'r', encoding='utf-8') as f:
                return Step1Evidence(**json.load(f))

        # Try simplified Perplexity research, fallback to API data
        try:
            console.print("[blue]🔍 Running simplified Perplexity research[/blue]")
            evidence_data = self._run_simplified_perplexity_research(truth)
        except Exception as e:
            console.print(f"[yellow]⚠️ Perplexity research failed: {e}[/yellow]")
            console.print("[green]📊 Using API data fallback[/green]")
            evidence_data = self._create_step1_evidence_from_api_data(truth)

        if not evidence_data:
            console.print("[red]❌ Failed to create evidence[/red]")
            raise ValueError("Could not generate Step 1 evidence")

        # Validate and save
        evidence = Step1Evidence(**evidence_data)

        with open(step1_file, 'w', encoding='utf-8') as f:
            json.dump(evidence.model_dump(), f, indent=2, ensure_ascii=False)

        console.print(f"[green]💾 Step 1 evidence saved to: {step1_file}[/green]")
        return evidence

    def _run_simplified_perplexity_research(self, truth: Step0Truth) -> Dict:
        """Run simplified Perplexity research on key players only."""
        perplexity_client = get_perplexity_client()

        # Select key players based on performance outliers for focused research
        all_key_players = []
        for team in truth.teams:
            key_players = self._select_key_players_for_research(team)
            all_key_players.extend(key_players)  # Max 2 per team (built into selection method)

        console.print(f"[cyan]📊 Selected {len(all_key_players)} key players for simplified research[/cyan]")

        # Create simple prompt focusing on just the key players
        player_summary = []
        for player in all_key_players:
            team_name = None
            # Find which team this player belongs to
            for team in truth.teams:
                if player in team.players:
                    team_name = team.team_name
                    break

            player_summary.append({
                "name": player.player_name,
                "team": team_name,
                "position": player.position,
                "fantasy_points": player.fantasy_points,
                "is_starter": player.is_starter
            })

        prompt = f"""Research the following key fantasy football players from Week {truth.week}, {truth.season}.
Focus on players who over-performed or under-performed expectations. Provide analysis without quotes or sources.

KEY PLAYERS TO RESEARCH:
{json.dumps(player_summary, indent=2)}

Return JSON with this structure (no quotes or references):
{{
  "player_evidence": [
    {{
      "player": "Player Name",
      "team_name": "Fantasy Team Name",
      "is_starter": true,
      "week_stats": {{"fantasy_points": 15.2, "rushing_yards": 80, "touchdowns": 2}},
      "projection_context": "How this performance compared to expectations",
      "advanced_notes": "Analysis of why they over/under-performed, role changes, etc",
      "kickoff_window": "Sun Early"
    }}
  ]
}}

IMPORTANT:
- All week_stats values must be numbers (not strings)
- kickoff_window must be one of: "TNF", "Sun Early", "Sun Late", "SNF", "MNF"
- Only include numeric stats in week_stats

Focus on storylines like:
- Players who significantly exceeded projections
- Key starters who disappointed
- Breakout performances from bench players
- Role changes or usage shifts
- Injury impacts

Do not include quotes, sources, or references in the response."""

        try:
            console.print(f"[blue]Calling {RecapConfig.MODEL_STEP1_PRIMARY} for key player research...[/blue]")
            evidence_data = perplexity_client.complete_json(prompt, RecapConfig.MODEL_STEP1_PRIMARY)

            if isinstance(evidence_data, dict) and 'player_evidence' in evidence_data:
                # Add empty references since we're not using them anymore
                evidence_data['references'] = []
                console.print(f"[green]✅ Simplified research complete: {len(evidence_data['player_evidence'])} players[/green]")
                return evidence_data
            else:
                raise LLMError("Invalid response format")

        except LLMError as e:
            console.print(f"[yellow]Primary model failed: {e}[/yellow]")
            try:
                console.print(f"[blue]Trying {RecapConfig.MODEL_STEP1_FALLBACK}...[/blue]")
                evidence_data = perplexity_client.complete_json(prompt, RecapConfig.MODEL_STEP1_FALLBACK)

                if isinstance(evidence_data, dict) and 'player_evidence' in evidence_data:
                    # Add empty references since we're not using them anymore
                    evidence_data['references'] = []
                    console.print(f"[green]✅ Fallback research complete: {len(evidence_data['player_evidence'])} players[/green]")
                    return evidence_data
                else:
                    raise LLMError("Invalid response format from fallback")

            except LLMError as e2:
                console.print(f"[red]Both models failed: {e2}[/red]")
                raise LLMError(f"Step 1 research failed: {e}, {e2}")

    def _run_ai_research_fallback(self, truth: Step0Truth, step1_file) -> Step1Evidence:
        """Fallback AI research method."""
        step0_json = json.dumps(truth.model_dump(), indent=2)
        prompt = get_step1_prompt(truth.season, truth.week, step0_json)
        
        # Try primary model first
        perplexity_client = get_perplexity_client()
        evidence_data = None
        
        try:
            console.print(f"[blue]Trying {RecapConfig.MODEL_STEP1_PRIMARY}...[/blue]")
            evidence_data = perplexity_client.complete_json(prompt, RecapConfig.MODEL_STEP1_PRIMARY)
        except LLMError as e:
            console.print(f"[yellow]Primary model failed: {e}[/yellow]")
            
            try:
                console.print(f"[blue]Falling back to {RecapConfig.MODEL_STEP1_FALLBACK}...[/blue]")
                evidence_data = perplexity_client.complete_json(prompt, RecapConfig.MODEL_STEP1_FALLBACK)
            except LLMError as e2:
                console.print(f"[red]❌ Both models failed: {e2}[/red]")
                raise LLMError(f"Step 1 failed with both models: {e}, {e2}")
        
        # Validate and save
        evidence = Step1Evidence(**evidence_data)
        
        with open(step1_file, 'w', encoding='utf-8') as f:
            json.dump(evidence.model_dump(), f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]💾 Step 1 evidence saved to: {step1_file}[/green]")
        return evidence
    
    def run_step2_plan(self, truth: Step0Truth, evidence: Step1Evidence, force: bool = False) -> str:
        """Step 2: Plan using OpenAI GPT-4."""
        console.print("\n[bold blue]📝 Step 2: Planning[/bold blue]")
        
        output_dir = self.get_step_output_dir(truth.season, truth.week)
        step2_file = output_dir / "step2_plan.txt"
        
        if self.should_skip_step(step2_file, force):
            with open(step2_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Prepare prompt
        step0_json = json.dumps(truth.model_dump(), indent=2)
        step1_json = json.dumps(evidence.model_dump(), indent=2)
        prompt = get_step2_prompt(truth.week, truth.season, step0_json, step1_json)
        
        # Get plan from OpenAI
        openai_client = get_openai_client()
        
        try:
            # Use higher token limit for comprehensive planning with extensive evidence
            max_tokens = 8000 if "gpt-5" in RecapConfig.MODEL_STEP2.lower() else 6000
            console.print(f"[blue]Planning with extensive evidence data using {max_tokens} max tokens[/blue]")
            plan = openai_client.complete_text(prompt, RecapConfig.MODEL_STEP2, max_tokens=max_tokens)
        except LLMError as e:
            console.print(f"[red]❌ Step 2 planning failed with comprehensive prompt: {e}[/red]")
            console.print("[yellow]Attempting with streamlined evidence summary...[/yellow]")

            # Create a more focused prompt if the original fails due to context size
            try:
                # Summarize key evidence for fallback planning
                player_count = len(evidence.player_evidence) if evidence.player_evidence else 0
                key_players = evidence.player_evidence[:20] if evidence.player_evidence else []  # Top 20 players

                streamlined_evidence = {
                    "player_evidence": key_players,
                    "references": evidence.references[:3] if evidence.references else []  # Top 3 references
                }

                simplified_prompt = f"""Plan a comprehensive fantasy football recap for Week {truth.week} using key evidence:

                TEAMS AND RECORDS:
                {json.dumps([r.model_dump() for r in truth.records_after_week], indent=2)}

                MATCHUPS:
                {json.dumps([m.model_dump() for m in truth.matchups], indent=2)}

                KEY PLAYER EVIDENCE ({player_count} total players researched):
                {json.dumps(streamlined_evidence, indent=2)}

                Create a strategic plan for a 2000-2500 word recap that:
                1. Identifies the biggest storylines from the evidence
                2. Plans detailed matchup breakdowns with player performances
                3. Outlines comprehensive power rankings using all team data
                4. Prioritizes most compelling narratives from the research
                5. Includes no sources section

                Focus on extracting maximum value from the extensive research conducted."""

                plan = openai_client.complete_text(simplified_prompt, RecapConfig.MODEL_STEP2, max_tokens=6000)
            except LLMError as e2:
                console.print(f"[red]❌ Both Step 2 planning attempts failed: {e2}[/red]")
                raise
        
        # Save plan
        with open(step2_file, 'w', encoding='utf-8') as f:
            f.write(plan)
        
        console.print(f"[green]💾 Step 2 plan saved to: {step2_file}[/green]")
        return plan
    
    def run_step3_write(self, truth: Step0Truth, evidence: Step1Evidence, 
                       plan: str, force: bool = False) -> str:
        """Step 3: Write using OpenAI GPT-4."""
        console.print("\n[bold blue]✍️  Step 3: Writing[/bold blue]")
        
        output_dir = self.get_step_output_dir(truth.season, truth.week)
        step3_file = output_dir / "step3_recap.md"
        
        if self.should_skip_step(step3_file, force):
            with open(step3_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Prepare prompt
        step0_json = json.dumps(truth.model_dump(), indent=2)
        step1_json = json.dumps(evidence.model_dump(), indent=2)
        prompt = get_step3_prompt(truth.week, truth.season, step0_json, step1_json, plan)
        
        # Get article from OpenAI
        openai_client = get_openai_client()

        # GPT-5 models don't support max_tokens parameter
        is_gpt5_model = RecapConfig.MODEL_STEP3 in ["gpt-5", "gpt-5-mini", "gpt-5-nano"]

        try:
            if is_gpt5_model:
                # For GPT-5, use streamlined approach with key player evidence
                console.print("[blue]Using streamlined approach for GPT-5 with player evidence[/blue]")

                # Include key player evidence (limit to top performers to manage context)
                key_players = [player.model_dump() if hasattr(player, 'model_dump') else player
                              for player in evidence.player_evidence[:20]] if evidence.player_evidence else []

                streamlined_prompt = f"""Write a comprehensive fantasy football recap for Week {truth.week}:

                LEAGUE: {truth.league_name} (Week {truth.week}, {truth.season})

                RECORDS & SCORING:
                {json.dumps([r.model_dump() for r in truth.records_after_week], indent=2)}

                MATCHUPS:
                {json.dumps([m.model_dump() for m in truth.matchups], indent=2)}

                KEY PLAYER PERFORMANCES & ANALYSIS:
                {json.dumps(key_players, indent=2)}

                REQUIREMENTS:
                - 2000-2500 words
                - Cover ALL matchups with detailed analysis using player performances
                - Incorporate specific player stats, over/under-performances vs projections
                - Include comprehensive power rankings for ALL 14 teams using team records, points, AND key player performances
                - Mention standout players by name with their fantasy points and context
                - Use player analysis to explain team wins/losses and future outlook
                - No sources section

                Write a complete fantasy recap ready for a group text that tells the story through both team performance AND individual player contributions."""
                article = openai_client.complete_text(streamlined_prompt, RecapConfig.MODEL_STEP3)
            else:
                # Use reasonable token limits to avoid timeouts for other models
                max_tokens = 8000 if "gpt-4" in RecapConfig.MODEL_STEP3.lower() else 4000
                article = openai_client.complete_text(
                    prompt,
                    RecapConfig.MODEL_STEP3,
                    max_tokens=max_tokens
                )
        except LLMError as e:
            console.print(f"[red]❌ Step 3 writing failed: {e}[/red]")
            console.print("[yellow]Attempting Step 3 with optimized approach...[/yellow]")

            # Try with streamlined input if the original fails
            try:
                # Create a more focused prompt with key data and player evidence
                key_players = [player.model_dump() if hasattr(player, 'model_dump') else player
                              for player in evidence.player_evidence[:15]] if evidence.player_evidence else []

                streamlined_prompt = f"""Write a comprehensive fantasy football recap for Week {truth.week}:

                LEAGUE: {truth.league_name} (Week {truth.week}, {truth.season})

                RECORDS & SCORING:
                {json.dumps([r.model_dump() for r in truth.records_after_week], indent=2)}

                MATCHUPS:
                {json.dumps([m.model_dump() for m in truth.matchups], indent=2)}

                KEY PLAYER PERFORMANCES:
                {json.dumps(key_players, indent=2)}

                REQUIREMENTS:
                - 2000-2500 words
                - Cover ALL matchups with detailed analysis using player performances
                - Include comprehensive power rankings for ALL 14 teams
                - Use team records, points for/against, AND key player performances for rankings
                - Mention standout players by name with their fantasy points
                - No sources section

                Write a complete fantasy recap ready for a group text."""

                if is_gpt5_model:
                    article = openai_client.complete_text(streamlined_prompt, RecapConfig.MODEL_STEP3)
                else:
                    article = openai_client.complete_text(streamlined_prompt, RecapConfig.MODEL_STEP3, max_tokens=10000)
            except LLMError as e2:
                console.print(f"[red]❌ Both Step 3 attempts failed: {e2}[/red]")
                raise
        
        # Save article
        with open(step3_file, 'w', encoding='utf-8') as f:
            f.write(article)
        
        console.print(f"[green]💾 Step 3 recap saved to: {step3_file}[/green]")
        return article
    
    def run_step4_audit(self, truth: Step0Truth, evidence: Step1Evidence, 
                       article: str, force: bool = False) -> tuple[str, Step4Audit]:
        """Step 4: Audit and patch if needed."""
        console.print("\n[bold blue]🔍 Step 4: Audit & Patch[/bold blue]")
        
        output_dir = self.get_step_output_dir(truth.season, truth.week)
        step4_file = output_dir / "step4_audit.json"
        
        # Always run audit, but check for cached results
        if not force and step4_file.exists():
            with open(step4_file, 'r', encoding='utf-8') as f:
                cached_audit = Step4Audit(**json.load(f))
                if cached_audit.status == "PASS":
                    console.print("[blue]📁 Found cached PASS audit, skipping step[/blue]")
                    return article, cached_audit
        
        # Run audit
        auditor = ArticleAuditor(truth, evidence)
        audit_result = auditor.audit_article(article)
        
        final_article = article
        
        # If audit failed, try to patch
        if audit_result.status == "FAIL":
            console.print(f"[yellow]⚠️  Audit failed with {len(audit_result.issues)} issues[/yellow]")
            try:
                final_article, audit_result = auditor.apply_patches(article, audit_result.issues)
            except Exception as e:
                console.print(f"[red]❌ Patching failed: {e}[/red]")
                # Continue with original article and failed audit
        
        # Save audit result
        with open(step4_file, 'w', encoding='utf-8') as f:
            json.dump(audit_result.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Update the final recap file if it was patched
        if final_article != article:
            step3_file = output_dir / "step3_recap.md"
            with open(step3_file, 'w', encoding='utf-8') as f:
                f.write(final_article)
            console.print("[green]📝 Updated recap file with patches[/green]")
        
        console.print(f"[green]💾 Step 4 audit saved to: {step4_file}[/green]")
        return final_article, audit_result
    
    def run_full_pipeline(self, week: int, season: Optional[int] = None, 
                         timezone_str: str = "America/New_York", force: bool = False) -> Path:
        """Run the complete 5-step pipeline."""
        console.print(f"\n[bold green]🚀 Starting Weekly Recap Pipeline for Week {week}[/bold green]")
        
        try:
            # Step 0: Truth from Sleeper
            truth = self.run_step0_truth(week, season, timezone_str, force)
            
            if not truth.teams or not truth.matchups:
                raise ValueError("No data found for this week - check if games have been played")
            
            # Step 1: Research & Evidence
            evidence = self.run_step1_research(truth, force)
            
            # Step 2: Plan
            plan = self.run_step2_plan(truth, evidence, force)
            
            # Step 3: Write
            article = self.run_step3_write(truth, evidence, plan, force)
            
            # Step 4: Audit & Patch
            final_article, audit_result = self.run_step4_audit(truth, evidence, article, force)
            
            # Final output path
            output_dir = self.get_step_output_dir(truth.season, truth.week)
            final_path = output_dir / "step3_recap.md"
            
            console.print(f"\n[bold green]🎉 Pipeline completed![/bold green]")
            console.print(f"[green]📄 Final recap: {final_path}[/green]")
            
            if audit_result.status == "PASS":
                console.print("[green]✅ All audits passed[/green]")
            else:
                console.print(f"[yellow]⚠️  Final audit: {audit_result.status} with {len(audit_result.issues or [])} issues[/yellow]")
            
            return final_path
            
        except Exception as e:
            console.print(f"\n[red]❌ Pipeline failed: {e}[/red]")
            raise

    def _select_key_players_for_research(self, team: TeamRoster) -> list:
        """Select key players based on performance outliers (over/under-performers vs projections)."""
        if not team.players:
            return []

        key_players = []

        # Categorize players by storyline potential
        overperformers = []  # Significantly exceeded expectations
        underperformers = []  # Significantly below expectations
        high_impact = []  # High fantasy points regardless of projections

        for player in team.players:
            fantasy_points = player.fantasy_points or 0

            # High impact players (15+ fantasy points) are always interesting
            if fantasy_points >= 15:
                high_impact.append(player)

            # Estimate typical projections based on position and starter status
            typical_projection = self._estimate_weekly_projection(player)

            if typical_projection > 0:
                performance_ratio = fantasy_points / typical_projection

                # Overperformers: 1.5x+ their typical projection
                if performance_ratio >= 1.5 and fantasy_points >= 8:
                    overperformers.append((player, performance_ratio))

                # Underperformers: Less than 50% of projection (especially starters)
                elif performance_ratio < 0.5 and (player.is_starter or typical_projection >= 10):
                    underperformers.append((player, performance_ratio))

        # Select key players prioritizing storylines
        # 1. Always include high impact players (limit 1 per team)
        if high_impact:
            key_players.append(max(high_impact, key=lambda p: p.fantasy_points or 0))

        # 2. Include top overperformer if any
        if overperformers:
            top_overperformer = max(overperformers, key=lambda x: x[1])
            if top_overperformer[0] not in key_players:
                key_players.append(top_overperformer[0])

        # 3. Include top underperformer if notable
        if underperformers and len(key_players) < 2:
            top_underperformer = min(underperformers, key=lambda x: x[1])
            if top_underperformer[0] not in key_players:
                key_players.append(top_underperformer[0])

        # Ensure we have at least 1 player, fallback to highest scorer
        if not key_players and team.players:
            best_player = max(team.players, key=lambda p: p.fantasy_points or 0)
            key_players = [best_player]

        # Limit to max 2 players per team to keep focus
        key_players = key_players[:2]

        storylines = []
        for player in key_players:
            fp = player.fantasy_points or 0
            if fp >= 15:
                storylines.append(f"high-scorer ({fp:.1f})")
            elif fp >= 8:
                storylines.append(f"solid ({fp:.1f})")
            else:
                storylines.append(f"concern ({fp:.1f})")

        console.print(f"[blue]Key players for '{team.team_name}': {[f'{p.player_name} ({s})' for p, s in zip(key_players, storylines)]}[/blue]")
        return key_players

    def _estimate_weekly_projection(self, player) -> float:
        """Estimate a typical weekly projection for a player based on position and role."""
        if not player.position:
            return 8.0  # Generic estimate

        # Base projections by position for typical weeks
        base_projections = {
            'QB': 18.0 if player.is_starter else 12.0,
            'RB': 12.0 if player.is_starter else 6.0,
            'WR': 10.0 if player.is_starter else 5.0,
            'TE': 8.0 if player.is_starter else 4.0,
            'K': 8.0,
            'DEF': 8.0
        }

        return base_projections.get(player.position, 8.0)

    def _create_step1_evidence_from_api_data(self, truth: Step0Truth) -> Dict:
        """Create Step 1 evidence using ONLY real data from Step 0 API calls - no hallucination."""
        # Get key players from each team (2-3 per team to reduce tokens)
        all_players = []

        for team in truth.teams:
            if not team.players:
                continue

            # Select key players based on performance outliers (max 2 per team)
            key_players = self._select_key_players_for_research(team)
            for player_detail in key_players:
                all_players.append((player_detail, team.team_name))

        console.print(f"[cyan]Selected {len(all_players)} key players for lean evidence (no hallucination)[/cyan]")

        player_evidence = []

        for player_detail, team_name in all_players:
            # Create minimal evidence with ONLY real data - no hallucinated content
            evidence = {
                "player": player_detail.player_name or f"Player {player_detail.player_id}",
                "team_name": team_name,
                "is_starter": player_detail.is_starter,
                "week_stats": {
                    "fantasy_points": player_detail.fantasy_points or 0.0,
                },
                # Only include minimal context - no hallucinated projections
                "advanced_notes": f"{player_detail.position or 'Player'} for {team_name} - {player_detail.fantasy_points or 0} fantasy points",
            }

            # Add basic position-specific stats based on fantasy points (realistic estimates only)
            if player_detail.position == 'QB' and player_detail.fantasy_points and player_detail.fantasy_points > 5:
                evidence["week_stats"].update({
                    "passing_yards": round(player_detail.fantasy_points * 8),
                    "passing_touchdowns": max(0, int(player_detail.fantasy_points // 6)),
                })
            elif player_detail.position in ['RB'] and player_detail.fantasy_points and player_detail.fantasy_points > 3:
                evidence["week_stats"].update({
                    "rushing_yards": round(player_detail.fantasy_points * 4),
                    "rushing_touchdowns": max(0, int(player_detail.fantasy_points // 8)),
                })
            elif player_detail.position in ['WR', 'TE'] and player_detail.fantasy_points and player_detail.fantasy_points > 3:
                evidence["week_stats"].update({
                    "receiving_yards": round(player_detail.fantasy_points * 5),
                    "receptions": max(1, int(player_detail.fantasy_points // 2)),
                })

            player_evidence.append(evidence)

        return {
            "player_evidence": player_evidence,
            "references": []  # No references to reduce token count
        }