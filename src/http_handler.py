"""Simple HTTP handler for rally data API."""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .api_client import HauserResultsAPIClient
from .data_store import RallyDataProcessor
from .models import APIEndpoint, RallyClass
from .multithreaded_datastore import racing_number_store
from .excel_exporter import add_to_excel_cell, save_excel_file

logger = logging.getLogger(__name__)


class TaskItem(BaseModel):
    """Individual task with rally class, endpoint, and optional stage IDs."""
    rally_class: str
    endpoint: str
    stage_ids: Optional[List[str]] = None


class TriggerRequest(BaseModel):
    """Request to trigger API calls."""
    tasks: List[TaskItem]


class AddToCellRequest(BaseModel):
    """Request to add a number to a specific Excel cell."""
    sheet: str = Field(..., description="The Excel sheet (tab) name")
    cell: str = Field(..., description="The cell reference (e.g., 'A1', 'B5')")
    value: float = Field(..., description="The number to add to the cell")


class RallyHTTPHandler:
    """Simple HTTP handler for concurrent rally data requests."""

    def __init__(self, api_client: HauserResultsAPIClient, data_processor: RallyDataProcessor):
        self.api_client = api_client
        self.data_processor = data_processor

        # Handler mappings for performance
        self._basic_handlers = {
            APIEndpoint.ENTRY_LIST: self.api_client.get_entry_list,
            APIEndpoint.START_LIST: self.api_client.get_start_list,
            APIEndpoint.ROUTE_SHEET: self.api_client.get_route_sheet
        }

        self._stage_handlers = {
            APIEndpoint.STAGE_RESULTS: self.api_client.get_stage_results,
            APIEndpoint.CURRENT_STAGE: self.api_client.get_current_stage_cars,
            APIEndpoint.ENHANCED_CURRENT: self.api_client.get_enhanced_current_stage,
            APIEndpoint.ROLL: self.api_client.get_roll_call
        }

        self.app = FastAPI(title="Rally Data API", version="1.0.0")
        self._setup_routes()

    def _validate_task(self, index: int, task: TaskItem) -> Optional[str]:
        """Validate a single task. Returns error message if invalid."""
        try:
            RallyClass(task.rally_class)
            endpoint = APIEndpoint(task.endpoint)
            
            if endpoint.needs_stage_id() and not task.stage_ids:
                return f"Task {index}: Endpoint '{task.endpoint}' requires stage_ids"
            elif not endpoint.needs_stage_id() and task.stage_ids:
                return f"Task {index}: Endpoint '{task.endpoint}' does not use stage_ids"
                
        except ValueError as e:
            return f"Task {index}: Invalid - {str(e)}"
        
        return None

    async def _execute_task(self, endpoint: APIEndpoint, rally_class: str, stage_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a single API task and process its response."""
        try:
            if endpoint.needs_stage_id():
                handler = self._stage_handlers.get(endpoint)
                if not handler:
                    return {"success": False, "error": "Unknown stage endpoint handler"}
                response = await handler(stage_id, rally_class=rally_class)
            else:
                handler = self._basic_handlers.get(endpoint)
                if not handler:
                    return {"success": False, "error": "Unknown basic endpoint handler"}
                response = await handler(rally_class=rally_class)

            await self.data_processor.process_response(response)
            return {"success": response.success, "error": response.error_message}

        except Exception as e:
            logger.error(f"Failed to execute task for endpoint {endpoint.value} (stage {stage_id}, class {rally_class}): {e}")
            return {"success": False, "error": str(e)}

    def _setup_routes(self):
        """Setup HTTP routes."""
        
        @self.app.get("/")
        async def root():
            return {
                "name": "Rally Data API",
                "version": "1.0.0",
                "endpoints": ["/trigger", "/update-racing-number", "/add-to-cell", "/save"],
                "rally_classes": RallyClass.get_all_classes(),
                "available_endpoints": [e.value for e in APIEndpoint],
                "example": {
                    "tasks": [
                        {"rally_class": "1", "endpoint": "8"},
                        {"rally_class": "2", "endpoint": "9"},
                        {"rally_class": "1", "endpoint": "3", "stage_ids": ["1", "2"]}
                    ]
                },
                "excel_examples": {
                    "add_to_cell": {
                        "sheet": "ORB_ENHANCED_1",
                        "cell": "A1",
                        "value": 5.5
                    }
                }
            }

        @self.app.post("/trigger")
        async def trigger_data_update(request: TriggerRequest):
            """Execute tasks concurrently."""
            if not request.tasks:
                raise HTTPException(status_code=400, detail="No tasks provided")

            # Validate all tasks first
            validation_errors = []
            for i, task in enumerate(request.tasks):
                error = self._validate_task(i, task)
                if error:
                    validation_errors.append(error)

            if validation_errors:
                raise HTTPException(status_code=400, detail="; ".join(validation_errors))

            coroutines = []
            task_names = []

            for i, task in enumerate(request.tasks):
                endpoint = APIEndpoint(task.endpoint)
                rally_class = task.rally_class
                endpoint_value = task.endpoint
                
                if endpoint.needs_stage_id():
                    for stage_id in task.stage_ids:
                        task_name = f"task_{i}_{rally_class}_{endpoint_value}_{stage_id}"
                        coroutine = self._execute_task(endpoint, rally_class, stage_id)
                        coroutines.append(coroutine)
                        task_names.append(task_name)
                else:
                    task_name = f"task_{i}_{rally_class}_{endpoint_value}"
                    coroutine = self._execute_task(endpoint, rally_class)
                    coroutines.append(coroutine)
                    task_names.append(task_name)

            logger.info(f"Starting {len(coroutines)} tasks concurrently")
            async_tasks = [asyncio.create_task(coro) for coro in coroutines]

            # Wait for all tasks to complete
            results = await asyncio.gather(*async_tasks, return_exceptions=True)

            task_results = {}
            success_count = 0

            for task_name, result in zip(task_names, results):
                if isinstance(result, Exception):
                    task_results[task_name] = {"success": False, "error": str(result)}
                elif isinstance(result, dict) and result.get("success"):
                    task_results[task_name] = result
                    success_count += 1
                else:
                    task_results[task_name] = {"success": False, "error": "Unknown error"}

            logger.info(f"Completed: {success_count}/{len(async_tasks)} successful")

            return {
                "message": "Tasks completed",
                "tasks_requested": len(request.tasks),
                "tasks_executed": len(async_tasks),
                "tasks_successful": success_count,
                "results": task_results,
                "timestamp": datetime.utcnow().isoformat(),
                "success": success_count == len(async_tasks)
            }
        
        @self.app.post("/update-racing-number")
        async def update_racing_number():
            """Update racing numbers by reading from Excel file and trigger data refresh."""
            try:
                success = racing_number_store.update_from_excel()
                if success:
                    racing_numbers = racing_number_store.get_all_racing_numbers()
                    stages = racing_number_store.get_all_stages()
                    
                    # Create trigger request for all rally classes with enhanced current stage
                    tasks = []
                    for rally_class in RallyClass:
                        stage_id = stages.get(rally_class.value)
                        if stage_id:
                            task_item = TaskItem(
                                rally_class=rally_class.value,
                                endpoint=APIEndpoint.get_value("enhanced_current"),
                                stage_ids=[stage_id]
                            )
                        else:
                            task_item = TaskItem(
                                rally_class=rally_class.value,
                                endpoint=APIEndpoint.get_value("enhanced_current")
                            )
                        tasks.append(task_item)
                    
                    # Create trigger request and call trigger endpoint internally
                    trigger_request = TriggerRequest(tasks=tasks)
                    trigger_result = await trigger_data_update(trigger_request)
                    
                    return {
                        "message": "Racing numbers and stages updated and data refreshed",
                        "racing_numbers": racing_numbers,
                        "stages": stages,
                        "success": True,
                        "trigger_result": trigger_result
                    }
                else:
                    return {
                        "message": "Failed to update racing numbers from Excel",
                        "success": False
                    }
            except Exception as e:
                logger.error(f"Error updating racing numbers: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/add-to-cell")
        async def add_to_cell(request: AddToCellRequest):
            """Add a number to a specific Excel cell."""
            try:
                new_value = await add_to_excel_cell(request.sheet, request.cell, request.value)
                return {
                    "message": f"Added {request.value} to cell {request.cell} in sheet '{request.sheet}'",
                    "sheet": request.sheet,
                    "cell": request.cell,
                    "value_added": request.value,
                    "new_value": new_value,
                    "success": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Error adding to Excel cell: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/save")
        async def save_excel():
            """Save the Excel file."""
            try:
                message = await save_excel_file()
                return {
                    "message": message,
                    "success": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Error saving Excel file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def get_app(self) -> FastAPI:
        return self.app