"""Programmatic audit system with player-team binding validation."""

import json
import re
from typing import Dict, List, Set, Tuple, Optional
from rich.console import Console

from .schemas import Step0Truth, Step1Evidence, Step4Issue, Step4Audit
from .llm import get_openai_client
from .prompts import get_step4_patch_prompt
from .config import RecapConfig

console = Console()

class ArticleAuditor:
    """Audits article content against Step 0 truth and Step 1 evidence."""
    
    def __init__(self, step0_truth: Step0Truth, step1_evidence: Step1Evidence):
        self.step0_truth = step0_truth
        self.step1_evidence = step1_evidence
        
        # Build lookup tables
        self.player_to_team = self._build_player_team_mapping()
        self.team_matchups = self._build_team_matchups()
        self.reference_ids = {ref["id"] for ref in step1_evidence.references}
    
    def _build_player_team_mapping(self) -> Dict[str, str]:
        """Build mapping from player name to team name from Step 0."""
        player_to_team = {}
        
        for team in self.step0_truth.teams:
            team_name = team.team_name
            for player_id in team.roster:
                # We need to normalize player names for lookup
                # For now, use player_id as key - in practice, we'd need player name resolution
                player_to_team[player_id] = team_name
        
        # Also add evidence mappings (which should include player names)
        for evidence in self.step1_evidence.player_evidence:
            player_to_team[evidence.player] = evidence.team_name
        
        return player_to_team
    
    def _build_team_matchups(self) -> Dict[str, Dict]:
        """Build team matchup information from Step 0."""
        team_matchups = {}
        
        for matchup in self.step0_truth.matchups:
            team_matchups[matchup.team_a] = {
                "opponent": matchup.team_b,
                "score": matchup.team_a_score,
                "opponent_score": matchup.team_b_score,
                "winner": matchup.winner,
                "loser": matchup.loser
            }
            
            if matchup.team_b != "BYE":
                team_matchups[matchup.team_b] = {
                    "opponent": matchup.team_a,
                    "score": matchup.team_b_score,
                    "opponent_score": matchup.team_a_score,
                    "winner": matchup.winner,
                    "loser": matchup.loser
                }
        
        return team_matchups
    
    def audit_article(self, article_text: str) -> Step4Audit:
        """Perform comprehensive audit of the article."""
        console.print("[blue]🔍 Running Step 4 audit...[/blue]")
        
        issues = []
        
        # Check player-team binding
        issues.extend(self._audit_player_team_binding(article_text))
        
        # Check scores and records
        issues.extend(self._audit_scores_and_records(article_text))
        
        # Check citation mapping
        issues.extend(self._audit_citations(article_text))
        
        # Check style requirements
        issues.extend(self._audit_style(article_text))
        
        if issues:
            console.print(f"[yellow]⚠️  Found {len(issues)} issues[/yellow]")
            return Step4Audit(status="FAIL", issues=issues)
        else:
            console.print("[green]✅ Article passed all audits[/green]")
            return Step4Audit(status="PASS")
    
    def _audit_player_team_binding(self, article_text: str) -> List[Step4Issue]:
        """Check that every mentioned player belongs to the correct team."""
        issues = []
        
        # Extract player names mentioned in the article
        player_mentions = self._extract_player_mentions(article_text)
        
        for player_name, context in player_mentions:
            # Try to find this player in our mapping
            correct_team = None
            for mapped_player, team in self.player_to_team.items():
                if self._names_match(player_name, mapped_player):
                    correct_team = team
                    break
            
            if correct_team is None:
                issues.append(Step4Issue(
                    type="player_not_in_step0",
                    location_snippet=context,
                    fix_instruction=f"Remove or replace '{player_name}' as they don't appear in Step 0 rosters"
                ))
                continue
            
            # Check if the player is attributed to the correct team in context
            if not self._check_team_attribution_in_context(context, correct_team):
                issues.append(Step4Issue(
                    type="incorrect_team_attribution",
                    location_snippet=context,
                    fix_instruction=f"Ensure '{player_name}' is attributed to '{correct_team}' not another team"
                ))
        
        return issues
    
    def _audit_scores_and_records(self, article_text: str) -> List[Step4Issue]:
        """Check that scores and records match Step 0 truth."""
        issues = []
        
        # Extract score mentions (pattern like "Team A 123.4–Team B 89.2")
        score_pattern = r'([A-Za-z\s]+?)[\s]*(\d+\.?\d*)[-–—]([A-Za-z\s]+?)[\s]*(\d+\.?\d*)'
        score_matches = re.finditer(score_pattern, article_text)
        
        for match in score_matches:
            team_a_text = match.group(1).strip()
            score_a = float(match.group(2))
            team_b_text = match.group(3).strip()
            score_b = float(match.group(4))
            
            context = match.group(0)
            
            # Try to match teams to Step 0 data
            step0_matchup = self._find_matching_step0_matchup(team_a_text, team_b_text)
            if step0_matchup:
                if (abs(score_a - step0_matchup.team_a_score) > 0.1 or 
                    abs(score_b - step0_matchup.team_b_score) > 0.1):
                    issues.append(Step4Issue(
                        type="incorrect_score",
                        location_snippet=context,
                        fix_instruction=f"Correct scores to {step0_matchup.team_a_score}–{step0_matchup.team_b_score}"
                    ))
        
        # Check record mentions (pattern like "(2-1)" or "2-1")
        record_pattern = r'\(?(\d+[-–]\d+(?:\.\d+)?)\)?'
        record_matches = re.finditer(record_pattern, article_text)
        
        for match in record_matches:
            record_text = match.group(1)
            context = self._get_context_around_match(article_text, match, 50)
            
            # Try to identify which team this record refers to
            team_name = self._extract_team_from_record_context(context)
            if team_name:
                correct_record = self._get_correct_record_for_team(team_name)
                if correct_record and correct_record != record_text:
                    issues.append(Step4Issue(
                        type="incorrect_record",
                        location_snippet=context,
                        fix_instruction=f"Correct '{team_name}' record to {correct_record}"
                    ))
        
        return issues
    
    def _audit_citations(self, article_text: str) -> List[Step4Issue]:
        """Check that all citations map to Step 1 references."""
        issues = []
        
        # Find all citation references [1], [2], etc.
        citation_pattern = r'\[(\d+)\]'
        citations = re.findall(citation_pattern, article_text)
        
        for citation_id_str in citations:
            citation_id = int(citation_id_str)
            if citation_id not in self.reference_ids:
                issues.append(Step4Issue(
                    type="invalid_citation",
                    location_snippet=f"[{citation_id}]",
                    fix_instruction=f"Remove citation [{citation_id}] or map to valid reference from Step 1"
                ))
        
        # Check that Sources section matches Step 1 references
        sources_section = self._extract_sources_section(article_text)
        if sources_section:
            for ref in self.step1_evidence.references:
                ref_id = ref["id"]
                expected_source = f"[{ref_id}] {ref['publisher']} — {ref['title']} ({ref['url']})"
                if expected_source not in sources_section:
                    issues.append(Step4Issue(
                        type="missing_source_entry",
                        location_snippet="Sources section",
                        fix_instruction=f"Add or correct source entry for reference {ref_id}"
                    ))
        
        return issues
    
    def _audit_style(self, article_text: str) -> List[Step4Issue]:
        """Check style requirements."""
        issues = []
        
        # Check for em dashes (should use regular dashes)
        if '—' in article_text or '–' in article_text:
            # Allow these in scores, but not elsewhere
            non_score_em_dashes = re.findall(r'[^0-9\s]([—–])[^0-9\s]', article_text)
            if non_score_em_dashes:
                issues.append(Step4Issue(
                    type="em_dashes_found",
                    location_snippet="Multiple locations",
                    fix_instruction="Replace em dashes with regular hyphens or rewrite sentences"
                ))
        
        # Check word count
        word_count = len(article_text.split())
        if word_count < 900:
            issues.append(Step4Issue(
                type="word_count_low",
                location_snippet="Overall article",
                fix_instruction=f"Expand article from {word_count} to 900-1500 words"
            ))
        elif word_count > 1500:
            issues.append(Step4Issue(
                type="word_count_high",
                location_snippet="Overall article",
                fix_instruction=f"Trim article from {word_count} to 900-1500 words"
            ))
        
        # Check for Oxford comma heuristic (basic check)
        # Look for patterns like "A, B and C" which should be "A, B, and C"
        oxford_violations = re.findall(r'\w+,\s+\w+\s+and\s+\w+', article_text)
        if len(oxford_violations) > 3:  # Allow some flexibility
            issues.append(Step4Issue(
                type="oxford_comma_missing",
                location_snippet=f"Example: {oxford_violations[0]}",
                fix_instruction="Add Oxford commas before 'and' in lists"
            ))
        
        return issues
    
    def apply_patches(self, article_text: str, issues: List[Step4Issue], max_attempts: int = 2) -> Tuple[str, Step4Audit]:
        """Apply patches using LLM and re-audit."""
        console.print(f"[yellow]🔧 Applying patches for {len(issues)} issues...[/yellow]")
        
        current_text = article_text
        
        for attempt in range(max_attempts):
            console.print(f"[blue]Patch attempt {attempt + 1}/{max_attempts}[/blue]")
            
            # Create patch prompt
            issues_json = json.dumps([issue.model_dump() for issue in issues], indent=2)
            step0_truth_json = json.dumps(self.step0_truth.model_dump(), indent=2)
            step1_evidence_json = json.dumps(self.step1_evidence.model_dump(), indent=2)
            
            patch_prompt = get_step4_patch_prompt(
                current_text, issues_json, step0_truth_json, step1_evidence_json
            )
            
            # Get patch from LLM
            openai_client = get_openai_client()
            try:
                # GPT-4 supports higher token limits
                max_tokens = 8000 if "gpt-4" in RecapConfig.MODEL_STEP4_PATCH.lower() else 4000
                patched_text = openai_client.complete_text(
                    patch_prompt, 
                    RecapConfig.MODEL_STEP4_PATCH,
                    max_tokens=max_tokens
                )
                
                # Re-audit the patched text
                audit_result = self.audit_article(patched_text)
                
                if audit_result.status == "PASS":
                    console.print(f"[green]✅ Patches successful after attempt {attempt + 1}[/green]")
                    return patched_text, audit_result
                else:
                    console.print(f"[yellow]Still {len(audit_result.issues)} issues after attempt {attempt + 1}[/yellow]")
                    current_text = patched_text
                    issues = audit_result.issues
                    
            except Exception as e:
                console.print(f"[red]❌ Patch attempt {attempt + 1} failed: {e}[/red]")
                break
        
        # If we get here, patching failed
        console.print("[red]❌ Patching failed after maximum attempts[/red]")
        final_audit = self.audit_article(current_text)
        return current_text, final_audit
    
    # Helper methods for text processing
    
    def _extract_player_mentions(self, text: str) -> List[Tuple[str, str]]:
        """Extract player name mentions with context."""
        # This is a simplified implementation
        # In practice, would need more sophisticated NER or player name matching
        mentions = []
        
        # Look for capitalized names that might be players
        name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        for match in re.finditer(name_pattern, text):
            name = match.group(0)
            context = self._get_context_around_match(text, match, 100)
            mentions.append((name, context))
        
        return mentions
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two names refer to the same player."""
        # Simple implementation - could be more sophisticated
        name1_clean = name1.lower().strip()
        name2_clean = name2.lower().strip()
        
        return name1_clean == name2_clean or name1_clean in name2_clean or name2_clean in name1_clean
    
    def _check_team_attribution_in_context(self, context: str, correct_team: str) -> bool:
        """Check if the context correctly attributes the player to the team."""
        # Look for team name in the surrounding context
        return correct_team.lower() in context.lower()
    
    def _find_matching_step0_matchup(self, team_a_text: str, team_b_text: str):
        """Find matching matchup from Step 0 based on team names."""
        for matchup in self.step0_truth.matchups:
            if (self._team_names_match(team_a_text, matchup.team_a) and 
                self._team_names_match(team_b_text, matchup.team_b)):
                return matchup
            elif (self._team_names_match(team_a_text, matchup.team_b) and 
                  self._team_names_match(team_b_text, matchup.team_a)):
                # Return with swapped scores
                from types import SimpleNamespace
                return SimpleNamespace(
                    team_a_score=matchup.team_b_score,
                    team_b_score=matchup.team_a_score
                )
        return None
    
    def _team_names_match(self, text_name: str, step0_name: str) -> bool:
        """Check if team names match (allowing for abbreviations)."""
        text_clean = text_name.lower().strip()
        step0_clean = step0_name.lower().strip()
        
        return (text_clean == step0_clean or 
                text_clean in step0_clean or 
                step0_clean in text_clean)
    
    def _get_context_around_match(self, text: str, match, chars: int) -> str:
        """Get context around a regex match."""
        start = max(0, match.start() - chars)
        end = min(len(text), match.end() + chars)
        return text[start:end]
    
    def _extract_team_from_record_context(self, context: str) -> Optional[str]:
        """Extract team name from record context."""
        # Look for team names from Step 0 in the context
        for team in self.step0_truth.teams:
            if team.team_name.lower() in context.lower():
                return team.team_name
        return None
    
    def _get_correct_record_for_team(self, team_name: str) -> Optional[str]:
        """Get the correct record for a team from Step 0."""
        for record in self.step0_truth.records_after_week:
            if record.team_name == team_name:
                return record.record
        return None
    
    def _extract_sources_section(self, text: str) -> Optional[str]:
        """Extract the Sources section from the article."""
        sources_match = re.search(r'Sources\s*:?\s*(.*?)(?:\n\n|\Z)', text, re.DOTALL | re.IGNORECASE)
        if sources_match:
            return sources_match.group(1)
        return None