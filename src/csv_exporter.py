"""CSV and Excel export functionality for rally data."""

import asyncio
import aiofiles
import logging
from pathlib import Path
from typing import List, Dict, Any

from .config import settings
from .excel_exporter import ExcelExporter


logger = logging.getLogger(__name__)

# Global lock for CSV operations
_csv_lock = asyncio.Lock()

# Global Excel exporter instance
_excel_exporter = ExcelExporter()


async def export_to_csv(
    data: List[Dict[str, Any]],
    filename: str
) -> str:
    """Export data to CSV file with headers."""
    if not data:
        raise ValueError("No data provided for export")
        
    async with _csv_lock:
        output_dir = Path(settings.csv_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = output_dir / filename
        
        # Ensure filename has .csv extension
        if not filename.endswith('.csv'):
            file_path = file_path.with_suffix('.csv')
            
        try:
            # Get headers from first record
            headers = list(data[0].keys()) if data else []
            
            # Create CSV content
            csv_lines = []
            
            # Add headers
            csv_lines.append(settings.csv_delimiter.join(f'"{header}"' for header in headers))
            
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
                    if settings.csv_delimiter in value or '"' in value or '\n' in value:
                        value = f'"{value.replace('"', '""')}"'
                    row_values.append(value)
                csv_lines.append(settings.csv_delimiter.join(row_values))
            
            # Write to file
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write('\n'.join(csv_lines))
                
            logger.info(f"Exported {len(data)} records to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to export CSV to {file_path}: {e}")
            raise


async def export_to_excel_sheet(
    data: List[Dict[str, Any]],
    sheet_name: str
) -> str:
    """Export data to a specific Excel sheet."""
    return await _excel_exporter.export_to_sheet(data, sheet_name)
