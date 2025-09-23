# AI-Powered Weekly Fantasy Football Recap

Generate professional, ESPN-style fantasy football recaps for your Sleeper league using AI. This system creates comprehensive, groupchat-ready recaps that include research, analysis, quotes, and power rankings.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up API Keys

You'll need API keys from two providers:

**Anthropic API Key:**
1. Visit https://console.anthropic.com/
2. Create an account and get your API key (starts with `sk-ant-`)

**Perplexity API Key:**
1. Visit https://www.perplexity.ai/settings/api
2. Create an account and get your API key (starts with `pplx-`)

**Configure Your Keys (Choose One Method):**

**Option A: Use the .env file (Recommended)**
```bash
# Edit the .env file and add your keys
nano .env

# Then load it
source .env
```

**Option B: Set environment variables directly**
```bash
export ANTHROPIC_API_KEY='your-key-here'
export PERPLEXITY_API_KEY='your-key-here'
```

**League Configuration:**
The league ID is automatically handled by the CLI system - no environment variable needed!

### 3. Generate Your First Recap

**Interactive Mode:**
```bash
python -m sleeper_agent
# Choose option 4: "week-recap - Generate AI-powered groupchat recap"
```

**Command Line:**
```bash
python -m sleeper_agent week-recap --week 1 --verbose
```

## 🏗️ How It Works

The system uses a 5-step pipeline to create high-quality recaps:

### Step 0: Truth Building (Free)
- Fetches canonical data from Sleeper APIs
- Builds team rosters, matchup results, and records
- No LLM usage - pure data extraction

### Step 1: Research & Evidence (~$0.01-0.05)
- **Model**: Perplexity Sonar-mini (primary) / Sonar (fallback)
- Gathers box score stats, projections vs. actuals
- Finds quotes from ESPN, NFL.com, The Athletic
- Identifies injuries and kickoff windows
- **Output**: Structured JSON with citations

### Step 2: Planning (~$0.001)
- **Model**: Claude 3.7 Haiku
- Creates detailed outline for the article
- Plans matchup coverage and power rankings approach
- **Output**: Numbered outline

### Step 3: Writing (~$0.05-0.15)
- **Model**: Claude 3.7 Sonnet  
- Generates 900-1500 word ESPN-style recap
- Includes proper citations, quotes, and analysis
- **Output**: Groupchat-ready markdown article

### Step 4: Audit & Patch (~$0.001-0.01)
- **Programmatic checks**: Player-team binding, scores, citations
- **AI patches**: Claude 3.7 Haiku fixes any issues
- **Output**: Final validated article + audit report

## 💰 Cost Breakdown

**Typical cost per recap: $0.06-0.21**

| Step | Model | Typical Cost | Purpose |
|------|-------|-------------|----------|
| 0 | None | $0.00 | Data extraction |
| 1 | Sonar-mini | $0.01-0.05 | Research & citations |
| 2 | Claude Haiku | ~$0.001 | Article planning |
| 3 | Claude Sonnet | $0.05-0.15 | Article writing |
| 4 | Claude Haiku | ~$0.001-0.01 | Error fixing |

*Costs vary based on league size, player activity, and research depth*

## 🛠️ Advanced Usage

### Command Line Options
```bash
python -m sleeper_agent week-recap \
    --week 5 \                    # Required: NFL week (1-18)
    --season 2024 \              # Optional: NFL season (defaults to current)
    --outdir ./my-recaps \       # Optional: Output directory
    --force \                    # Optional: Force regeneration of all steps
    --verbose \                  # Optional: Detailed progress output
    --league-id 123456789        # Optional: Override league ID
```

### Environment Variables

**Required:**
- `ANTHROPIC_API_KEY` - Claude API key
- `PERPLEXITY_API_KEY` - Perplexity API key

**Note:** League ID is handled automatically by the CLI system - no environment variable needed!

**Optional Model Overrides:**
- `MODEL_STEP1_PRIMARY=sonar-mini` - Research model (primary)
- `MODEL_STEP1_FALLBACK=sonar` - Research model (fallback)
- `MODEL_STEP2=claude-3-7-haiku-2025-07-15` - Planning model
- `MODEL_STEP3=claude-3-7-sonnet-2025-07-15` - Writing model
- `MODEL_STEP4_PATCH=claude-3-7-haiku-2025-07-15` - Patch model

