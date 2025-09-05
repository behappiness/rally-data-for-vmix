"""Simple HTTP handler for API reruns."""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel

from .api_client import HauserResultsAPIClient
from .data_store import RallyDataProcessor
from .models import APIEndpoint, RallyClass
from .csv_exporter import CSVExporter


logger = logging.getLogger(__name__)


class TriggerRequest(BaseModel):
    """Request model for triggering API calls."""
    endpoints: List[str]
    stage_ids: Optional[List[str]] = None
    rally_class: str = "1"


class RallyHTTPHandler:
    """Simple HTTP handler for rerunning API requests."""
    
    def __init__(
        self,
        api_client: HauserResultsAPIClient,
        data_processor: RallyDataProcessor,
        csv_exporter: CSVExporter
    ):
        """Initialize the HTTP handler."""
        self.api_client = api_client
        self.data_processor = data_processor
        self.csv_exporter = csv_exporter
        self.app = FastAPI(
            title="Rally Data API",
            description="Simple API for rerunning rally data requests",
            version="1.0.0"
        )
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up simple HTTP routes."""
        
        @self.app.get("/")
        async def root():
            """Root endpoint with API information."""
            return {
                "name": "Rally Data API",
                "version": "1.0.0",
                "description": "Simple API for rerunning rally data requests",
                "endpoints": {
                    "trigger": "/trigger"
                }
            }
            
        @self.app.post("/trigger")
        async def trigger_data_update(request: TriggerRequest):
            """Trigger immediate data updates for specific endpoints."""
            try:
                # Validate rally class
                try:
                    RallyClass(request.rally_class)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid rally class: {request.rally_class}. Valid values: {RallyClass.get_all_classes()}")
                
                results = {}
                
                for endpoint_str in request.endpoints:
                    try:
                        endpoint = APIEndpoint(endpoint_str)
                    except ValueError:
                        results[endpoint_str] = {"success": False, "error": "Invalid endpoint"}
                        continue
                        
                    if endpoint in [APIEndpoint.STAGE_RESULTS, APIEndpoint.CURRENT_STAGE, APIEndpoint.ENHANCED_CURRENT]:
                        if not request.stage_ids:
                            results[endpoint_str] = {"success": False, "error": "Stage IDs required for this endpoint"}
                            continue
                            
                        for stage_id in request.stage_ids:
                            # Execute API call
                            if endpoint == APIEndpoint.STAGE_RESULTS:
                                response = await self.api_client.get_stage_results(stage_id, rally_class=request.rally_class)
                            elif endpoint == APIEndpoint.CURRENT_STAGE:
                                response = await self.api_client.get_current_stage_cars(stage_id, rally_class=request.rally_class)
                            elif endpoint == APIEndpoint.ENHANCED_CURRENT:
                                response = await self.api_client.get_enhanced_current_stage(stage_id, rally_class=request.rally_class)
                                
                            # Process data and wait for completion (including CSV export)
                            await self.data_processor.process_response(response)
                            results[f"{endpoint_str}_{stage_id}"] = {"success": response.success, "error": response.error_message}
                    else:
                        # Execute API call
                        if endpoint == APIEndpoint.ENTRY_LIST:
                            response = await self.api_client.get_entry_list(rally_class=request.rally_class)
                        elif endpoint == APIEndpoint.START_LIST:
                            response = await self.api_client.get_start_list(rally_class=request.rally_class)
                        elif endpoint == APIEndpoint.ROUTE_SHEET:
                            response = await self.api_client.get_route_sheet(rally_class=request.rally_class)
                            
                        # Process data and wait for completion (including CSV export)
                        await self.data_processor.process_response(response)
                        results[endpoint_str] = {"success": response.success, "error": response.error_message}
                        
                return {
                    "results": results,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Failed to trigger data update: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self.app
