"""League-agnostic prompts for the recap orchestrator."""

def get_step1_prompt(season: int, week: int, step0_truth: str) -> str:
    """Step 1 - Research & Evidence (Perplexity Sonar-mini) - Optimized for focused research."""
    return f"""ROLE:
You are an expert fantasy football research analyst conducting focused, high-impact analysis for compelling storylines.

INPUTS:
- Canonical Step 0 truth (teams, rosters, matchups, records) for SEASON={season}, WEEK={week}.
- Research KEY PLAYERS from each team with both current week performance AND season-long outlook for WEEK {week}, SEASON {season}.

STEP 0 TRUTH:
{step0_truth}

STRATEGIC RESEARCH TASK:
You must conduct DEEP, FOCUSED research on the MOST IMPACTFUL PLAYERS from each team (2-3 players per team) for compelling storylines and analysis:

**PLAYER SELECTION PRIORITY:**
1. **Highest Fantasy Scorers**: Players with most fantasy points this week
2. **Biggest Storylines**: Players with largest projection vs actual gaps (over/under)
3. **Key Contributors**: Starting QBs, RB1s, WR1s who drive team success
4. **Breakout/Bust Candidates**: Players showing significant role changes or performance shifts

**FOCUS ON QUALITY OVER QUANTITY:**
Research 2-3 KEY PLAYERS per team instead of entire rosters. Prioritize players who will create the most compelling narratives and storylines for the recap.

**FOR STARTING PLAYERS (Priority Research):**
- Week {week} complete box score stats: yards, TDs, receptions, attempts, etc.
- Fantasy points scored and detailed breakdown by scoring category
- Weekly ranking/ECR vs actual performance gap analysis
- Snap count percentage and usage rate trends
- Target share, red zone looks, goal line usage
- Game script impact and pace of play effects
- Injury status during game and any limitations
- Weather/venue impacts on performance
- Matchup difficulty analysis (opponent rankings vs position)

**FOR SELECTED KEY PLAYERS (Deep Season Analysis):**
- **Trajectory Analysis**: Week-over-week trend analysis, usage changes, emerging patterns
- **Role Security**: Depth chart position, snap share trends, coach comments, beat writer reports
- **Opportunity Outlook**: Upcoming schedule strength, injury situations ahead of player, role expansion potential
- **Boom/Bust Profile**: Historical variance, ceiling games, floor concerns, game script dependency
- **Injury Intel**: Current health status, injury history, durability red flags, expected impact timeline
- **Expert Consensus**: FantasyPros ROS rankings, expert trade/start/sit recommendations, dynasty value
- **Advanced Metrics**: Air yards, target quality, snap route participation, red zone market share
- **Schedule Analysis**: Upcoming playoff matchups, bye week timing, strength of schedule ROS

**FOCUSED RESEARCH SOURCES:**
- FantasyPros: Weekly rankings, ROS outlook, expert consensus for key players
- ESPN: Player news, injury reports, snap counts, target shares for storyline players
- NFL.com: Official injury reports, depth chart updates for impact players
- The Athletic: Beat writer insights for team's top performers and breakout candidates
- Team beat writers: Local insight on usage, health, and opportunity for key storylines

**EXPERT QUOTES & ANALYSIS:**
- 2-3 expert quotes covering the MOST COMPELLING storylines from this team
- Focus on analyst predictions about the biggest surprises/disappointments
- Source beat writer comments about the most impactful player performances
- Reference coaching staff comments about key contributors and role changes

**FOCUSED RESEARCH REQUIREMENTS:**
- STRATEGIC FOCUS: Research 2-3 MOST IMPACTFUL players per team with INTENSIVE detail
- STORYLINE PRIORITY: Focus on players who create the most compelling narratives
- EXPERT INTEGRATION: Gather multiple expert opinions on the biggest storylines
- PROJECTION ANALYSIS: Emphasize biggest gaps between projected vs actual performance
- SEASON-LONG FOCUS: Detailed trajectory analysis and future outlook for every player
- INJURY INTELLIGENCE: Complete health status and durability assessment
- ROLE ANALYSIS: Snap counts, usage rates, and opportunity trends
- BREAKOUT ASSESSMENT: Identify potential season-long breakouts and sleepers
- HANDCUFF VALUES: Analyze backup/depth players and their upside potential

OUTPUT (valid JSON with comprehensive data):
{{
  "player_evidence": [
    {{
      "player": "Player Name",
      "team_name": "Fantasy Team Name from Step 0",
      "is_starter": true,
      "week_stats": {{
        "fantasy_points": 18.5,
        "passing_yards": 250,
        "passing_tds": 2,
        "rushing_yards": 35,
        "receptions": 4,
        "receiving_yards": 42,
        "snap_count_percentage": 85.2,
        "target_share": 22.1,
        "red_zone_looks": 3
      }},
      "projection_context": "Projected 15.2 points (FantasyPros consensus, #12 weekly rank), actual 18.5 points (#8 weekly finish)",
      "season_outlook": {{
        "trajectory": "trending up - increased target share from 18% to 22%, usage expanding in red zone",
        "role_security": "locked-in starter with 85% snap share, coach praised versatility this week",
        "boom_bust_profile": "high ceiling (30+ point games possible), moderate floor due to TD dependency and game script",
        "ros_projection": "RB2 with RB1 upside in plus matchups, FantasyPros consensus RB18 ROS",
        "breakout_potential": "already established but showing signs of increased efficiency and usage",
        "schedule_analysis": "favorable ROS schedule, 3 top-10 matchups in fantasy playoffs",
        "advanced_metrics": "22% target share, 15.2 air yards per target, 45% route participation"
      }},
      "injury": {{
        "status": "healthy",
        "impact": "none",
        "durability": "missed 2 games last season with ankle, otherwise durable",
        "current_concerns": "none reported"
      }},
      "opportunity_notes": "Benefits from improved O-line play, goal-line role expanding, team struggling in red zone creates more opportunity",
      "handcuff_value": "N/A - is the starter, backup is unproven rookie",
      "expert_analysis": "Multiple analysts upgrading ROS outlook based on increased usage and efficiency trends",
      "advanced_notes": "First game back from bye week, snap count increasing weekly, coach mentioned expanded role",
      "quotes": [
        {{"text": "His usage is trending in right direction, expect 15+ touches per game ROS", "source": "ESPN analyst"}},
        {{"text": "One of the more undervalued assets in fantasy right now", "source": "FantasyPros expert"}}
      ],
      "quote_source_id": 1,
      "kickoff_window": "Sun Early"
    }}
  ],
  "references": [
    {{"id": 1, "title": "Week {week} Fantasy Analysis", "url": "https://www.espn.com/fantasy/football/", "publisher": "ESPN", "date": "{season}-09-15"}},
    {{"id": 2, "title": "ROS Outlook Update", "url": "https://www.fantasypros.com/", "publisher": "FantasyPros", "date": "{season}-09-14"}},
    {{"id": 3, "title": "Snap Count Analysis", "url": "https://www.pro-football-reference.com/", "publisher": "PFR", "date": "{season}-09-13"}}
  ]
}}"""

