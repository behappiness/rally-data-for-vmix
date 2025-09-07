"""Simplified Excel export functionality using xlwings for rally data."""

import asyncio
import logging
from typing import List, Dict, Any
import xlwings as xw

from .config import settings


logger = logging.getLogger(__name__)


class ExcelExporter:
    """Simplified Excel export functionality using xlwings."""
    
    def __init__(self):
        """Initialize the Excel exporter."""
        self._lock = asyncio.Lock()
        
    async def export_to_sheet(
        self,
        data: List[Dict[str, Any]],
        sheet_name: str
    ) -> str:
        """Export data to a specific sheet in the Excel file."""
        if not data:
            raise ValueError("No data provided for export")
            
        async with self._lock:
            try:
                # Run Excel operations in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._write_to_sheet, data, sheet_name)
                
                logger.info(f"Exported {len(data)} records to sheet '{sheet_name}' in {settings.excel_filename}")
                return settings.excel_filename
                
            except Exception as e:
                logger.error(f"Failed to export to Excel sheet '{sheet_name}': {e}")
                raise
                
    def _write_to_sheet(self, data: List[Dict[str, Any]], sheet_name: str):
        """Write data to specific sheet using xlwings (runs in thread pool)."""
        wb = None
        
        try:
            # Clean sheet name (Excel limitations)
            clean_sheet_name = self._clean_sheet_name(sheet_name)
            
            # Try to open existing workbook from open Excel files
            try:
                wb = xw.Book(settings.excel_filename)
                logger.debug(f"Opened existing workbook: {settings.excel_filename}")
            except:
                # If file doesn't exist or isn't open, skip export
                logger.warning(f"Excel file {settings.excel_filename} not found or not open, skipping export")
                return
            
            # Get or create sheet
            try:
                sheet = wb.sheets[clean_sheet_name]
                logger.debug(f"Found existing sheet: {clean_sheet_name}")
            except:
                # Sheet doesn't exist, create it
                sheet = wb.sheets.add(name=clean_sheet_name)
                logger.debug(f"Created new sheet: {clean_sheet_name}")
            
            # Get headers from first record
            headers = list(data[0].keys()) if data else []
            
            if headers:
                # Always write headers (overwrite existing ones)
                sheet.range('A1').value = headers
                
                # Write data rows starting from row 2
                for i, record in enumerate(data):
                    row_num = 2 + i
                    row_values = [record.get(header, '') for header in headers]
                    sheet.range(f'A{row_num}').value = row_values
                
                # Auto-fit columns
                sheet.autofit('c')
                
                logger.debug(f"Set {len(data)} rows in sheet '{clean_sheet_name}' starting from row 2")
            
            # Save workbook
            wb.save()
            
        except Exception as e:
            logger.error(f"Error writing to Excel sheet: {e}")
            raise
                
    def _clean_sheet_name(self, name: str) -> str:
        """Clean sheet name to comply with Excel limitations."""
        # Excel sheet name limitations:
        # - Max 31 characters
        # - Cannot contain: \ / ? * [ ]
        # - Cannot be empty
        
        if not name:
            name = "Sheet"
            
        # Remove invalid characters
        invalid_chars = ['\\', '/', '?', '*', '[', ']']
        for char in invalid_chars:
            name = name.replace(char, '_')
            
        # Truncate to 31 characters
        if len(name) > 31:
            name = name[:31]
            
        return name
