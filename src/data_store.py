"""Simplified data processor for rally data callbacks."""

import logging
from typing import Dict, List, Optional, Callable

from .models import APIResponse, APIEndpoint


logger = logging.getLogger(__name__)


def filter_racing_numbers(data: List[List[str]], rs_column_name: str = "RSz") -> List[List[str]]:
    """Filter out rows where racing number (RSz) is greater than 900."""
    if not data or len(data) < 2:
        return data
    
    headers = data[0]
    filtered_data = [headers]
    
    # Find the RSz column index
    rs_column_index = None
    for i, header in enumerate(headers):
        if header and str(header).strip() == rs_column_name:
            rs_column_index = i
            break
    
    if rs_column_index is None:
        logger.warning(f"RSz column '{rs_column_name}' not found in headers: {headers}")
        return data
    
    removed_count = 0
    for row in data[1:]:
        if row and len(row) > rs_column_index:
            try:
                # Try to convert the racing number to integer
                racing_number_str = str(row[rs_column_index]).strip()
                if racing_number_str and racing_number_str.isdigit():
                    racing_number = int(racing_number_str)
                    if racing_number <= 900:
                        filtered_data.append(row)
                    else:
                        removed_count += 1
                        logger.debug(f"Filtered out racing number {racing_number} (> 900)")
                else:
                    # Keep non-numeric or empty racing numbers
                    filtered_data.append(row)
            except (ValueError, TypeError) as e:
                # Keep rows with invalid racing number format
                filtered_data.append(row)
                logger.debug(f"Keeping row with invalid racing number format: {e}")
        else:
            # Keep rows that don't have enough columns
            filtered_data.append(row)
    
    if removed_count > 0:
        logger.info(f"Filtered out {removed_count} rows with racing numbers > 900")
    
    return filtered_data


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
        
        # Apply racing number filtering (remove RSz > 900)
        filtered_data = filter_racing_numbers(data)
        if len(filtered_data) != len(data):
            logger.info(f"Filtered data: {len(data)} -> {len(filtered_data)} rows for {response.endpoint.value}")
        
        # Trigger callbacks - use filtered data for most callbacks, but original data for racing speed
        await self._trigger_callbacks(response.endpoint, filtered_data, response.stage_id, response.rally_class)
        
        return filtered_data
        
    async def _trigger_callbacks(self, endpoint: APIEndpoint, data: List[List[str]], stage_id: Optional[str] = None, rally_class: str = None) -> None:
        """Trigger all callbacks for the endpoint."""
        # Use .get() for faster lookup with default empty list
        callbacks = self._callbacks.get(endpoint, [])
        for callback in callbacks:
            try:
                await callback(data, stage_id, rally_class)
            except Exception as e:
                logger.error(f"Callback error for {endpoint.value}: {e}")
                
