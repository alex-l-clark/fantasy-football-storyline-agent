"""Tests for historical roster functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from copy import deepcopy

from sleeper_agent.models.roster import Roster
from sleeper_agent.models.transaction import Transaction
from sleeper_agent.services.historical_rosters import HistoricalRosterService


class TestTransaction:
    """Test Transaction model."""
    
    def test_from_api_response(self):
        """Test creating Transaction from API response."""
        data = {
            "type": "waiver",
            "transaction_id": "123456",
            "status": "complete",
            "leg": 2,
            "roster_ids": [1, 2],
            "adds": {"4034": 1},
            "drops": {"421": 1}
        }
        
        transaction = Transaction.from_api_response(data)
        
        assert transaction.type == "waiver"
        assert transaction.transaction_id == "123456"
        assert transaction.week == 2
        assert transaction.is_completed
        assert transaction.affects_roster(1)
        assert not transaction.affects_roster(3)
    
    def test_get_player_changes_for_roster(self):
        """Test getting player changes for a specific roster."""
        transaction = Transaction(
            type="waiver",
            transaction_id="123",
            status="complete",
            leg=2,
            roster_ids=[1],
            adds={"4034": 1},
            drops={"421": 1}
        )
        
        changes = transaction.get_player_changes_for_roster(1)
        
        assert "4034" in changes["added"]
        assert "421" in changes["dropped"]
        
        # Different roster should have no changes
        changes_other = transaction.get_player_changes_for_roster(2)
        assert len(changes_other["added"]) == 0
        assert len(changes_other["dropped"]) == 0


class TestHistoricalRosterService:
    """Test HistoricalRosterService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = HistoricalRosterService("test_league")
    
    @patch('sleeper_agent.services.historical_rosters.get_json')
    def test_fetch_transactions_for_week(self, mock_get_json):
        """Test fetching transactions for a specific week."""
        mock_data = [
            {
                "type": "waiver",
                "transaction_id": "123456",
                "status": "complete",
                "leg": 2,
                "roster_ids": [1],
                "adds": {"4034": 1},
                "drops": {"421": 1}
            },
            {
                "type": "free_agent",
                "transaction_id": "123457",
                "status": "complete",
                "leg": 2,
                "roster_ids": [2],
                "adds": {"5849": 2}
            }
        ]
        
        mock_get_json.return_value = mock_data
        
        transactions = self.service.fetch_transactions_for_week(2)
        
        assert len(transactions) == 2
        assert transactions[0].type == "waiver"
        assert transactions[1].type == "free_agent"
        mock_get_json.assert_called_once_with("league/test_league/transactions/2")
    
    @patch('sleeper_agent.services.historical_rosters.get_json')
    def test_fetch_transactions_for_week_no_data(self, mock_get_json):
        """Test fetching transactions when no data exists."""
        mock_get_json.return_value = []
        
        transactions = self.service.fetch_transactions_for_week(1)
        
        assert len(transactions) == 0
    
    def test_get_current_week(self):
        """Test getting current week."""
        with patch.object(self.service.league_service, 'get_league') as mock_get_league:
            mock_league = Mock()
            mock_get_league.return_value = mock_league
            
            current_week = self.service.get_current_week()
            
            assert current_week == 18  # Default implementation
    
    @patch('sleeper_agent.services.historical_rosters.HistoricalRosterService.get_current_week')
    def test_get_roster_for_week_current_week(self, mock_current_week):
        """Test getting roster for current week returns current roster."""
        mock_current_week.return_value = 5
        
        mock_roster = Mock()
        mock_roster.roster_id = 1
        
        with patch.object(self.service.league_service, 'get_rosters') as mock_get_rosters:
            mock_get_rosters.return_value = [mock_roster]
            
            result = self.service.get_roster_for_week(1, 5)
            
            assert result == mock_roster
    
    @patch('sleeper_agent.services.historical_rosters.HistoricalRosterService.get_current_week')
    @patch('sleeper_agent.services.historical_rosters.HistoricalRosterService.fetch_transactions_for_week')
    def test_reconstruct_roster_for_week(self, mock_fetch_transactions, mock_current_week):
        """Test reconstructing roster for a historical week."""
        mock_current_week.return_value = 3
        
        # Mock current roster
        current_roster = Roster(
            roster_id=1,
            owner_id="user1",
            league_id="test",
            players=["4034", "421", "5849"],  # Current players
            starters=["4034", "421"]
        )
        
        # Mock transactions for weeks 3 and 2 (working backwards from current to target week 1)
        # Week 3: Added "5849" and dropped "1234" 
        week3_transaction = Transaction(
            type="waiver",
            transaction_id="tx3",
            status="complete",
            leg=3,
            roster_ids=[1],
            adds={"5849": 1},
            drops={"1234": 1}
        )
        
        # Week 2: Added "421" 
        week2_transaction = Transaction(
            type="free_agent",
            transaction_id="tx2",
            status="complete",
            leg=2,
            roster_ids=[1],
            adds={"421": 1}
        )
        
        def mock_fetch(week):
            if week == 3:
                return [week3_transaction]
            elif week == 2:
                return [week2_transaction]
            return []
        
        mock_fetch_transactions.side_effect = mock_fetch
        
        with patch.object(self.service.league_service, 'get_rosters') as mock_get_rosters:
            mock_get_rosters.return_value = [current_roster]
            
            historical_roster = self.service.get_roster_for_week(1, 1)
            
            # Should have reversed both transactions:
            # - Remove "5849" (was added in week 3)
            # - Remove "421" (was added in week 2) 
            # - Add back "1234" (was dropped in week 3)
            expected_players = {"4034", "1234"}  # Original roster for week 1
            actual_players = set(historical_roster.players)
            
            assert actual_players == expected_players
            assert historical_roster.roster_id == 1
    
    def test_get_all_historical_rosters_for_week(self):
        """Test getting all historical rosters for a week."""
        mock_roster1 = Mock()
        mock_roster1.roster_id = 1
        mock_roster2 = Mock() 
        mock_roster2.roster_id = 2
        
        with patch.object(self.service.league_service, 'get_rosters') as mock_get_rosters:
            mock_get_rosters.return_value = [mock_roster1, mock_roster2]
            
            with patch.object(self.service, 'get_roster_for_week') as mock_get_roster:
                mock_get_roster.side_effect = lambda roster_id, week: mock_roster1 if roster_id == 1 else mock_roster2
                
                result = self.service.get_all_historical_rosters_for_week(1)
                
                assert len(result) == 2
                assert 1 in result
                assert 2 in result
                assert result[1] == mock_roster1
                assert result[2] == mock_roster2
    
    def test_clear_cache(self):
        """Test clearing cache."""
        # Set up some cached data
        self.service._transactions_cache[1] = []
        self.service._historical_rosters_cache["1_1"] = Mock()
        
        assert len(self.service._transactions_cache) == 1
        assert len(self.service._historical_rosters_cache) == 1
        
        self.service.clear_cache()
        
        assert len(self.service._transactions_cache) == 0
        assert len(self.service._historical_rosters_cache) == 0


# Fixtures for common test data
@pytest.fixture
def sample_transaction():
    """Sample transaction data."""
    return {
        "type": "waiver",
        "transaction_id": "123456",
        "status": "complete",
        "leg": 2,
        "roster_ids": [1],
        "adds": {"4034": 1},
        "drops": {"421": 1},
        "creator": "user1"
    }


@pytest.fixture
def sample_roster():
    """Sample roster data."""
    return Roster(
        roster_id=1,
        owner_id="user1",
        league_id="test_league",
        players=["4034", "421", "5849"],
        starters=["4034", "421"]
    )