**Other Options:**
- `TIMEZONE=America/New_York` - Timezone for season calculation

### Caching & Performance

The system caches each step's output to avoid expensive re-computation:

```
out/
└── 2024_week5/
    ├── step0_truth.json      # Sleeper data (always regenerated)
    ├── step1_evidence.json   # Research results (cached)
    ├── step2_plan.txt        # Article outline (cached)
    ├── step3_recap.md        # Final article (cached)
    └── step4_audit.json      # Audit results (cached)
```

Use `--force` to regenerate all cached data.

## 📋 Output Format

The generated recap includes:

### Structure
1. **Lede** - 3-5 punchy opening sentences
2. **Matchup Recaps** - Each with:
   - Final scores and records
   - Timeline beats (TNF/Early/Late/SNF/MNF)
   - Good/Bad/Ugly analysis with stats
   - Injury updates and projections context
3. **Power Rankings** - 1-sentence outlook per team
4. **Sources** - Numbered citations with links

### Style Guidelines
- ✅ ESPN analyst tone with energy
- ✅ PG-13 language appropriate for group chats
- ✅ Oxford commas throughout
- ✅ 900-1500 words
- ❌ No em dashes (uses regular hyphens)
- ❌ No tables (text-message friendly)

## 🔧 Troubleshooting

### Common Issues

**"Configuration error: Missing required environment variables"**
```bash
# Solution: Set your API keys (league ID handled by CLI)
export ANTHROPIC_API_KEY='your-anthropic-key'
export PERPLEXITY_API_KEY='your-perplexity-key'
```

**"No matchup data found for this week"**
- Games may not have been played yet
- Check if the week number is correct (1-18)
- Verify your league has scheduled games for that week

**"Failed to parse JSON from API response"**
- Usually a temporary API issue - try again
- The system has automatic retry logic with backoff
- Check your API key validity and rate limits

**"Player not found in Step 0 truth"**
- The audit system caught an error (good!)
- This triggers automatic patching
- Should resolve automatically, but may indicate data issues

### Rate Limits
- **Anthropic**: ~0.5 seconds between requests
- **Perplexity**: ~1.0 seconds between requests
- Automatic retry with exponential backoff
- Total runtime: typically 2-5 minutes

### Debug Mode
```bash
python -m sleeper_agent week-recap --week 1 --verbose
```

Shows:
- Step-by-step progress
- Token usage estimates
- Cost calculations
- Detailed error messages

## 🎯 Best Practices

### When to Generate Recaps
- **Tuesday/Wednesday**: After Monday Night Football concludes
- **Avoid Sunday**: Games still in progress, incomplete data
- **Check Sleeper**: Ensure fantasy scores are finalized

### Cost Optimization
- Use caching effectively (don't use `--force` unless needed)
- Smaller leagues = lower costs (fewer players to research)
- Mid-season weeks typically cost less than Week 1

### Quality Tips
- Verify league settings match your expectations
- Check that injury reports are current
- Review citations for accuracy before sharing

## 🤝 Contributing

The AI Weekly Recap system is part of the broader Sleeper Agent project. The codebase follows these principles:

- **Modular design**: Each step is independent and cacheable
- **Error resilience**: Automatic fallbacks and retries
- **Cost awareness**: Optimized model selection for each task
- **League agnostic**: Works with any Sleeper league configuration

### Key Files
```
sleeper_agent/recap_orchestrator/
├── config.py          # Environment and model configuration
├── schemas.py         # Pydantic models for data validation  
├── sleeper.py         # Step 0: Truth building from Sleeper APIs
├── llm.py            # Step 1,2,3,4: LLM client abstraction
├── prompts.py        # League-agnostic prompt templates
├── audit.py          # Step 4: Programmatic validation
├── pipeline.py       # Main orchestrator
└── main.py          # CLI integration
```

## 📄 License

This project uses the same license as the parent Sleeper Agent project.

## 🆘 Support

For issues, questions, or feature requests:
1. Check this README for common solutions
2. Review the verbose output for specific error details
3. Ensure your API keys are correctly configured
4. Try regenerating with the `--force` flag

---

**Ready to create your first AI-powered fantasy recap?**

```bash
export ANTHROPIC_API_KEY='your-key'
export PERPLEXITY_API_KEY='your-key'

python -m sleeper_agent week-recap --week 1 --verbose
```