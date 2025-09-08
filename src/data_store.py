"""Simplified data processor for rally data callbacks."""

import logging
from typing import Dict, List, Optional, Callable

from .models import APIResponse, APIEndpoint


logger = logging.getLogger(__name__)


class RallyDataProcessor:
    """Simplified data processor that only handles callbacks."""
    
    def __init__(self):
        """Initialize the data processor."""
        self._callbacks: Dict[APIEndpoint, List[Callable]] = {}
        
    def add_callback(self, endpoint: APIEndpoint, callback: Callable[[List[List[str]], Optional[str], str], None]) -> None:
        """Add callback for when data is processed."""
        if endpoint not in self._callbacks:
            self._callbacks[endpoint] = []
        self._callbacks[endpoint].append(callback)
        logger.info(f"Added callback for endpoint {endpoint.value}")
        
    async def process_response(self, response: APIResponse) -> List[List[str]]:
        """Process API response and trigger callbacks."""
        if not response.success:
            logger.warning(f"Processing failed response for {response.endpoint.value}: {response.error_message}")
            return []
            
        # Use 2D array data as-is
        data = response.data
        logger.info(f"Processing {len(data)} rows for {response.endpoint.value}" + 
                   (f" stage {response.stage_id}" if response.stage_id else ""))
            
        # Trigger callbacks
        await self._trigger_callbacks(response.endpoint, data, response.stage_id, response.rally_class)
        
        return data
        
    async def _trigger_callbacks(self, endpoint: APIEndpoint, data: List[List[str]], stage_id: Optional[str] = None, rally_class: str = None) -> None:
        """Trigger all callbacks for the endpoint."""
        # Use .get() for faster lookup with default empty list
        callbacks = self._callbacks.get(endpoint, [])
        for callback in callbacks:
            try:
                await callback(data, stage_id, rally_class)
            except Exception as e:
                logger.error(f"Callback error for {endpoint.value}: {e}")
                
