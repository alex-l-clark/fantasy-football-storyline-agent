"""Tests for matchups functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from sleeper_agent.models.matchup import Matchup
from sleeper_agent.services.matchups import MatchupsService
from sleeper_agent.io.csv_export import CSVExporter


class TestMatchupModel:
    """Test Matchup model."""
    
    def test_from_api_response(self):
        """Test creating Matchup from API response."""
        data = {
            "roster_id": 1,
            "matchup_id": 5,
            "points": 125.6,
            "players_points": {"4034": 24.5},
            "starters": ["4034", "421", None],
            "starters_points": [24.5, 18.2, None],
            "custom_points": 128.0
        }
        
        matchup = Matchup.from_api_response(data)
        
        assert matchup.roster_id == 1
        assert matchup.matchup_id == 5
        assert matchup.points == 125.6
        assert matchup.custom_points == 128.0
        assert matchup.starters == ["4034", "421", None]
    
    def test_bye_week(self):
        """Test bye week detection."""
        bye_data = {
            "roster_id": 1,
            "matchup_id": None,
            "points": 125.6
        }
        
        regular_data = {
            "roster_id": 2,
            "matchup_id": 5,
            "points": 130.2
        }
        
        bye_matchup = Matchup.from_api_response(bye_data)
        regular_matchup = Matchup.from_api_response(regular_data)
        
        assert bye_matchup.has_bye is True
        assert regular_matchup.has_bye is False
    
    def test_points_properties(self):
        """Test projected and actual points properties."""
        data = {
            "roster_id": 1,
            "matchup_id": 5,
            "points": 125.6,
            "custom_points": 128.0
        }
        
        matchup = Matchup.from_api_response(data)
        
        assert matchup.projected_points == 128.0
        assert matchup.actual_points == 125.6
    
    def test_get_starters_list(self):
        """Test getting cleaned starters list."""
        data = {
            "roster_id": 1,
            "starters": ["4034", "421", None, "", "5849"],
        }
        
        matchup = Matchup.from_api_response(data)
        starters = matchup.get_starters_list()
        
        assert starters == ["4034", "421", "5849"]


class TestMatchupsService:
    """Test MatchupsService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = MatchupsService("test_league")
        
    @patch('sleeper_agent.services.matchups.get_json')
    def test_fetch_week_matchups(self, mock_get_json):
        """Test fetching week matchups."""
        mock_data = [
            {
                "roster_id": 1,
                "matchup_id": 1,
                "points": 125.6,
                "starters": ["4034", "421"]
            },
            {
                "roster_id": 2,
                "matchup_id": 1,
                "points": 118.4,
                "starters": ["5849", "6794"]
            }
        ]
        
        mock_get_json.return_value = mock_data
        
        matchups = self.service.fetch_week_matchups(1)
        
        assert len(matchups) == 2
        assert matchups[0].roster_id == 1
        assert matchups[1].roster_id == 2
        assert matchups[0].matchup_id == 1
        mock_get_json.assert_called_once_with("league/test_league/matchups/1")
    
    def test_fetch_week_matchups_invalid_week(self):
        """Test fetching with invalid week number."""
        with pytest.raises(ValueError, match="Week must be between 1 and 18"):
            self.service.fetch_week_matchups(0)
            
        with pytest.raises(ValueError, match="Week must be between 1 and 18"):
            self.service.fetch_week_matchups(19)
    
    def test_group_matchups_by_id(self):
        """Test grouping matchups by matchup_id."""
        matchups = [
            Matchup(roster_id=1, matchup_id=1, points=125.6),
            Matchup(roster_id=2, matchup_id=1, points=118.4),
            Matchup(roster_id=3, matchup_id=2, points=132.1),
            Matchup(roster_id=4, matchup_id=2, points=109.8),
            Matchup(roster_id=5, matchup_id=None, points=120.0),  # bye
        ]
        
        grouped = self.service.group_matchups_by_id(matchups)
        
        assert len(grouped) == 3  # 2 regular matchups + 1 bye
        assert len(grouped[1]) == 2  # matchup 1 has 2 teams
        assert len(grouped[2]) == 2  # matchup 2 has 2 teams
        assert len(grouped[-1]) == 1  # bye has 1 team
        assert grouped[-1][0].roster_id == 5
    
    @patch('sleeper_agent.services.matchups.MatchupsService.fetch_week_matchups')
    @patch('sleeper_agent.services.leagues.LeagueService.get_rosters')
    def test_compute_records_through_week_1(self, mock_rosters, mock_fetch):
        """Test computing records for week 1 (should be all 0-0)."""
        mock_rosters.return_value = [
            Mock(roster_id=1),
            Mock(roster_id=2),
            Mock(roster_id=3)
        ]
        
        records = self.service.compute_records_through_week(1)
        
        assert records[1] == (0, 0, 0)
        assert records[2] == (0, 0, 0)
        assert records[3] == (0, 0, 0)
        mock_fetch.assert_not_called()
    
    @patch('sleeper_agent.services.matchups.MatchupsService.fetch_week_matchups')
    @patch('sleeper_agent.services.matchups.MatchupsService.group_matchups_by_id')
    @patch('sleeper_agent.services.leagues.LeagueService.get_rosters')
    def test_compute_records_through_week_3(self, mock_rosters, mock_group, mock_fetch):
        """Test computing records through week 3."""
        mock_rosters.return_value = [
            Mock(roster_id=1),
            Mock(roster_id=2),
            Mock(roster_id=3),
            Mock(roster_id=4)
        ]
        
        # Mock week 1 data
        week1_matchups = [
            Mock(roster_id=1, actual_points=125.6),
            Mock(roster_id=2, actual_points=118.4),
            Mock(roster_id=3, actual_points=132.1),
            Mock(roster_id=4, actual_points=109.8)
        ]
        
        # Mock week 2 data  
        week2_matchups = [
            Mock(roster_id=1, actual_points=115.2),
            Mock(roster_id=3, actual_points=115.2),  # tie
            Mock(roster_id=2, actual_points=128.7),
            Mock(roster_id=4, actual_points=105.3)
        ]
        
        def fetch_side_effect(week):
            if week == 1:
                return week1_matchups
            elif week == 2:
                return week2_matchups
            else:
                return []
                
        def group_side_effect(matchups):
            if matchups == week1_matchups:
                return {
                    1: [matchups[0], matchups[1]],  # 1 vs 2 (1 wins)
                    2: [matchups[2], matchups[3]]   # 3 vs 4 (3 wins)
                }
            elif matchups == week2_matchups:
                return {
                    1: [matchups[0], matchups[1]],  # 1 vs 3 (tie)
                    2: [matchups[2], matchups[3]]   # 2 vs 4 (2 wins)
                }
            else:
                return {}
        
        mock_fetch.side_effect = fetch_side_effect
        mock_group.side_effect = group_side_effect
        
        records = self.service.compute_records_through_week(3)
        
        # Expected records after 2 weeks:
        # Roster 1: 1 win (beat 2), 1 tie (with 3) = 1-0-1
        # Roster 2: 1 loss (to 1), 1 win (beat 4) = 1-1-0  
        # Roster 3: 1 win (beat 4), 1 tie (with 1) = 1-0-1
        # Roster 4: 1 loss (to 3), 1 loss (to 2) = 0-2-0
        
        assert records[1] == (1, 0, 1)  # 1-0-1
        assert records[2] == (1, 1, 0)  # 1-1-0
        assert records[3] == (1, 0, 1)  # 1-0-1
        assert records[4] == (0, 2, 0)  # 0-2-0
    
    def test_format_record(self):
        """Test formatting W-L-T records."""
        assert self.service.format_record((3, 1, 0)) == "3-1"
        assert self.service.format_record((2, 2, 1)) == "2-2-1"
        assert self.service.format_record((0, 0, 0)) == "0-0"
    
    @patch('sleeper_agent.services.matchups.players_cache')
    def test_hydrate_starters(self, mock_cache):
        """Test hydrating starter player IDs to names."""
        mock_player1 = Mock()
        mock_player1.full_name = "Christian McCaffrey"
        mock_player1.display_position = "RB"
        mock_player1.display_team = "SF"
        
        mock_player2 = Mock()
        mock_player2.full_name = "Tyreek Hill"
        mock_player2.display_position = "WR"
        mock_player2.display_team = "MIA"
        
        def lookup_side_effect(player_id):
            if player_id == "4034":
                return mock_player1
            elif player_id == "6794":
                return mock_player2
            else:
                return None
        
        # Mock both ensure_loaded and lookup_player
        mock_cache.ensure_loaded.return_value = None        
        mock_cache.lookup_player.side_effect = lookup_side_effect
        
        result = self.service.hydrate_starters(["4034", "6794", "999999", ""])
        
        expected = "Christian McCaffrey (RB, SF); Tyreek Hill (WR, MIA); Unknown Player (999999) (N/A, N/A)"
        assert result == expected
        
        # Test empty list
        assert self.service.hydrate_starters([]) == ""
    
    @patch('sleeper_agent.services.matchups.MatchupsService.fetch_week_matchups')
    @patch('sleeper_agent.services.matchups.MatchupsService.group_matchups_by_id')
    @patch('sleeper_agent.services.matchups.MatchupsService.compute_records_through_week')
    @patch('sleeper_agent.services.matchups.MatchupsService.hydrate_starters')
    @patch('sleeper_agent.services.leagues.LeagueService.get_users')
    @patch('sleeper_agent.services.leagues.LeagueService.get_rosters')
    def test_build_matchups_dataframe(self, mock_rosters, mock_users, mock_hydrate, 
                                     mock_records, mock_group, mock_fetch):
        """Test building complete matchups dataframe."""
        # Mock data setup
        mock_matchups = [
            Mock(roster_id=1, matchup_id=1, projected_points=120.0, actual_points=125.6, get_starters_list=Mock(return_value=["4034", "6794"])),
            Mock(roster_id=2, matchup_id=1, projected_points=115.0, actual_points=118.4, get_starters_list=Mock(return_value=["5849", "421"]))
        ]
        
        mock_grouped = {
            1: [mock_matchups[0], mock_matchups[1]]
        }
        
        mock_records_data = {
            1: (2, 1, 0),
            2: (1, 2, 0)
        }
        
        mock_user1 = Mock()
        mock_user1.user_id = "user1"
        mock_user1.username = "player1"
        mock_user1.display_name = "Player One"
        mock_user1.team_name = "Team Alpha"
        
        mock_user2 = Mock()
        mock_user2.user_id = "user2"
        mock_user2.username = "player2"
        mock_user2.display_name = "Player Two"
        mock_user2.team_name = "Team Beta"
        
        mock_roster1 = Mock()
        mock_roster1.roster_id = 1
        mock_roster1.owner_id = "user1"
        
        mock_roster2 = Mock()
        mock_roster2.roster_id = 2
        mock_roster2.owner_id = "user2"
        
        # Configure mocks
        mock_fetch.return_value = mock_matchups
        mock_group.return_value = mock_grouped
        mock_records.return_value = mock_records_data
        mock_users.return_value = [mock_user1, mock_user2]
        mock_rosters.return_value = [mock_roster1, mock_roster2]
        mock_hydrate.side_effect = ["CMC (RB, SF); Hill (WR, MIA)", "Kupp (WR, LAR); Adams (WR, LV)"]
        
        # Test
        df = self.service.build_matchups_dataframe(2)
        
        # Verify
        assert len(df) == 1
        assert df.iloc[0]['league_id'] == "test_league"
        assert df.iloc[0]['week'] == 2
        assert df.iloc[0]['matchup_id'] == 1
        assert df.iloc[0]['side_a_roster_id'] == 1  # lower roster_id = side A
        assert df.iloc[0]['side_a_username'] == "player1"
        assert df.iloc[0]['side_a_record_pre'] == "2-1"
        assert df.iloc[0]['side_b_roster_id'] == 2
        assert df.iloc[0]['side_b_username'] == "player2"
        assert df.iloc[0]['side_b_record_pre'] == "1-2"