def get_step2_prompt(week: int, season: int, step0_truth: str, step1_evidence: str) -> str:
    """Step 2 - Simplified Plan (OpenAI GPT-5) - Reduced token count."""
    return f"""Create a concise plan for a fantasy football recap for Week {week}, {season}.

DATA:
{step0_truth}

PLAYER EVIDENCE:
{step1_evidence}

OUTPUT: Brief numbered plan covering:

1. LEDE: Top 3 storylines from this week
2. MATCHUPS: Key narrative for each matchup
3. POWER RANKINGS: Ranking approach using records and points
4. Structure should be 1500-2000 words total

Focus on the most compelling player performances and team storylines. Keep plan concise."""

def get_step3_prompt(week: int, season: int, step0_truth: str, step1_evidence: str, step2_plan: str) -> str:
    """Step 3 - Write (OpenAI GPT-4)."""
    team_count = step0_truth.count('"team_name":')
    
    return f"""ROLE:
ESPN-style columnist with Bleacher Report energy; PG-13; Oxford commas; no em dashes. Audience: a fantasy league groupchat.

INPUTS:
- Step 0 truth (rosters, scores, records).
- Step 1 evidence (stats, projection context, performance analysis, kickoff windows).
- Step 2 plan.

STEP 0 TRUTH:
{step0_truth}

STEP 1 EVIDENCE:
{step1_evidence}

STEP 2 PLAN:
{step2_plan}

TEAM RECORD & SCORING DATA USAGE:
- Step 0 Truth contains cumulative records (wins-losses) AND total points_for/points_against through Week {week}
- REQUIRED: Include each team's record after the specified week in all matchup headers
- REQUIRED: Use points_for and points_against data to inform power rankings and team evaluations
- Example: "Team A (2-0, 245.3 PF, 180.2 PA) vs Team B (1-1, 220.1 PF, 200.8 PA)"
- Power Rankings MUST factor in: record, total points scored (points_for), defensive strength (points_against), and roster depth

STRICT PLAYER-TEAM ATTRIBUTION RULES:
- CRITICAL: Only mention players who appear in Step 1 Evidence player_evidence array
- CRITICAL: Use the EXACT team_name from Step 1 Evidence for each player mentioned
- FORBIDDEN: Never mention players not explicitly listed in Step 1 Evidence
- FORBIDDEN: Never guess or assume player-team relationships
- FORBIDDEN: Never make up player information or stats
- FORBIDDEN: Never create fictional player performances or associations
- FORBIDDEN: Never assume a player belongs to a team unless verified in Step 1 Evidence
- VERIFICATION REQUIRED: Before writing about any player, confirm they exist in Step 1 Evidence with correct team
- STARTERS ONLY: Step 1 Evidence contains only starting players - these are the only players who contributed to team wins/losses
- DATA INTEGRITY: If uncertain about any player-team relationship, omit that player rather than guess

CONTENT RULES:
- TARGET LENGTH: 1200-1500 words (much longer than previous attempts)
- Include exact final score and both teams' records for every matchup
- NO SOURCES: Do not include a Sources section in the final output
- Focus on Week {week} narratives and performances
- Include Good/Bad/Ugly per matchup with specific stats from Step 1 Evidence
- Work in timeline elements: TNF, early games, late surges, SNF/MNF drama
- Note injuries and impact using Step 1 Evidence data
- Reference projections vs actual performance from Step 1 Evidence

STRUCTURE (aim for 2000-2500 words):
1) Engaging Lede (300-400 words): Set the week's tone with major storylines and key narratives
2) Detailed Matchup Breakdowns (1100-1400 words):
   - CRITICAL: Cover ALL matchups from Step 0 truth - ensure no matchup is missed
   - Header: Team A vs Team B: <A score>–<B score> (Team A Record, PF, PA vs Team B Record, PF, PA)
   - Example Header: "Warriors vs Knights: 145.2–132.8 (2-0, 285.4 PF, 210.6 PA vs 1-1, 265.3 PF, 245.2 PA)"
   - Rich narrative paragraph (180-220 words per matchup) including:
     * Key player performances with exact stats from Step 1 Evidence
     * Timeline beats and game flow
     * Projection vs actual performance analysis
     * Conversational discussion of what went well, what struggled, and notable surprises
     * Commentary on how this result affects each team's season trajectory
     * Deep analysis of bench impact and missed opportunities
     * Strategic implications for both teams moving forward
     * NO explicit "Good/Bad/Ugly" headers - weave these themes naturally into the narrative
3) Weekly Wrap-up (200-250 words): League trends, standings analysis, and broader implications using cumulative data
4) **MANDATORY Power Rankings Section (700-900 words)**:
   - CRITICAL: This section is REQUIRED and must be included in EVERY recap
   - Header: "**Power Rankings**"
   - CRITICAL: Must include ALL 14 teams (clackpanthers, frankchainzzz, myleshugee, Bward242, oats4, jakemaus, lamp68, patrickzepf, jimmysteeze, Willx1149, ac58, LennaShakes, bootiemunchers, adhamsobhy)
   - Rank ALL teams 1-14 using HOLISTIC team strength evaluation:
   - PRIMARY FACTORS (most important):
     * Points_for trends and offensive ceiling potential
     * Roster talent depth and future outlook (analyze ALL players in Step 0, both starters and bench)
     * Player trajectory and season-long projections for key contributors
     * Boom/bust potential of roster construction and player profiles
   - SECONDARY FACTORS:
     * Current record (wins-losses) and recent performance trends
     * Points_against and defensive performance (for context, not primary ranking)
     * Schedule difficulty and matchup luck (both past and upcoming)
     * Injury situations and depth chart implications
   - RANKING PHILOSOPHY: A 0-2 team with elite talent and high points_for could rank above a 2-0 team with low scoring
   - EXPLANATION REQUIREMENTS: 1-2 sentences per team covering talent assessment, outlook, and key factors driving their ranking
   - FUTURE FOCUS: Emphasize which teams are built for sustained success vs. lucky/unlucky starts
   - LUCK ANALYSIS: Consider teams that are scoring well but losing (unlucky) vs. teams winning with low scores (lucky)
   - BENCH DEPTH: Factor in unused talent that could become starters, handcuffs, and potential waiver wire upgrades
   - CEILING vs FLOOR: Evaluate which teams have highest upside potential even if current record doesn't reflect it
   - FORMAT: Number each team clearly (1. Team Name, 2. Team Name, etc.) with 4-5 sentences explaining their ranking
   - VERIFICATION: Double-check that all 14 teams are included before finishing the power rankings

CRITICAL OUTPUT REQUIREMENTS:
- Power Rankings section is MANDATORY - the article is incomplete without it
- CRITICAL: Must include ALL 14 teams in power rankings (clackpanthers, frankchainzzz, myleshugee, Bward242, oats4, jakemaus, lamp68, patrickzepf, jimmysteeze, Willx1149, ac58, LennaShakes, bootiemunchers, adhamsobhy)
- CRITICAL: Cover ALL matchups from Step 0 truth in matchup breakdowns
- ABSOLUTELY NO SOURCES SECTION - Do not include any sources, references, citations, or bibliography at the end
- FORBIDDEN: No "Sources:", "References:", or any citation list in the final output
- The article should end immediately after the Power Rankings section

WRITING REQUIREMENTS:
- Every matchup should get substantial coverage (150-200 words minimum)
- Longer, more comprehensive analysis throughout
- Use specific player stats from Step 1 Evidence: "Player X: 85 yards, 7 catches, 15.5 fantasy points"
- Reference projection context: "projected 12.0 but delivered 15.5"
- Include injury impacts and timeline drama
- Conversational, groupchat-friendly tone throughout
- Text-message friendly, no tables or complex formatting
- For Power Rankings: CRITICAL - Use Step 1 Evidence season_outlook data for ALL players (starters + bench) to evaluate:
  * Team talent depth and roster construction quality
  * Bench players with breakout potential or handcuff value
  * Teams with high upside vs. teams at their ceiling
  * Injury concerns and role security across the roster
  * Which teams have the best combination of current performance AND future outlook

FINAL OUTPUT FORMAT:
- Start with the engaging lede
- Include all matchup breakdowns with headers
- Include weekly wrap-up
- Include comprehensive power rankings section
- END IMMEDIATELY after power rankings - NO sources, references, or citations
- Ready to paste directly into a group text

OUTPUT:
Only the final article content as specified above."""

def get_step4_patch_prompt(article_text: str, issues_json: str, step0_truth: str, step1_evidence: str) -> str:
    """Step 4 - Patch (only if audit fails; OpenAI GPT-4)."""
    return f"""ROLE:
You patch an existing article with minimal edits.

INPUTS:
- The article text.
- A JSON array of issues with {{type, location_snippet, fix_instruction}}.
- Step 0 truth and Step 1 evidence (for validation).

ARTICLE TEXT:
{article_text}

ISSUES TO FIX:
{issues_json}

STEP 0 TRUTH:
{step0_truth}

STEP 1 EVIDENCE:
{step1_evidence}

TASK:
Apply the smallest possible edits that satisfy all fix_instructions while preserving tone, length target, and structure. Do not introduce new players or claims beyond Step 1 evidence. Maintain citations [#] and Sources list.

OUTPUT:
Return only the patched article text."""