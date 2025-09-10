"""CSV export functionality for rally data."""

import aiofiles
import logging
from pathlib import Path
from typing import List

from .config import settings
from .multithreaded_datastore import racing_number_store
from .models import RallyClass


logger = logging.getLogger(__name__)


async def export_to_csv(
    data: List[List[str]],
    filename: str
) -> str:
    """Export 2D array data to CSV file using async operations."""
    if not data:
        raise ValueError("No data provided for export")
        
    try:
        delimiter = settings.csv_delimiter
        csv_lines = [delimiter.join(row) for row in data]
        
        await _write_csv_data(filename, csv_lines)
        
        logger.info(f"Exported {len(data)} rows to {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Failed to export CSV to {filename}: {e}")
        raise


async def export_racing_speed(response) -> None:
    """Callback to export racing speed filtered by racing number."""
    if not response.success or not response.data:
        logger.warning("No data to export for racing speed")
        return
    
    racing_number = racing_number_store.get_racing_number(response.rally_class)
    if not racing_number:
        logger.debug(f"No racing number set for class {response.rally_class}, skipping racing speed export")
        return
    
    try:
        filtered_data = _filter_data_by_racing_number(response.data, racing_number)
        
        if not filtered_data:
            logger.debug(f"No data found for racing number {racing_number}")
            return
        
        # Get rally class name for filename
        try:
            rally_class = RallyClass(response.rally_class)
            class_name = rally_class.description.lower().replace(" ", "_")
        except (ValueError, AttributeError):
            class_name = response.rally_class
        
        filename = f"{class_name}_{settings.racing_speed_filename}.csv"
        await export_to_csv(filtered_data, filename)
        logger.info(f"Exported racing speed for racing number {racing_number}")
        
    except Exception as e:
        logger.error(f"Failed to export racing speed: {e}")


def _filter_data_by_racing_number(data: List[List[str]], racing_number: str) -> List[List[str]]:
    """Filter 2D array data by racing number, keeping headers."""
    if not data:
        return []
    
    headers = data[0]
    filtered_data = [headers]
    
    racing_number_col = 0
    
    for row in data[1:]:
        if row and len(row) > racing_number_col:
            if str(row[racing_number_col]).strip() == racing_number.strip():
                filtered_data.append(row)
    
    return filtered_data


async def _write_csv_data(filename: str, csv_lines: List[str]):
    """Write CSV data to file in async task."""
    output_dir = Path(settings.csv_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = output_dir / filename
    
    if not filename.endswith('.csv'):
        file_path = file_path.with_suffix('.csv')
    
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write('\n'.join(csv_lines))


