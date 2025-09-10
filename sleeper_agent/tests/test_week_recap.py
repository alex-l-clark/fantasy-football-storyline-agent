"""Tests for week recap functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from sleeper_agent.models.matchup import Matchup
from sleeper_agent.services.week_recap import WeekRecapService
from sleeper_agent.io.csv_export import CSVExporter


class TestWeekRecapService:
    """Test WeekRecapService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = WeekRecapService("test_league")
    
    @patch('sleeper_agent.services.week_recap.get_json')
    def test_fetch_week_matchups(self, mock_get_json):
        """Test fetching week matchups."""
        mock_data = [
            {
                "roster_id": 1,
                "matchup_id": 1,
                "points": 125.6,
                "starters": ["4034", "421"],
                "starters_points": [24.5, 18.2]
            },
            {
                "roster_id": 2,
                "matchup_id": 1,
                "points": 118.4,
                "starters": ["5849", "6794"],
                "players_points": {"5849": 22.1, "6794": 16.8}
            }
        ]
        
        mock_get_json.return_value = mock_data
        
        matchups = self.service.fetch_week_matchups(1)
        
        assert len(matchups) == 2
        assert matchups[0].roster_id == 1
        assert matchups[1].roster_id == 2
        mock_get_json.assert_called_once_with("league/test_league/matchups/1")
    
    def test_fetch_week_matchups_invalid_week(self):
        """Test fetching with invalid week number."""
        with pytest.raises(ValueError, match="Week must be between 1 and 18"):
            self.service.fetch_week_matchups(0)
            
        with pytest.raises(ValueError, match="Week must be between 1 and 18"):
            self.service.fetch_week_matchups(19)
    
    def test_group_by_matchup_id(self):
        """Test grouping matchups by matchup_id."""
        matchups = [
            Matchup(roster_id=1, matchup_id=1, points=125.6),
            Matchup(roster_id=2, matchup_id=1, points=118.4),
            Matchup(roster_id=3, matchup_id=2, points=132.1),
            Matchup(roster_id=4, matchup_id=2, points=109.8),
            Matchup(roster_id=5, matchup_id=None, points=120.0),  # bye
        ]
        
        grouped = self.service.group_by_matchup_id(matchups)
        
        assert len(grouped) == 3  # 2 regular matchups + 1 bye
        assert len(grouped[1]) == 2  # matchup 1 has 2 teams
        assert len(grouped[2]) == 2  # matchup 2 has 2 teams
        assert len(grouped[-1]) == 1  # bye has 1 team
        assert grouped[-1][0].roster_id == 5
    
    def test_assign_sides(self):
        """Test side assignment by roster_id ordering."""
        # Regular matchup with two teams
        pair = [
            Matchup(roster_id=3, matchup_id=1),
            Matchup(roster_id=1, matchup_id=1)
        ]
        
        side_a, side_b = self.service.assign_sides(pair)
        
        assert side_a.roster_id == 1  # Lower roster_id = Side A
        assert side_b.roster_id == 3  # Higher roster_id = Side B
        
        # Bye week - single team
        bye_pair = [Matchup(roster_id=5, matchup_id=None)]
        side_a, side_b = self.service.assign_sides(bye_pair)
        
        assert side_a.roster_id == 5
        assert side_b is None
    
    def test_assign_sides_invalid_length(self):
        """Test assign_sides with invalid pair length."""
        with pytest.raises(ValueError, match="Invalid matchup pair length: 3"):
            self.service.assign_sides([Mock(), Mock(), Mock()])
    
    @patch('sleeper_agent.services.leagues.LeagueService.get_users')
    @patch('sleeper_agent.services.leagues.LeagueService.get_rosters')
    def test_resolve_users_and_rosters(self, mock_rosters, mock_users):
        """Test resolving user and roster mappings."""
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
        
        mock_users.return_value = [mock_user1, mock_user2]
        mock_rosters.return_value = [mock_roster1, mock_roster2]
        
        user_by_user_id, user_id_by_roster_id = self.service.resolve_users_and_rosters("test_league", 1)
        
        assert user_by_user_id["user1"]["username"] == "player1"
        assert user_by_user_id["user2"]["display_name"] == "Player Two"
        assert user_id_by_roster_id[1] == "user1"
        assert user_id_by_roster_id[2] == "user2"
    
    def test_extract_starters(self):
        """Test extracting starter player IDs."""
        matchup = Matchup(
            roster_id=1,
            starters=["4034", "421", None, "", "5849"]
        )
        
        starters = self.service.extract_starters(matchup)
        assert starters == ["4034", "421", "5849"]
    
    def test_extract_player_points_starters_points(self):
        """Test extracting player points from starters_points array."""
        matchup = Matchup(
            roster_id=1,
            starters=["4034", "421", "5849"],
            starters_points=[24.5, 18.2, 15.3],
            players_points={"4034": 20.0}  # Should prefer starters_points
        )
        
        player_points = self.service.extract_player_points(matchup)
        
        assert player_points["4034"] == 24.5
        assert player_points["421"] == 18.2
        assert player_points["5849"] == 15.3
    
    def test_extract_player_points_players_points_fallback(self):
        """Test extracting player points from players_points dict."""
        matchup = Matchup(
            roster_id=1,
            starters=["4034", "421", "5849"],
            starters_points=None,
            players_points={"4034": 24.5, "421": 18.2, "9999": 10.0}  # 9999 not a starter
        )
        
        player_points = self.service.extract_player_points(matchup)
        
        assert player_points["4034"] == 24.5
        assert player_points["421"] == 18.2
        assert "5849" not in player_points  # Not in players_points
        assert "9999" not in player_points   # Not a starter
    
    def test_extract_player_points_no_data(self):
        """Test extracting player points when no data is available."""
        matchup = Matchup(
            roster_id=1,
            starters=["4034", "421"],
            starters_points=None,
            players_points=None
        )
        
        player_points = self.service.extract_player_points(matchup)
        
        assert player_points == {}
    
    @patch('sleeper_agent.services.week_recap.players_cache')
    def test_build_player_row(self, mock_cache):
        """Test building a single player row."""
        mock_player = Mock()
        mock_player.full_name = "Christian McCaffrey"
        mock_player.display_position = "RB"
        mock_player.display_team = "SF"
        
        mock_cache.ensure_loaded.return_value = None
        mock_cache.lookup_player.return_value = mock_player
        
        side_user = {
            'username': 'testuser',
            'display_name': 'Test User',
            'team_name': 'Test Team'
        }
        
        row = self.service._build_player_row(
            league_id="test_league",
            week=1,
            matchup_id=1,
            winner_roster_id="2",
            is_tie=False,
            side="A",
            side_roster_id=1,
            side_user_id="user1",
            side_user=side_user,
            side_total_points=125.6,
            opp_roster_id="2",
            opp_username="opp_user",
            opp_total_points=118.4,
            player_id="4034",
            player_points=24.5,
            player_status="starter"
        )
        
        assert row["league_id"] == "test_league"
        assert row["week"] == 1
        assert row["matchup_id"] == 1
        assert row["winner_roster_id"] == "2"
        assert row["is_tie"] is False
        assert row["side"] == "A"
        assert row["side_roster_id"] == 1
        assert row["side_username"] == "testuser"
        assert row["player_name"] == "Christian McCaffrey"
        assert row["position"] == "RB"
        assert row["nfl_team"] == "SF"
        assert row["player_points"] == 24.5
        assert row["player_status"] == "starter"
    
    @patch('sleeper_agent.services.week_recap.players_cache')
    def test_build_player_row_unknown_player(self, mock_cache):
        """Test building a player row for unknown player."""
        mock_cache.ensure_loaded.return_value = None
        mock_cache.lookup_player.return_value = None
        
        side_user = {'username': 'testuser', 'display_name': 'Test User', 'team_name': ''}
        
        row = self.service._build_player_row(
            league_id="test_league",
            week=1,
            matchup_id=1,
            winner_roster_id="",
            is_tie=True,
            side="B",
            side_roster_id=2,
            side_user_id="user2",
            side_user=side_user,
            side_total_points=118.4,
            opp_roster_id="1",
            opp_username="opp_user",
            opp_total_points=118.4,  # Tie
            player_id="unknown123",
            player_points="",
            player_status="bench"
        )
        
        assert row["player_name"] == "Unknown unknown123"
        assert row["position"] == ""
        assert row["nfl_team"] == ""
        assert row["is_tie"] is True
        assert row["winner_roster_id"] == ""
        assert row["player_points"] == ""
        assert row["player_status"] == "bench"
    
    def test_determine_week_specific_player_status(self):
        """Test determining week-specific player status from matchup data."""
        # Create a matchup with specific starters
        matchup = Matchup(
            roster_id=1,
            matchup_id=1,
            starters=["4034", "421"],  # These were the actual starters that week
            players_points={"4034": 24.5, "421": 18.2, "5849": 12.0}  # 5849 was on roster but not starting
        )
        
        # Create a historical roster
        from sleeper_agent.models.roster import Roster
        historical_roster = Roster(
            roster_id=1, 
            owner_id="user1", 
            league_id="test",
            players=["4034", "421", "5849"],  # All players that were on roster that week
            starters=["4034", "421"]  # Current starters (irrelevant for week-specific analysis)
        )
        
        # Test starter
        status = self.service.determine_week_specific_player_status("4034", matchup)
        assert status == "starter"
        
        # Test bench player
        status = self.service.determine_week_specific_player_status("5849", matchup)
        assert status == "bench"
        
        # Test player not on roster that week
        status = self.service.determine_week_specific_player_status("9999", matchup)
        assert status is None
    
    def test_build_rows_for_matchup_regular(self):
        """Test building rows for a regular head-to-head matchup."""
        side_a = Matchup(
            roster_id=1,
            matchup_id=1,
            points=125.6,
            starters=["4034", "421"],
            starters_points=[24.5, 18.2],
            players_points={"4034": 24.5, "421": 18.2, "bench1": 8.0}  # All players on roster that week
        )
        
        side_b = Matchup(
            roster_id=2,
            matchup_id=1,
            points=118.4,
            starters=["5849"],
            starters_points=[22.1],
            players_points={"5849": 22.1, "bench2": 5.5}  # All players on roster that week
        )
        
        user_by_user_id = {
            "user1": {"username": "player1", "display_name": "Player One", "team_name": "Team A"},
            "user2": {"username": "player2", "display_name": "Player Two", "team_name": "Team B"}
        }
        
        user_id_by_roster_id = {1: "user1", 2: "user2"}
        
        with patch.object(self.service, '_build_player_row') as mock_build_row:
            mock_build_row.return_value = {"test": "row"}
            
            rows = self.service.build_rows_for_matchup(
                matchup_id=1,
                week=1,
                side_a=side_a,
                side_b=side_b,
                user_by_user_id=user_by_user_id,
                user_id_by_roster_id=user_id_by_roster_id
            )
            
            # Should have 5 rows: 3 from side A (2 starters + 1 bench) + 2 from side B (1 starter + 1 bench)
            assert len(rows) == 5
            assert mock_build_row.call_count == 5
    
    def test_build_rows_for_matchup_bye(self):
        """Test building rows for a bye week matchup."""
        side_a = Matchup(
            roster_id=1,
            matchup_id=None,
            points=125.6,
            starters=["4034"],
            starters_points=[24.5],
            players_points={"4034": 24.5, "bench1": 8.0}  # All players on roster that week
        )
        
        user_by_user_id = {
            "user1": {"username": "player1", "display_name": "Player One", "team_name": "Team A"}
        }
        
        user_id_by_roster_id = {1: "user1"}
        
        with patch.object(self.service, '_build_player_row') as mock_build_row:
            mock_build_row.return_value = {"test": "row"}
            
            rows = self.service.build_rows_for_matchup(
                matchup_id=-1,
                week=1,
                side_a=side_a,
                side_b=None,
                user_by_user_id=user_by_user_id,
                user_id_by_roster_id=user_id_by_roster_id
            )
            
            # Should have 2 rows from side A only (1 starter + 1 bench)
            assert len(rows) == 2
            assert mock_build_row.call_count == 2
    
    @patch('sleeper_agent.services.week_recap.WeekRecapService.fetch_week_matchups')
    @patch('sleeper_agent.services.week_recap.WeekRecapService.group_by_matchup_id')  
    @patch('sleeper_agent.services.week_recap.WeekRecapService.resolve_users_and_rosters')
    @patch('sleeper_agent.services.week_recap.WeekRecapService.assign_sides')
    @patch('sleeper_agent.services.week_recap.WeekRecapService.build_rows_for_matchup')
    def test_build_week_recap_dataframe(self, mock_build_rows, mock_assign, 
                                       mock_resolve, mock_group, mock_fetch):
        """Test building complete week recap dataframe."""
        # Mock the chain of method calls
        mock_matchups = [Mock(), Mock()]
        mock_grouped = {1: [Mock(), Mock()]}
        mock_users = {"user1": {"username": "player1"}}
        mock_rosters = {1: "user1"}
        mock_rows = [
            {
                "league_id": "test_league", "week": 1, "matchup_id": 1, "winner_roster_id": 1,
                "is_tie": False, "side": "A", "side_roster_id": 1, "side_user_id": "user1",
                "side_username": "player1", "side_display_name": "Player One", "side_team_name": "Team A",
                "side_total_points": 125.6, "opp_roster_id": 2, "opp_username": "player2",
                "opp_total_points": 118.4, "player_id": "4034", "player_name": "Player 1",
                "position": "RB", "nfl_team": "SF", "player_points": 24.5, "player_status": "starter"
            },
            {
                "league_id": "test_league", "week": 1, "matchup_id": 1, "winner_roster_id": 1,
                "is_tie": False, "side": "B", "side_roster_id": 2, "side_user_id": "user2",
                "side_username": "player2", "side_display_name": "Player Two", "side_team_name": "Team B",
                "side_total_points": 118.4, "opp_roster_id": 1, "opp_username": "player1",
                "opp_total_points": 125.6, "player_id": "5849", "player_name": "Player 2",
                "position": "WR", "nfl_team": "MIA", "player_points": 22.1, "player_status": "starter"
            }
        ]
        
        mock_fetch.return_value = mock_matchups
        mock_group.return_value = mock_grouped
        mock_resolve.return_value = (mock_users, mock_rosters)
        mock_assign.return_value = (Mock(), Mock())
        mock_build_rows.return_value = mock_rows
        
        df = self.service.build_week_recap_dataframe(1)
        
        assert len(df) == 2
        assert list(df.columns) == [
            "league_id", "week", "matchup_id", "winner_roster_id", "is_tie",
            "side", "side_roster_id", "side_user_id", "side_username", 
            "side_display_name", "side_team_name", "side_total_points",
            "opp_roster_id", "opp_username", "opp_total_points",
            "player_id", "player_name", "position", "nfl_team", "player_points", "player_status"
        ]
        
        mock_fetch.assert_called_once_with(1)
        mock_group.assert_called_once_with(mock_matchups)
        mock_resolve.assert_called_once()
    
    def test_build_week_recap_dataframe_no_matchups(self):
        """Test building dataframe when no matchups found."""
        with patch.object(self.service, 'fetch_week_matchups') as mock_fetch:
            mock_fetch.return_value = []
            
            df = self.service.build_week_recap_dataframe(1)
            
            assert df.empty


