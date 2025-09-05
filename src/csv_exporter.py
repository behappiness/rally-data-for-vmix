"""Simple CSV export functionality for rally data."""

import asyncio
import aiofiles
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import settings


logger = logging.getLogger(__name__)


class CSVExporter:
    """Simple CSV export functionality."""
    
    def __init__(self):
        """Initialize the CSV exporter."""
        self.output_dir = Path(settings.csv_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delimiter = settings.csv_delimiter
        self._lock = asyncio.Lock()
        
    async def export_to_csv(
        self,
        data: List[Dict[str, Any]],
        filename: str
    ) -> str:
        """Export data to CSV file with headers."""
        if not data:
            raise ValueError("No data provided for export")
            
        async with self._lock:
            file_path = self.output_dir / filename
            
            # Ensure filename has .csv extension
            if not filename.endswith('.csv'):
                file_path = file_path.with_suffix('.csv')
                
            try:
                # Get headers from first record
                headers = list(data[0].keys()) if data else []
                
                # Create CSV content
                csv_lines = []
                
                # Add headers
                csv_lines.append(self.delimiter.join(f'"{header}"' for header in headers))
                
                # Add data rows
                for record in data:
                    row_values = []
                    for header in headers:
                        value = record.get(header, '')
                        if value is None:
                            value = ''
                        else:
                            value = str(value)
                        # Simple CSV escaping
                        if self.delimiter in value or '"' in value or '\n' in value:
                            value = f'"{value.replace('"', '""')}"'
                        row_values.append(value)
                    csv_lines.append(self.delimiter.join(row_values))
                
                # Write to file
                async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                    await f.write('\n'.join(csv_lines))
                    
                logger.info(f"Exported {len(data)} records to {file_path}")
                return str(file_path)
                
            except Exception as e:
                logger.error(f"Failed to export CSV to {file_path}: {e}")
                raise
