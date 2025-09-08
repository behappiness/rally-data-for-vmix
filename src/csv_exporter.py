"""CSV export functionality for rally data."""

import aiofiles
import logging
from pathlib import Path
from typing import List

from .config import settings


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


async def _write_csv_data(filename: str, csv_lines: List[str]):
    """Write CSV data to file in async task."""
    output_dir = Path(settings.csv_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = output_dir / filename
    
    # Ensure filename has .csv extension
    if not filename.endswith('.csv'):
        file_path = file_path.with_suffix('.csv')
    
    # Write to file
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write('\n'.join(csv_lines))


