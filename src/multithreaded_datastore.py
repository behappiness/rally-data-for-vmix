"""Multithreaded datastore for racing number that reads from Excel."""

import logging
import threading
from typing import Optional
import xlwings as xw
from .config import settings
from .models import RallyClass, RALLY_CLASS_NAMES

logger = logging.getLogger(__name__)


class MultithreadedDatastore:
    """Multithreaded datastore for racing numbers by class."""
    
    def __init__(self):
        """Initialize the racing number and stage store."""
        self._racing_numbers: dict[str, str] = {}
        self._stages: dict[str, str] = {}
        self._lock = threading.Lock()
    
    def get_racing_number(self, rally_class: str) -> Optional[str]:
        """Get the racing number for a specific rally class thread-safely."""
        with self._lock:
            return self._racing_numbers.get(rally_class)
    
    def get_stage(self, rally_class: str) -> Optional[str]:
        """Get the stage for a specific rally class thread-safely."""
        with self._lock:
            return self._stages.get(rally_class)
    
    def get_all_racing_numbers(self) -> dict[str, str]:
        """Get all racing numbers thread-safely."""
        with self._lock:
            return self._racing_numbers.copy()
    
    def get_all_stages(self) -> dict[str, str]:
        """Get all stages thread-safely."""
        with self._lock:
            return self._stages.copy()
    
    def set_racing_number(self, rally_class: str, racing_number: str) -> None:
        """Set the racing number for a specific rally class thread-safely."""
        with self._lock:
            self._racing_numbers[rally_class] = racing_number
            logger.info(f"Racing number for class {rally_class} set to: {racing_number}")
    
    def set_stage(self, rally_class: str, stage: str) -> None:
        """Set the stage for a specific rally class thread-safely."""
        with self._lock:
            self._stages[rally_class] = stage
            logger.info(f"Stage for class {rally_class} set to: {stage}")
    
    def set_all_racing_numbers(self, racing_numbers: dict[str, str]) -> None:
        """Set all racing numbers thread-safely."""
        with self._lock:
            self._racing_numbers = racing_numbers.copy()
            logger.info(f"Updated racing numbers: {racing_numbers}")
    
    def set_all_stages(self, stages: dict[str, str]) -> None:
        """Set all stages thread-safely."""
        with self._lock:
            self._stages = stages.copy()
            logger.info(f"Updated stages: {stages}")
    
    def update_from_excel(self) -> bool:
        """Update racing numbers by reading from Excel range with headers."""
        try:
            wb = xw.Book(settings.excel_filename)
            logger.debug(f"Connected to workbook: {settings.excel_filename}")
            
            try:
                sheet = wb.sheets[settings.racing_number_tab]
                logger.debug(f"Found sheet: {settings.racing_number_tab}")
            except Exception:
                logger.warning(f"Sheet '{settings.racing_number_tab}' not found in Excel file")
                return False
            
            try:
                # Read the range as 2D array (now 3 rows: headers, racing numbers, stages)
                range_data = sheet.range(settings.racing_number_range).value
                if not range_data or len(range_data) < 3:
                    logger.warning(f"Invalid data in range {settings.racing_number_range} - need 3 rows")
                    return False
                
                # First row: headers (rally class names or numbers)
                # Second row: racing numbers
                # Third row: stages
                headers = range_data[0]
                racing_number_values = range_data[1]
                stage_values = range_data[2]
                
                if not isinstance(headers, (list, tuple)):
                    headers = [headers]
                if not isinstance(racing_number_values, (list, tuple)):
                    racing_number_values = [racing_number_values]
                if not isinstance(stage_values, (list, tuple)):
                    stage_values = [stage_values]
                
                racing_numbers = {}
                stages = {}
                
                for i, header in enumerate(headers):
                    if header is not None:
                        class_key = str(header).strip()
                        if class_key:
                            try:
                                # Validate using RallyClass enum
                                RallyClass(class_key)
                                
                                # Get racing number
                                if i < len(racing_number_values) and racing_number_values[i] is not None:
                                    racing_number = str(racing_number_values[i]).strip()
                                    if racing_number:
                                        racing_numbers[class_key] = racing_number
                                
                                # Get stage
                                if i < len(stage_values) and stage_values[i] is not None:
                                    stage = str(stage_values[i]).strip()
                                    if stage:
                                        stages[class_key] = stage
                                        
                            except ValueError:
                                # Invalid rally class, skip
                                continue
                
                if racing_numbers or stages:
                    if racing_numbers:
                        self.set_all_racing_numbers(racing_numbers)
                        logger.info(f"Updated racing numbers from Excel: {racing_numbers}")
                    if stages:
                        self.set_all_stages(stages)
                        logger.info(f"Updated stages from Excel: {stages}")
                    return True
                else:
                    logger.warning("No valid racing numbers or stages found in Excel range")
                    return False
                    
            except Exception as e:
                logger.error(f"Error reading range {settings.racing_number_range}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error accessing Excel file {settings.excel_filename}: {e}")
            return False


# Global multithreaded datastore instance
racing_number_store = MultithreadedDatastore()