class TestCSVExporter:
    """Test CSV export functionality for week recap."""
    
    @patch('sleeper_agent.io.csv_export.file_manager')
    def test_export_week_recap(self, mock_file_manager):
        """Test exporting week recap DataFrame to CSV."""
        # Create test DataFrame
        df = pd.DataFrame([{
            "league_id": "123456",
            "week": 1,
            "matchup_id": 1,
            "winner_roster_id": 1,
            "is_tie": False,
            "side": "A",
            "side_roster_id": 1,
            "side_user_id": "user1",
            "side_username": "player1",
            "side_display_name": "Player One",
            "side_team_name": "Team Alpha",
            "side_total_points": 125.6,
            "opp_roster_id": 2,
            "opp_username": "player2",
            "opp_total_points": 118.4,
            "player_id": "4034",
            "player_name": "Christian McCaffrey",
            "position": "RB",
            "nfl_team": "SF",
            "player_points": 24.5,
            "player_status": "starter"
        }])
        
        mock_path = Mock()
        mock_file_manager.week_recap_filename.return_value = "week_recap_123456_week1.csv"
        mock_file_manager.get_output_path.return_value = mock_path
        
        with patch('pandas.DataFrame.to_csv') as mock_to_csv:
            result_path = CSVExporter.export_week_recap(df, "123456", 1)
            
            assert result_path == mock_path
            mock_file_manager.week_recap_filename.assert_called_once_with("123456", 1)
            mock_file_manager.get_output_path.assert_called_once_with("week_recap_123456_week1.csv")
            mock_file_manager.ensure_output_dir.assert_called_once()
            mock_to_csv.assert_called_once_with(mock_path, index=False, encoding='utf-8')
    
    def test_export_week_recap_empty_dataframe(self):
        """Test exporting empty DataFrame raises ValueError."""
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError, match="No week recap data to export"):
            CSVExporter.export_week_recap(empty_df, "123456", 1)


