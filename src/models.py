"""Data models for Rally Data Scraper."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class APIEndpoint(str, Enum):
    """Available API endpoints based on 'a' parameter."""
    ENTRY_LIST = "8"  # Nevezési lista - Entry list with detailed data
    START_LIST = "9"  # Rajtlista - Start list
    ROUTE_SHEET = "10"  # Útvonallap - Route sheet with stage IDs
    STAGE_RESULTS = "3"  # Gyorsasági szakasz részletes eredmények - Detailed stage results
    CURRENT_STAGE = "4"  # Gyorsaságin lévő autók - Cars currently on stage
    ENHANCED_CURRENT = "104"  # Enhanced version of current stage with GPS data


class RallyClass(str, Enum):
    """Rally class categories based on 'oszt' parameter."""
    ORB_CLASS_1 = "1"  # 1. osztály (ORB+Int) - Class 1 for national and international events (ERC)
    RALLYE2 = "2"      # Rallye2 class
    HISTORIC = "3"     # Historic class
    
    @property
    def description(self) -> str:
        """Get human-readable description of the class."""
        descriptions = {
            "1": "1. osztály (ORB+International/ERC)",
            "2": "Rallye2",
            "3": "Historic"
        }
        return descriptions.get(self.value, f"Class {self.value}")
    
    @classmethod
    def get_all_classes(cls) -> List[str]:
        """Get all available class values."""
        return [c.value for c in cls]


class RallyEntry(BaseModel):
    """Model for rally entry data (a=8)."""
    race_number: int = Field(alias="RSz")
    string_race_number: str = Field(alias="sRSz")
    driver: str = Field(alias="Vezető")
    navigator: str = Field(alias="Navigátor")
    nation1: str = Field(alias="Nemzet1")
    nation2: str = Field(alias="Nemzet2")
    car_make: str = Field(alias="AutoMarka")
    car_model: str = Field(alias="Autó")
    entrant: str = Field(alias="Nevezo")
    class_category: str = Field(alias="Oszt.")


class StageResult(BaseModel):
    """Model for stage results (a=3, a=4, a=104)."""
    race_number: int = Field(alias="RSz")
    string_race_number: str = Field(alias="sRSz")
    driver: str = Field(alias="Vezető")
    navigator: str = Field(alias="Navigátor")
    nation1: str = Field(alias="Nemzet1")
    nation2: str = Field(alias="Nemzet2")
    car_make: str = Field(alias="AutoMarka")
    car_model: str = Field(alias="Autó")
    entrant: str = Field(alias="Nevezo")
    class_category: str = Field(alias="Oszt.")
    start_time: Optional[str] = Field(default=None, alias="dtRajtIdo")
    elapsed_time: Optional[str] = Field(default=None, alias="EddigiIdo")
    
    # GPS data (for a=104)
    gps_lat: Optional[float] = Field(default=None, alias="koo_lat")
    gps_lon: Optional[float] = Field(default=None, alias="koo_lon")
    gps_speed: Optional[float] = Field(default=None, alias="koo_seb")
    gps_timestamp: Optional[str] = Field(default=None, alias="koo_timestamp")
    gps_heading: Optional[float] = Field(default=None, alias="koo_heading")
    
    # Estimated times
    estimated_time: Optional[str] = Field(default=None, alias="BecsTeljIdo")
    last_estimated_time: Optional[str] = Field(default=None, alias="LastBTIdo")
    time_estimate_quality: Optional[str] = Field(default=None, alias="BTIdoOk")
    
    # Stage progress
    distance_from_start: Optional[float] = Field(default=None, alias="relNyomvTavKezd")
    alert: Optional[str] = Field(default=None, alias="Alert")
    slow_stage_seconds: Optional[int] = Field(default=None, alias="LassuGyorsonSec")
    total_stage_seconds: Optional[int] = Field(default=None, alias="AllGyorsonSec")
    geometry_name: Optional[str] = Field(default=None, alias="GeomNev")
    role: Optional[str] = Field(default=None, alias="Szerep")


class RouteSheet(BaseModel):
    """Model for route sheet data (a=10)."""
    stage_id: str = Field(alias="s")
    stage_name: str
    stage_type: str
    distance: Optional[float] = None


class APIResponse(BaseModel):
    """Generic API response wrapper."""
    endpoint: APIEndpoint
    stage_id: Optional[str] = None
    data: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_message: Optional[str] = None


