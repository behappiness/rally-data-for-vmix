"""Simplified Excel export functionality using xlwings for rally data."""

import logging
from typing import List
import xlwings as xw

from .config import settings


logger = logging.getLogger(__name__)


def _clear_cells_after_range(sheet, num_rows: int, num_cols: int, end_col: str):
    """Clear cells after the data range based on horizontal and vertical cleaning settings."""
    try:
        # Calculate the starting position for cleaning
        start_row = num_rows + 1
        start_col = num_cols + 1
        
        # Calculate the ending position for cleaning
        end_row = num_rows + settings.excel_clean_vertical_cells
        end_col_clean = _get_column_letter(num_cols + settings.excel_clean_horizontal_cells)
        
        # Only clear if we have cells to clear
        if end_row > num_rows or end_col_clean != end_col:
            # Clear horizontal cells (right of data)
            if settings.excel_clean_horizontal_cells > 0:
                horizontal_range = f"{_get_column_letter(start_col)}1:{end_col_clean}{num_rows}"
                sheet.range(horizontal_range).value = ""
                logger.debug(f"Cleared horizontal cells: {horizontal_range}")
            
            # Clear vertical cells (below data)
            if settings.excel_clean_vertical_cells > 0:
                vertical_range = f"A{start_row}:{end_col}{end_row}"
                sheet.range(vertical_range).value = ""
                logger.debug(f"Cleared vertical cells: {vertical_range}")
            
            # Clear the corner area if both horizontal and vertical cleaning are enabled
            if settings.excel_clean_horizontal_cells > 0 and settings.excel_clean_vertical_cells > 0:
                corner_range = f"{_get_column_letter(start_col)}{start_row}:{end_col_clean}{end_row}"
                sheet.range(corner_range).value = ""
                logger.debug(f"Cleared corner cells: {corner_range}")
                
    except Exception as e:
        logger.error(f"Error clearing cells after range: {e}")


def _get_column_letter(col_num: int) -> str:
    """Convert column number to Excel column letter (1-based)."""
    if col_num <= 26:
        return chr(64 + col_num)
    else:
        col_index = col_num - 1
        if col_index < 702:
            first_char = chr(65 + col_index // 26 - 1)
            second_char = chr(65 + col_index % 26)
            return first_char + second_char
        else:
            return f"Z{col_num}"


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
                
                # Clear cells after the data range if cleaning is enabled
                if settings.excel_clean_horizontal_cells > 0 or settings.excel_clean_vertical_cells > 0:
                    _clear_cells_after_range(sheet, num_rows, num_cols, end_col)
                
                logger.debug(f"Set {num_rows} rows in sheet '{sheet_name}'")
        
        wb.save()
        
    except Exception as e:
        logger.error(f"Error writing to Excel sheet: {e}")
        raise