# Fixtures for common test data
@pytest.fixture
def sample_week_recap_data():
    """Sample week recap data."""
    return [
        {
            "league_id": "123456",
            "week": 1,
            "matchup_id": 1,
            "winner_roster_id": 1,
            "is_tie": False,
            "side": "A",
            "side_roster_id": 1,
            "side_user_id": "user1",
            "side_username": "player1",
            "side_display_name": "Player One",
            "side_team_name": "Team Alpha",
            "side_total_points": 125.6,
            "opp_roster_id": 2,
            "opp_username": "player2",
            "opp_total_points": 118.4,
            "player_id": "4034",
            "player_name": "Christian McCaffrey",
            "position": "RB",
            "nfl_team": "SF",
            "player_points": 24.5,
            "player_status": "starter"
        }
    ]


@pytest.fixture
def sample_matchup_with_points():
    """Sample matchup with player points data."""
    return {
        "roster_id": 1,
        "matchup_id": 1,
        "points": 125.6,
        "starters": ["4034", "421", "5849"],
        "starters_points": [24.5, 18.2, 15.3],
        "players_points": {"4034": 24.5, "421": 18.2, "5849": 15.3, "bench_player": 10.0}
    }


@pytest.fixture
def sample_bye_matchup():
    """Sample bye week matchup data."""
    return {
        "roster_id": 3,
        "matchup_id": None,
        "points": 132.1,
        "starters": ["4034", "6794"],
        "starters_points": [28.5, 19.3]
    }