class TestCSVExporter:
    """Test CSV export functionality for matchups."""
    
    @patch('sleeper_agent.io.csv_export.file_manager')
    def test_export_matchups(self, mock_file_manager):
        """Test exporting matchups DataFrame to CSV."""
        # Create test DataFrame
        df = pd.DataFrame([{
            "league_id": "123456",
            "week": 1,
            "matchup_id": 1,
            "side_a_roster_id": 1,
            "side_a_username": "player1",
            "side_a_display_name": "Player One",
            "side_a_team_name": "Team Alpha",
            "side_a_record_pre": "0-0",
            "side_a_projected_points": 120.0,
            "side_a_actual_points": 125.6,
            "side_a_starters": "CMC (RB, SF); Hill (WR, MIA)",
            "side_b_roster_id": 2,
            "side_b_username": "player2",
            "side_b_display_name": "Player Two",
            "side_b_team_name": "Team Beta", 
            "side_b_record_pre": "0-0",
            "side_b_projected_points": 115.0,
            "side_b_actual_points": 118.4,
            "side_b_starters": "Kupp (WR, LAR); Adams (WR, LV)"
        }])
        
        mock_path = Mock()
        mock_file_manager.matchups_filename.return_value = "matchups_123456_week1.csv"
        mock_file_manager.get_output_path.return_value = mock_path
        
        with patch('pandas.DataFrame.to_csv') as mock_to_csv:
            result_path = CSVExporter.export_matchups(df, "123456", 1)
            
            assert result_path == mock_path
            mock_file_manager.matchups_filename.assert_called_once_with("123456", 1)
            mock_file_manager.get_output_path.assert_called_once_with("matchups_123456_week1.csv")
            mock_file_manager.ensure_output_dir.assert_called_once()
            mock_to_csv.assert_called_once_with(mock_path, index=False, encoding='utf-8')
    
    def test_export_matchups_empty_dataframe(self):
        """Test exporting empty DataFrame raises ValueError."""
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError, match="No matchup data to export"):
            CSVExporter.export_matchups(empty_df, "123456", 1)


# Fixtures for common test data
@pytest.fixture
def sample_matchup_data():
    """Sample matchup API response."""
    return [
        {
            "roster_id": 1,
            "matchup_id": 1,
            "points": 125.6,
            "players_points": {"4034": 24.5, "6794": 18.2},
            "starters": ["4034", "6794", "421"],
            "starters_points": [24.5, 18.2, 15.3],
            "custom_points": 128.0
        },
        {
            "roster_id": 2,
            "matchup_id": 1,
            "points": 118.4,
            "players_points": {"5849": 22.1, "8167": 16.8},
            "starters": ["5849", "8167", "9134"],
            "starters_points": [22.1, 16.8, 12.4],
            "custom_points": 121.5
        }
    ]


@pytest.fixture 
def sample_bye_data():
    """Sample bye week matchup data."""
    return [
        {
            "roster_id": 3,
            "matchup_id": None,
            "points": 132.1,
            "starters": ["4034", "6794"],
            "starters_points": [28.5, 19.3]
        }
    ]