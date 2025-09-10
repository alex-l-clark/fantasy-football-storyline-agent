"""Transaction data models."""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel


class Transaction(BaseModel):
    """Sleeper transaction model."""
    
    type: str  # "trade", "waiver", "free_agent"
    transaction_id: str
    status: str  # "complete", "pending"
    leg: int  # week number
    roster_ids: List[int]
    settings: Optional[Dict] = None
    metadata: Optional[Dict] = None
    creator: Optional[str] = None
    created: Optional[int] = None  # timestamp
    
    # Player movement data
    adds: Optional[Dict[str, int]] = None  # {player_id: roster_id}
    drops: Optional[Dict[str, int]] = None  # {player_id: roster_id}
    
    # Trade specific
    consenter_ids: Optional[List[int]] = None
    draft_picks: Optional[List[Dict]] = None
    
    # Waiver specific
    waiver_budget: Optional[List[Dict]] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> "Transaction":
        """Create Transaction from API response."""
        return cls(**data)
    
    @property
    def week(self) -> int:
        """Get the week this transaction occurred in."""
        return self.leg
    
    @property
    def is_completed(self) -> bool:
        """Check if transaction is completed."""
        return self.status == "complete"
    
    def affects_roster(self, roster_id: int) -> bool:
        """Check if this transaction affects a specific roster."""
        return roster_id in self.roster_ids
    
    def get_player_changes_for_roster(self, roster_id: int) -> Dict[str, str]:
        """Get player changes for a specific roster.
        
        Returns:
            Dict with 'added' and 'dropped' keys containing lists of player IDs
        """
        changes = {"added": [], "dropped": []}
        
        # Players added to this roster
        if self.adds:
            for player_id, target_roster_id in self.adds.items():
                if target_roster_id == roster_id:
                    changes["added"].append(player_id)
        
        # Players dropped from this roster
        if self.drops:
            for player_id, source_roster_id in self.drops.items():
                if source_roster_id == roster_id:
                    changes["dropped"].append(player_id)
        
        return changes