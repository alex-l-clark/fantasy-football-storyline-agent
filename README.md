# 🏈 Sleeper Fantasy Football Weekly Recap Generator

**Transform your fantasy football league into engaging stories with AI-powered weekly recaps!**

## What This Does

This tool takes your Sleeper Fantasy Football league and automatically generates **comprehensive weekly recaps** that combine:

- 📈 **Real Statistical Analysis** - Points scored, lineup decisions, waiver wire moves, and performance trends
- 📰 **Current NFL Storylines** - Latest news, injuries, and developments affecting your players
- 🎯 **Smart Commentary** - AI-powered insights that connect real NFL events to your fantasy outcomes
- 📊 **Data-Driven Insights** - Advanced analytics on team performance, optimal lineups, and season trends

Perfect for sharing in your league group chat, these recaps turn raw fantasy data into compelling narratives that make your league more engaging and fun!

## Key Features

✨ **One-Click Weekly Recaps**: Simply enter your league ID and week number
🔍 **Real NFL Research**: Automatically pulls in current storylines and player news
📱 **Group Chat Ready**: Formatted for easy sharing in Discord, Slack, or text
🎲 **Bench Analysis**: Covers not just starters, but key bench decisions and missed opportunities
📈 **Season Context**: Tracks season-long trends and storylines
🤖 **AI-Powered**: Uses advanced language models to create engaging, readable content

## Sample Output

Your weekly recap will include sections like:

- **Week Overview**: Key matchups and storylines
- **Top Performances**: Highest scorers with context about their real NFL games
- **Biggest Disappointments**: Poor performances explained with injury/game context
- **Bench Decisions**: Critical sit/start choices that impacted outcomes
- **Looking Ahead**: Preview of next week's key storylines

Each section combines your league's actual data with real NFL context, creating recaps that are both informative and entertaining.

## Requirements

### API Keys (Required)

To generate AI-powered recaps, you'll need two free API keys:

1. **OpenAI API Key** (for AI analysis and writing)
   - Sign up at: https://platform.openai.com/
   - Cost: ~$1-3 per recap (depending on league size)

2. **Perplexity API Key** (for real-time NFL research)
   - Sign up at: https://www.perplexity.ai/settings/api
   - Cost: ~$0.50-1 per recap

### System Requirements
- Python 3.11+
- Your Sleeper Fantasy Football league ID

## Installation & Setup

### Step 1: Download the Software

```bash
# Download the project
git clone https://github.com/alex-l-clark/fantasy-football-storyline-agent.git
cd fantasy-football-storyline-agent
```

### Step 2: Set Up Python Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate it (Mac/Linux)
source venv/bin/activate

# Activate it (Windows)
venv\Scripts\activate

# Install the software
pip install -r requirements.txt
```

### Step 3: Configure Your API Keys

You'll need to set up your API keys as environment variables:

**Option A: Create a .env file (Recommended for beginners)**
1. Copy the example file: `cp .env.example .env`
2. Edit the `.env` file and add your keys:
   ```
   OPENAI_API_KEY=your_openai_key_here
   PERPLEXITY_API_KEY=your_perplexity_key_here
   ```

**Option B: Set environment variables directly**
```bash
# Mac/Linux
export OPENAI_API_KEY="your_openai_key_here"
export PERPLEXITY_API_KEY="your_perplexity_key_here"

# Windows
set OPENAI_API_KEY=your_openai_key_here
set PERPLEXITY_API_KEY=your_perplexity_key_here
```

## How to Use

### Finding Your League ID

1. Go to your Sleeper league in a web browser
2. Look at the URL: `https://sleeper.app/leagues/XXXXXXXXX/team`
3. The number in the middle (XXXXXXXXX) is your league ID

### Running the Recap Generator

1. **Start the program:**
   ```bash
   python -m sleeper_agent.cli
   ```

2. **Enter your league ID** when prompted (it will be saved for future use)

3. **Select "week-recap"** from the menu

4. **Choose which NFL week** you want to recap (1-18)

5. **Wait 2-5 minutes** while the AI:
   - Analyzes your league's data for that week
   - Researches current NFL storylines
   - Generates comprehensive recap content

6. **Get your recap!** The finished file will be saved and you can copy/paste it into your group chat

### Advanced Usage

You can also run recaps directly from the command line:

```bash
# Generate recap for week 5
python -m sleeper_agent.cli week-recap --week 5 --league-id YOUR_LEAGUE_ID

# Force regeneration (ignore any cached data)
python -m sleeper_agent.cli week-recap --week 5 --force
```

## Cost Information

**Typical costs per recap:**
- OpenAI (GPT-4): $1-3 depending on league size and complexity
- Perplexity: $0.50-1 for research queries
- **Total: ~$1.50-4 per recap**

Costs scale with:
- Number of teams in your league
- Amount of detailed analysis requested
- Length of generated content

## Troubleshooting

### "Configuration error" messages
- Double-check your API keys are set correctly
- Make sure you have credits in both OpenAI and Perplexity accounts
- Verify the keys aren't expired

### "No league data found"
- Confirm your league ID is correct
- Make sure the league is public or you have access
- Try a different week number

### Python/Installation issues
- Ensure you're using Python 3.11 or newer: `python --version`
- Make sure your virtual environment is activated
- Try reinstalling: `pip install -r requirements.txt --force-reinstall`

## Privacy & Data

- Your league data is processed temporarily to generate recaps
- No league data is stored permanently
- API keys are only used for generating your content
- All data stays on your local machine

## Support

Need help?
- Check the troubleshooting section above
- Open an issue on GitHub: https://github.com/alex-l-clark/fantasy-football-storyline-agent/issues

---

**Ready to make your fantasy league more engaging? Get started above! 🏈🤖**