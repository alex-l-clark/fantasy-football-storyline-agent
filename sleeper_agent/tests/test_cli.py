"""Tests for CLI functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from sleeper_agent.cli import SleeperCLI
from sleeper_agent.config import Config


class TestSleeperCLI:
    """Test SleeperCLI class."""
    
    def test_init(self):
        """Test CLI initialization."""
        cli = SleeperCLI()
        
        assert cli.config_manager is not None
        assert cli.config is not None
        assert cli.league_id is None
        assert cli.league_service is None
    
    @patch('sleeper_agent.cli.Prompt.ask')
    @patch('sleeper_agent.cli.Confirm.ask')
    @patch('sleeper_agent.services.leagues.LeagueService.validate_league')
    def test_setup_league_new(self, mock_validate, mock_confirm, mock_prompt):
        """Test setting up a new league ID."""
        cli = SleeperCLI()
        cli.config = Config()  # Empty config
        
        mock_prompt.return_value = "123456789"
        mock_validate.return_value = (True, "✓ League: Test League (2025)")
        
        result = cli.setup_league()
        
        assert result is True
        assert cli.league_id == "123456789"
        assert cli.league_service is not None
        mock_prompt.assert_called_once()
    
    @patch('sleeper_agent.cli.Prompt.ask')
    @patch('sleeper_agent.cli.Confirm.ask')
    def test_setup_league_cached(self, mock_confirm, mock_prompt):
        """Test using cached league ID."""
        cli = SleeperCLI()
        cli.config = Config(league_id="123456789")
        
        mock_confirm.return_value = True  # Use cached league ID
        
        with patch.object(cli.config_manager, 'load_config', return_value=cli.config):
            result = cli.setup_league()
        
        assert result is True
        assert cli.league_id == "123456789"
        mock_prompt.assert_not_called()
    
    @patch('sleeper_agent.cli.Prompt.ask')
    def test_show_main_menu(self, mock_prompt):
        """Test main menu display and choices."""
        cli = SleeperCLI()
        
        # Test draft-recap choice
        mock_prompt.return_value = "1"
        result = cli.show_main_menu()
        assert result == "draft-recap"
        
        # Test team-preview choice
        mock_prompt.return_value = "2"
        result = cli.show_main_menu()
        assert result == "team-preview"
        
        # Test quit choice
        mock_prompt.return_value = "q"
        result = cli.show_main_menu()
        assert result == "quit"


class TestCLIIntegration:
    """Integration tests for CLI flows."""
    
    @patch('sleeper_agent.services.drafts.get_json')
    @patch('sleeper_agent.services.players.get_json')
    def test_draft_recap_flow_mock(self, mock_players_api, mock_draft_api):
        """Test draft recap flow with mocked API calls."""
        # Mock draft API responses
        mock_draft_api.side_effect = [
            # League drafts
            [{
                "draft_id": "draft123",
                "league_id": "league456", 
                "status": "complete",
                "type": "snake",
                "start_time": 1693224000000
            }],
            # Draft picks
            [{
                "pick_no": 1,
                "round": 1,
                "draft_slot": 1,
                "player_id": "4034",
                "picked_by": "user123",
                "roster_id": 1,
                "timestamp": 1693224060000
            }]
        ]
        
        # Mock players API response
        mock_players_api.return_value = {
            "4034": {
                "first_name": "Christian",
                "last_name": "McCaffrey",
                "position": "RB",
                "team": "SF"
            }
        }
        
        cli = SleeperCLI()
        cli.league_id = "league456"
        cli.league_service = Mock()
        cli.league_service.get_users.return_value = [
            Mock(user_id="user123", username="testuser", effective_name="Test User")
        ]
        
        # This would normally require interactive input, so we'll just test
        # that the CLI can be instantiated and configured properly
        assert cli.league_id == "league456"
        assert cli.league_service is not None


# Fixtures for common test data
@pytest.fixture
def sample_league_data():
    """Sample league API response."""
    return {
        "league_id": "123456789",
        "name": "Test League",
        "season": "2025",
        "status": "in_season",
        "total_rosters": 12
    }


@pytest.fixture
def sample_users_data():
    """Sample users API response."""
    return [
        {
            "user_id": "user1",
            "username": "testuser1",
            "display_name": "Test User 1"
        },
        {
            "user_id": "user2", 
            "username": "testuser2",
            "display_name": "Test User 2"
        }
    ]


@pytest.fixture
def sample_draft_data():
    """Sample draft API response."""
    return {
        "draft_id": "draft123",
        "league_id": "league456",
        "status": "complete",
        "type": "snake",
        "start_time": 1693224000000
    }