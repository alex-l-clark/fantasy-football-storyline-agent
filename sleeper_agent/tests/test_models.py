"""Tests for data models."""

import pytest
from datetime import datetime

from sleeper_agent.models.league import League
from sleeper_agent.models.user import User
from sleeper_agent.models.roster import Roster
from sleeper_agent.models.draft import Draft, DraftPick
from sleeper_agent.models.player import Player


class TestLeague:
    """Test League model."""
    
    def test_from_api_response(self):
        """Test League creation from API response."""
        data = {
            "league_id": "123456789",
            "name": "Test League",
            "season": "2025",
            "status": "in_season",
            "total_rosters": 12
        }
        
        league = League.from_api_response(data)
        
        assert league.league_id == "123456789"
        assert league.name == "Test League"
        assert league.season == "2025"
        assert league.status == "in_season"
        assert league.total_rosters == 12


class TestUser:
    """Test User model."""
    
    def test_from_api_response(self):
        """Test User creation from API response."""
        data = {
            "user_id": "987654321",
            "username": "testuser",
            "display_name": "Test User",
            "team_name": "Test Team"
        }
        
        user = User.from_api_response(data)
        
        assert user.user_id == "987654321"
        assert user.username == "testuser"
        assert user.display_name == "Test User"
        assert user.team_name == "Test Team"
    
    def test_effective_name(self):
        """Test effective_name property."""
        user = User(
            user_id="123",
            username="testuser",
            display_name="Test User",
            team_name="Test Team"
        )
        assert user.effective_name == "Test User"
        
        user.display_name = None
        assert user.effective_name == "Test Team"
        
        user.team_name = None
        assert user.effective_name == "testuser"


class TestRoster:
    """Test Roster model."""
    
    def test_from_api_response(self):
        """Test Roster creation from API response."""
        data = {
            "roster_id": 1,
            "owner_id": "123456789",
            "players": ["4034", "5859", "6786"],
            "starters": ["4034", "5859"],
            "reserve": ["6786"]
        }
        
        roster = Roster.from_api_response(data)
        
        assert roster.roster_id == 1
        assert roster.owner_id == "123456789"
        assert roster.players == ["4034", "5859", "6786"]
        assert roster.starters == ["4034", "5859"]
        assert roster.reserve == ["6786"]
    
    def test_get_player_status(self):
        """Test player status determination."""
        roster = Roster(
            roster_id=1,
            owner_id="123",
            league_id="456",
            players=["p1", "p2", "p3"],
            starters=["p1"],
            reserve=["p3"]
        )
        
        assert roster.get_player_status("p1") == "starter"
        assert roster.get_player_status("p2") == "bench"
        assert roster.get_player_status("p3") == "bench"
        assert roster.get_player_status("p4") == "active"


class TestDraft:
    """Test Draft model."""
    
    def test_from_api_response(self):
        """Test Draft creation from API response."""
        data = {
            "draft_id": "draft123",
            "league_id": "league456",
            "status": "complete",
            "type": "snake",
            "start_time": 1693224000000  # Unix timestamp in milliseconds
        }
        
        draft = Draft.from_api_response(data)
        
        assert draft.draft_id == "draft123"
        assert draft.league_id == "league456"
        assert draft.status == "complete"
        assert draft.type == "snake"
        assert draft.start_time == 1693224000000
    
    def test_start_datetime(self):
        """Test start_datetime property."""
        draft = Draft(
            draft_id="123",
            league_id="456",
            status="complete",
            type="snake",
            start_time=1693224000000
        )
        
        dt = draft.start_datetime
        assert isinstance(dt, datetime)
        assert dt.year == 2023


class TestDraftPick:
    """Test DraftPick model."""
    
    def test_from_api_response(self):
        """Test DraftPick creation from API response."""
        data = {
            "pick_no": 1,
            "round": 1,
            "draft_slot": 1,
            "player_id": "4034",
            "picked_by": "user123",
            "roster_id": 1,
            "timestamp": 1693224060000
        }
        
        pick = DraftPick.from_api_response(data)
        
        assert pick.pick_no == 1
        assert pick.round == 1
        assert pick.draft_slot == 1
        assert pick.player_id == "4034"
        assert pick.picked_by == "user123"
        assert pick.roster_id == 1
        assert pick.timestamp == 1693224060000
    
    def test_timestamp_utc(self):
        """Test timestamp_utc property."""
        pick = DraftPick(
            pick_no=1,
            round=1,
            draft_slot=1,
            player_id="4034",
            picked_by="user123",
            roster_id=1,
            timestamp=1693224060000
        )
        
        dt = pick.timestamp_utc
        assert isinstance(dt, datetime)


class TestPlayer:
    """Test Player model."""
    
    def test_from_api_response(self):
        """Test Player creation from API response."""
        data = {
            "first_name": "Christian",
            "last_name": "McCaffrey",
            "position": "RB",
            "team": "SF",
            "number": 23,
            "age": 27,
            "fantasy_positions": ["RB"]
        }
        
        player = Player.from_api_response("4034", data)
        
        assert player.player_id == "4034"
        assert player.first_name == "Christian"
        assert player.last_name == "McCaffrey"
        assert player.position == "RB"
        assert player.team == "SF"
        assert player.number == 23
        assert player.age == 27
        assert player.fantasy_positions == ["RB"]
    
    def test_full_name(self):
        """Test full_name property."""
        player = Player(
            player_id="123",
            first_name="Christian",
            last_name="McCaffrey"
        )
        assert player.full_name == "Christian McCaffrey"
        
        player.first_name = None
        assert player.full_name == "McCaffrey"
        
        player.last_name = None
        player.first_name = "Christian"
        assert player.full_name == "Christian"
        
        player.first_name = None
        assert player.full_name == "Unknown Player"
    
    def test_display_properties(self):
        """Test display properties."""
        player = Player(
            player_id="123",
            position="RB",
            team="SF"
        )
        
        assert player.display_position == "RB"
        assert player.display_team == "SF"
        
        player.position = None
        player.team = None
        
        assert player.display_position == "N/A"
        assert player.display_team == "N/A"