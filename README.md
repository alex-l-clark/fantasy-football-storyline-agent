# Sleeper Fantasy Football CLI Agent

A comprehensive command-line tool for analyzing and exporting Sleeper Fantasy Football league data. Built with Python, this tool provides easy access to draft recaps, team rosters, and weekly matchup analysis with comprehensive CSV exports.

## Features

### 🏈 Current Functionality

- **Draft Recap**: Export complete draft analysis with pick-by-pick breakdown
- **Team Preview**: Export detailed roster analysis for any league member  
- **Week Matchups**: Export weekly head-to-head matchups with records and lineups

### 📊 Export Formats

All data exports to CSV format with the following outputs:
- `out/draft_{league_id}_{draft_id}.csv` - Complete draft recap
- `out/roster_{league_id}_{username}_{timestamp}.csv` - Team roster export
- `out/matchups_{league_id}_week{week}.csv` - Weekly matchup analysis

## Installation

### Prerequisites

- Python 3.11+
- Sleeper Fantasy Football league access

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/alex-l-clark/fantasy-football-storyline-agent.git
   cd fantasy-football-storyline-agent
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Interactive CLI

Start the interactive command-line interface:

```bash
python -m sleeper_agent.cli
```

The CLI will guide you through:

1. **League Setup**: Enter your Sleeper league ID (cached for future use)
2. **Menu Selection**: Choose from available analysis options
3. **Data Export**: Automatic CSV generation with progress indicators

### Menu Options

#### 1. Draft Recap
- Exports complete draft analysis
- Includes player info, team names, and pick details
- Shows draft summary and first 5 picks preview

#### 2. Team Preview  
- Select any league member
- Exports their complete roster
- Shows player positions, NFL teams, and roster status

#### 3. Week Matchups ⭐ *New Feature*
- Enter NFL week number (1-18)
- Exports all league matchups for that week
- Includes both teams' records through the previous week
- Shows complete starting lineups
- Handles bye weeks automatically

### Week Matchups CSV Schema

The matchups export includes 18 columns with comprehensive head-to-head data:

```
league_id, week, matchup_id,
side_a_roster_id, side_a_username, side_a_display_name, side_a_team_name, 
side_a_record_pre, side_a_projected_points, side_a_actual_points, side_a_starters,
side_b_roster_id, side_b_username, side_b_display_name, side_b_team_name,
side_b_record_pre, side_b_projected_points, side_b_actual_points, side_b_starters
```

**Key Features:**
- **Deterministic Side Assignment**: Lower roster_id = Side A, Higher = Side B
- **Accurate Records**: Calculated by comparing actual points from previous weeks
- **Formatted Starters**: "Player Name (POS, NFL)" separated by semicolons
- **Bye Week Support**: Single-team matchups with empty Side B fields
- **Missing Data Handling**: Graceful handling of pre-game and missing data

## Configuration

### League ID Caching

The CLI automatically caches your league ID in `~/.sleeper_agent/config.json` for convenience. You can:
- Use cached league ID on startup
- Override with a new league ID anytime
- Validation ensures league access before proceeding

### Output Directory

All CSV exports are saved to the `out/` directory in your project folder. The directory is created automatically if it doesn't exist.

### Player Data Cache

Player information is cached locally in `~/.sleeper_agent/cache/players_2025.json`:
- Refreshed automatically if older than 7 days
- Contains all NFL player data with positions and teams
- Improves performance for repeated exports

## Development

### Project Structure

```
sleeper_agent/
├── __init__.py
├── __main__.py
├── cli.py              # Main CLI application
├── config.py           # Configuration management
├── models/             # Pydantic data models
│   ├── draft.py
│   ├── league.py
│   ├── matchup.py     # New matchup model
│   ├── player.py
│   ├── roster.py
│   └── user.py
├── services/           # Business logic services
│   ├── api.py         # Sleeper API client
│   ├── drafts.py      # Draft analysis
│   ├── leagues.py     # League data management
│   ├── matchups.py    # New matchups service
│   └── players.py     # Player data cache
├── io/                 # Input/output utilities
│   ├── csv_export.py  # CSV export functionality
│   └── files.py       # File management
└── tests/             # Comprehensive test suite
    ├── test_cli.py
    ├── test_matchups.py  # New matchups tests
    └── test_models.py
```

### Dependencies

- **httpx**: Async HTTP client for Sleeper API
- **pandas**: Data manipulation and CSV export
- **typer**: Command-line interface framework  
- **pydantic**: Data validation and serialization
- **rich**: Beautiful terminal output
- **tenacity**: Retry logic for API calls

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test module
python -m pytest sleeper_agent/tests/test_matchups.py

# Run with verbose output
python -m pytest -v
```

### Code Style

This project follows:
- **PEP 8**: Python style guide
- **Type hints**: Full type annotation coverage
- **Docstrings**: Comprehensive function documentation
- **Small focused modules**: Single responsibility principle
- **Error handling**: Graceful failure with user-friendly messages

## API Integration

Uses the official [Sleeper API](https://docs.sleeper.com/) endpoints:

- `GET /v1/league/{league_id}` - League information
- `GET /v1/league/{league_id}/users` - League members  
- `GET /v1/league/{league_id}/rosters` - Team rosters
- `GET /v1/league/{league_id}/drafts` - Draft information
- `GET /v1/draft/{draft_id}/picks` - Draft picks
- `GET /v1/league/{league_id}/matchups/{week}` - Weekly matchups ⭐ *New*
- `GET /v1/players/nfl` - NFL player database

### Rate Limiting & Reliability

- **Automatic retries** with exponential backoff
- **Request timeout** handling (30 seconds)
- **Connection pooling** for performance
- **Error recovery** with user-friendly messages

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`python -m pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built for the Sleeper Fantasy Football platform
- Uses the official Sleeper API
- Inspired by the need for better fantasy football analysis tools

## Support

For questions, issues, or feature requests:
- Open an [issue on GitHub](https://github.com/alex-l-clark/fantasy-football-storyline-agent/issues)
- Check the [Sleeper API documentation](https://docs.sleeper.com/) for API-related questions

---

**Happy analyzing! 🏈📊**
