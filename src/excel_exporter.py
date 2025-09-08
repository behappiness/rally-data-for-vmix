"""Simplified Excel export functionality using xlwings for rally data."""

import logging
from typing import List
import xlwings as xw

from .config import settings


logger = logging.getLogger(__name__)


async def export_to_excel_sheet(
    data: List[List[str]],
    sheet_name: str
) -> str:
    """Export 2D array data to a specific Excel sheet using async xlwings."""
    if not data:
        raise ValueError("No data provided for export")
        
    try:
        await _write_excel_data(sheet_name, data)
        logger.info(f"Exported {len(data)} rows to sheet '{sheet_name}' in {settings.excel_filename}")
        return settings.excel_filename
        
    except Exception as e:
        logger.error(f"Failed to export to Excel sheet '{sheet_name}': {e}")
        raise


@xw.func(async_mode='threading')
async def _write_excel_data(sheet_name: str, all_data: List[List]):
    """Write all Excel data in a single thread operation."""
    try:
        try:
            wb = xw.Book(settings.excel_filename)
            logger.debug(f"Connected to existing workbook: {settings.excel_filename}")
        except:
            logger.warning(f"Excel file {settings.excel_filename} not found or not open, skipping export")
            return
        
        try:
            sheet = wb.sheets[sheet_name]
            logger.debug(f"Found existing sheet: {sheet_name}")
        except:
            sheet = wb.sheets.add(name=sheet_name)
            logger.debug(f"Created new sheet: {sheet_name}")
        
        if all_data:
            num_cols = len(all_data[0])
            num_rows = len(all_data)
            
            if num_cols > 0:
                if num_cols <= 26:
                    end_col = chr(64 + num_cols)
                else:
                    col_index = num_cols - 1
                    if col_index < 702:
                        first_char = chr(65 + col_index // 26 - 1)
                        second_char = chr(65 + col_index % 26)
                        end_col = first_char + second_char
                    else:
                        end_col = f"Z{num_cols}"
                
                range_str = f'A1:{end_col}{num_rows}'
                sheet.range(range_str).value = all_data
                
                logger.debug(f"Set {num_rows} rows in sheet '{sheet_name}'")
        
        wb.save()
        
    except Exception as e:
        logger.error(f"Error writing to Excel sheet: {e}")
        raise
