"""Main application entry point."""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, List, Any

import uvicorn

from .api_client import HauserResultsAPIClient
from .data_store import RallyDataProcessor
from .http_handler import RallyHTTPHandler
from . import csv_exporter
from .config import settings
from .models import APIEndpoint


# Configure logging
def setup_logging():
    """Set up logging configuration with proper Unicode support."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Create output directory for logs
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
    # Set up handlers with UTF-8 encoding
    handlers = []
    
    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d - %(levelname)s - %(filename)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    handlers.append(console_handler)
    
    # File handler with UTF-8 encoding if specified
    if settings.log_file:
        file_handler = logging.FileHandler(settings.log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d - %(levelname)s - %(filename)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        handlers.append(file_handler)
        
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    # Set specific logger levels
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    

logger = logging.getLogger(__name__)


class RallyDataApplication:
    """Main application class."""
    
    def __init__(self):
        """Initialize the application."""
        self.api_client: HauserResultsAPIClient = None
        self.data_processor: RallyDataProcessor = None
        self.http_handler: RallyHTTPHandler = None
        self.running = False
        
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing Rally Data Application")
        
        # Initialize components
        self.api_client = HauserResultsAPIClient()
        self.data_processor = RallyDataProcessor()
        self.http_handler = RallyHTTPHandler(
            self.api_client,
            self.data_processor
        )
        
        # Set up automatic CSV export callbacks
        self._setup_export_callbacks()
        
        # Start API client session
        await self.api_client.start_session()
        
        logger.info("Application initialized successfully")
        
    def _setup_export_callbacks(self):
        """Set up automatic CSV and Excel export callbacks for all data types."""
        # Create and register callbacks for each endpoint using enum properties
        for endpoint in APIEndpoint:
            callback = self._create_export_callback(endpoint)
            self.data_processor.add_callback(endpoint, callback)
        
        enabled_exports = []
        if settings.csv_export_enabled:
            enabled_exports.append("CSV")
        if settings.excel_export_enabled:
            enabled_exports.append("Excel")
            
        logger.info(f"Set up automatic export callbacks for all endpoints: {', '.join(enabled_exports) if enabled_exports else 'None'}")
        
    def _create_export_callback(self, endpoint: APIEndpoint):
        """Create an export callback function for the given endpoint."""
        async def export_callback(data, stage_id=None):
            # Handle CSV export
            if settings.csv_export_enabled:
                csv_filename = endpoint.get_csv_filename_with_stage(stage_id)
                await csv_exporter.export_to_csv(data, csv_filename)
            
            # Handle Excel export
            if settings.excel_export_enabled:
                excel_sheet = endpoint.get_excel_sheet_with_stage(stage_id)
                await csv_exporter.export_to_excel_sheet(data, excel_sheet)
        
        return export_callback
        
    async def start(self):
        """Start the application."""
        if self.running:
            logger.warning("Application is already running")
            return
            
        try:
            await self.initialize()
            
            self.running = True
            logger.info("Rally Data Application started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            await self.shutdown()
            raise
            
            
    async def shutdown(self):
        """Shutdown the application."""
        if not self.running:
            return
            
        logger.info("Shutting down Rally Data Application")
        
        try:
            # Close API client session
            if self.api_client:
                await self.api_client.close_session()
                
            self.running = False
            logger.info("Application shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
    def get_app(self):
        """Get FastAPI application instance."""
        if not self.http_handler:
            raise RuntimeError("Application not initialized")
        return self.http_handler.get_app()


# Global application instance
app_instance = RallyDataApplication()


async def lifespan(app):
    """FastAPI lifespan context manager."""
    # Startup
    await app_instance.start()
    
    yield
    
    # Shutdown
    await app_instance.shutdown()


def create_app():
    """Create FastAPI application with lifespan."""
    from fastapi import FastAPI
    
    # Create a wrapper app with lifespan
    wrapper_app = FastAPI(lifespan=lifespan)
    
    # This will be replaced with the actual app after initialization
    return wrapper_app


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    asyncio.create_task(app_instance.shutdown())


async def main():
    """Main entry point for running the application."""
    setup_logging()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the application
        await app_instance.start()
        
        # Get the FastAPI app
        app = app_instance.get_app()
        
        # Run the HTTP server
        config = uvicorn.Config(
            app=app,
            host=settings.http_server_host,
            port=settings.http_server_port,
            log_level=settings.log_level.lower(),
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        logger.info(f"Starting HTTP server on {settings.http_server_host}:{settings.http_server_port}")
        
        # Run server
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
    finally:
        await app_instance.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
