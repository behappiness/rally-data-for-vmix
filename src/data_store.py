"""Data processing and management for rally data."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime
from dataclasses import dataclass

from .models import APIResponse, APIEndpoint
from .config import settings


logger = logging.getLogger(__name__)


@dataclass
class DataQuery:
    """Query parameters for data retrieval."""
    race_numbers: Optional[List[int]] = None
    stage_ids: Optional[List[str]] = None
    classes: Optional[List[str]] = None
    drivers: Optional[List[str]] = None
    with_gps: bool = False
    active_only: bool = False


class RallyDataProcessor:
    """Data processor for rally data with callback support."""
    
    def __init__(self):
        """Initialize the data processor."""
        self._lock = asyncio.Lock()
        self._callbacks: Dict[APIEndpoint, List[Callable]] = {}
        self._current_data: Dict[str, Any] = {}
        
    def add_callback(self, endpoint: APIEndpoint, callback: Callable[[List[Dict[str, Any]], Optional[str]], None]) -> None:
        """Add callback for when data is processed."""
        if endpoint not in self._callbacks:
            self._callbacks[endpoint] = []
        self._callbacks[endpoint].append(callback)
        logger.info(f"Added callback for endpoint {endpoint.value}")
        
    def remove_callback(self, endpoint: APIEndpoint, callback: Callable) -> None:
        """Remove callback for endpoint."""
        if endpoint in self._callbacks and callback in self._callbacks[endpoint]:
            self._callbacks[endpoint].remove(callback)
            logger.info(f"Removed callback for endpoint {endpoint.value}")
            
    async def process_response(self, response: APIResponse) -> List[Dict[str, Any]]:
        """Process API response and trigger callbacks."""
        async with self._lock:
            if not response.success:
                logger.warning(f"Processing failed response for {response.endpoint.value}: {response.error_message}")
                return []
                
            # Keep raw data as-is, no complex model conversion
            processed_data = response.data
            logger.info(f"Processed {len(processed_data)} records for {response.endpoint.value}" + 
                       (f" stage {response.stage_id}" if response.stage_id else ""))
                
            # Store current data for immediate access
            key = f"{response.endpoint.value}_{response.stage_id}" if response.stage_id else response.endpoint.value
            self._current_data[key] = {
                'data': processed_data,
                'timestamp': datetime.utcnow(),
                'stage_id': response.stage_id
            }
            
            # Trigger callbacks
            await self._trigger_callbacks(response.endpoint, processed_data, response.stage_id)
            
            return processed_data
            
    async def _trigger_callbacks(self, endpoint: APIEndpoint, data: List[Dict[str, Any]], stage_id: Optional[str] = None) -> None:
        """Trigger all callbacks for the endpoint."""
        if endpoint in self._callbacks:
            for callback in self._callbacks[endpoint]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data, stage_id)
                    else:
                        callback(data, stage_id)
                except Exception as e:
                    logger.error(f"Callback error for {endpoint.value}: {e}")
            
        
    async def get_current_data(self, endpoint: APIEndpoint, stage_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get currently stored data for an endpoint."""
        key = f"{endpoint.value}_{stage_id}" if stage_id else endpoint.value
        return self._current_data.get(key)
        
    async def get_status(self) -> Dict[str, Any]:
        """Get processor status information."""
        status = {
            'available_data': list(self._current_data.keys()),
            'callback_endpoints': list(self._callbacks.keys()),
            'callback_counts': {ep.value: len(callbacks) for ep, callbacks in self._callbacks.items()},
            'last_update': datetime.utcnow().isoformat()
        }
        return status
                
