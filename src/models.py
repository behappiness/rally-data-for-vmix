"""Simple data models for Rally Data Scraper."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Simple object maps for fast lookups
RALLY_CLASS_NAMES = {
    "1": "ORB",
    "2": "R2", 
    "3": "HST"
}

ENDPOINT_CSV_NAMES = {
    "8": "entry",
    "9": "start",
    "10": "route",
    "3": "stage",
    "4": "current",
    "104": "enhanced"
}

ENDPOINT_EXCEL_NAMES = {
    "8": "ENTRY",
    "9": "START",
    "10": "ROUTE",
    "3": "STAGE",
    "4": "CURRENT",
    "104": "ENHANCED"
}

# Endpoints that need stage ID parameter ('s')
STAGE_ENDPOINTS = {"3", "4", "104"}


class APIEndpoint(str, Enum):
    """Available API endpoints based on 'a' parameter."""
    ENTRY_LIST = "8"
    START_LIST = "9"
    ROUTE_SHEET = "10"
    STAGE_RESULTS = "3"
    CURRENT_STAGE = "4"
    ENHANCED_CURRENT = "104"
    
    def needs_stage_id(self) -> bool:
        """Check if endpoint needs stage ID parameter."""
        return self.value in STAGE_ENDPOINTS
    
    @classmethod
    def get_value(cls, endpoint_name: str) -> str:
        """Get endpoint value by name."""
        return getattr(cls, endpoint_name.upper()).value
    
    def get_csv_filename(self, rally_class: str, stage_id: Optional[str] = None) -> str:
        """Get CSV filename with rally class and optional stage ID."""
        class_name = RALLY_CLASS_NAMES.get(rally_class, f"{rally_class}")
        base_name = ENDPOINT_CSV_NAMES.get(self.value, f"{self.value}")
        
        if stage_id and self.needs_stage_id():
            return f"{class_name}_{base_name}_{stage_id}.csv"
        return f"{class_name}_{base_name}.csv"
    
    def get_excel_sheet(self, rally_class: str, stage_id: Optional[str] = None) -> str:
        """Get Excel sheet name with rally class and optional stage ID."""
        class_name = RALLY_CLASS_NAMES.get(rally_class, f"{rally_class}")
        base_name = ENDPOINT_EXCEL_NAMES.get(self.value, f"{self.value}")
        
        if stage_id and self.needs_stage_id():
            return f"{class_name}_{base_name}_{stage_id}"
        return f"{class_name}_{base_name}"


class RallyClass(str, Enum):
    """Rally class categories."""
    ORB = "1"
    RALLYE2 = "2"
    HISTORIC = "3"
    
    @property
    def description(self) -> str:
        """Get description."""
        return RALLY_CLASS_NAMES.get(self.value, f"{self.value}")
    
    @classmethod
    def get_all_classes(cls) -> List[str]:
        """Get all class values."""
        return [c.value for c in cls]


class APIResponse(BaseModel):
    """API response wrapper with 2D array data."""
    endpoint: APIEndpoint
    stage_id: Optional[str] = None
    rally_class: str
    data: List[List[str]]  # 2D array: [headers, row1, row2, ...]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: Optional[str] = None


# Note: Pydantic data models removed - using simple 2D arrays for direct CSV/Excel export