"""Async API client for HauserResults rally data."""

import asyncio
import aiohttp
import logging
from typing import Optional, List, Dict
from urllib.parse import urlencode
import csv
from io import StringIO

from .config import settings
from .models import APIEndpoint, APIResponse, RallyClass


logger = logging.getLogger(__name__)


class HauserResultsAPIClient:
    """Async client for HauserResults API."""
    
    def __init__(self):
        """Initialize the API client."""
        self.base_url = settings.api_base_url
        self.error_code = settings.api_error_code
        self.user_agent = settings.user_agent
        self.timeout = settings.request_timeout_seconds
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_session()
        
    async def start_session(self):
        """Start the aiohttp session."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,  # Increase total connection pool size
                limit_per_host=30,  # Allow more concurrent connections per host
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/csv,application/json,text/plain,*/*',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers
            )
            logger.info("HTTP session started")
            
    async def close_session(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("HTTP session closed")
            
    def _build_url(self, endpoint: APIEndpoint, stage_id: Optional[str] = None, rally_class: str = "1", **kwargs) -> str:
        """Build API URL with parameters."""
        params = {
            'oszt': rally_class,  # Class parameter (default to "1" if not specified)
            'error': self.error_code,
            'a': endpoint.value,
            'noform': '1',
            'csv': '1'  # Request CSV format
        }
        
        # Add stage ID if provided
        if stage_id:
            params['s'] = stage_id
            
        # Add any additional parameters
        params.update(kwargs)
        
        query_string = urlencode(params)
        url = f"{self.base_url}?{query_string}"
        logger.debug(f"Built URL: {url}")
        return url
        
    async def _make_request(self, url: str) -> str:
        """Make HTTP request and return response text."""
        if not self.session or self.session.closed:
            await self.start_session()
            
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                content = await response.text(encoding='utf-8')
                logger.debug(f"API response received: {len(content)} characters")
                return content
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during request: {e}")
            raise
            
    def _parse_csv_to_2d_array(self, csv_content: str) -> List[List[str]]:
        """Parse CSV response into a 2D array (list of lists)."""
        try:
            if csv_content.startswith('\ufeff'):
                csv_content = csv_content[1:]
                
            reader = csv.reader(StringIO(csv_content))
            raw_data = list(reader)
            
            data = [row for row in raw_data if any(cell.strip() for cell in row)]
            
            logger.debug(f"Removed {len(raw_data) - len(data)} empty rows")
                    
            logger.debug(f"Parsed {len(data)} rows from CSV (including headers)")
            return data
            
        except Exception as e:
            logger.error(f"Failed to parse CSV response: {e}")
            raise
            
    async def get_entry_list(self, rally_class: str = "1") -> APIResponse:
        """Get entry list (a=8) - detailed participant data."""
        try:
            url = self._build_url(APIEndpoint.ENTRY_LIST, rally_class=rally_class)
            content = await self._make_request(url)
            data = self._parse_csv_to_2d_array(content)
            
            return APIResponse(
                endpoint=APIEndpoint.ENTRY_LIST,
                rally_class=rally_class,
                data=data,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Failed to get entry list: {e}")
            return APIResponse(
                endpoint=APIEndpoint.ENTRY_LIST,
                rally_class=rally_class,
                data=[],
                success=False,
                error_message=str(e)
            )
            
    async def get_start_list(self, rally_class: str = "1") -> APIResponse:
        """Get start list (a=9) - starting order."""
        try:
            url = self._build_url(APIEndpoint.START_LIST, rally_class=rally_class)
            content = await self._make_request(url)
            data = self._parse_csv_to_2d_array(content)
            
            return APIResponse(
                endpoint=APIEndpoint.START_LIST,
                rally_class=rally_class,
                data=data,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Failed to get start list: {e}")
            return APIResponse(
                endpoint=APIEndpoint.START_LIST,
                rally_class=rally_class,
                data=[],
                success=False,
                error_message=str(e)
            )
            
    async def get_route_sheet(self, rally_class: str = "1") -> APIResponse:
        """Get route sheet (a=10) - stage information."""
        try:
            url = self._build_url(APIEndpoint.ROUTE_SHEET, rally_class=rally_class)
            content = await self._make_request(url)
            data = self._parse_csv_to_2d_array(content)
            
            return APIResponse(
                endpoint=APIEndpoint.ROUTE_SHEET,
                rally_class=rally_class,
                data=data,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Failed to get route sheet: {e}")
            return APIResponse(
                endpoint=APIEndpoint.ROUTE_SHEET,
                rally_class=rally_class,
                data=[],
                success=False,
                error_message=str(e)
            )
            
    async def get_stage_results(self, stage_id: str, rally_class: str = "1") -> APIResponse:
        """Get detailed stage results (a=3)."""
        try:
            url = self._build_url(APIEndpoint.STAGE_RESULTS, stage_id=stage_id, rally_class=rally_class)
            content = await self._make_request(url)
            data = self._parse_csv_to_2d_array(content)
            
            return APIResponse(
                endpoint=APIEndpoint.STAGE_RESULTS,
                stage_id=stage_id,
                rally_class=rally_class,
                data=data,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Failed to get stage results for stage {stage_id}: {e}")
            return APIResponse(
                endpoint=APIEndpoint.STAGE_RESULTS,
                stage_id=stage_id,
                rally_class=rally_class,
                data=[],
                success=False,
                error_message=str(e)
            )
            
    async def get_current_stage_cars(self, stage_id: str, rally_class: str = "1") -> APIResponse:
        """Get cars currently on stage (a=4)."""
        try:
            url = self._build_url(APIEndpoint.CURRENT_STAGE, stage_id=stage_id, rally_class=rally_class)
            content = await self._make_request(url)
            data = self._parse_csv_to_2d_array(content)
            
            return APIResponse(
                endpoint=APIEndpoint.CURRENT_STAGE,
                stage_id=stage_id,
                rally_class=rally_class,
                data=data,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Failed to get current stage cars for stage {stage_id}: {e}")
            return APIResponse(
                endpoint=APIEndpoint.CURRENT_STAGE,
                stage_id=stage_id,
                rally_class=rally_class,
                data=[],
                success=False,
                error_message=str(e)
            )
            
    async def get_enhanced_current_stage(self, stage_id: str, rally_class: str = "1") -> APIResponse:
        """Get enhanced current stage data with GPS (a=104)."""
        try:
            url = self._build_url(APIEndpoint.ENHANCED_CURRENT, stage_id=stage_id, rally_class=rally_class)
            content = await self._make_request(url)
            data = self._parse_csv_to_2d_array(content)
            
            return APIResponse(
                endpoint=APIEndpoint.ENHANCED_CURRENT,
                stage_id=stage_id,
                rally_class=rally_class,
                data=data,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Failed to get enhanced current stage data for stage {stage_id}: {e}")
            return APIResponse(
                endpoint=APIEndpoint.ENHANCED_CURRENT,
                stage_id=stage_id,
                rally_class=rally_class,
                data=[],
                success=False,
                error_message=str(e)
            )
            
    async def get_all_stage_data(self, stage_id: str) -> Dict[str, APIResponse]:
        """Get all data for a specific stage concurrently."""
        tasks = {
            'stage_results': self.get_stage_results(stage_id),
            'current_cars': self.get_current_stage_cars(stage_id),
            'enhanced_current': self.get_enhanced_current_stage(stage_id)
        }
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        response_dict = {}
        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get {key} for stage {stage_id}: {result}")
                response_dict[key] = APIResponse(
                    endpoint=getattr(APIEndpoint, key.upper(), APIEndpoint.STAGE_RESULTS),
                    stage_id=stage_id,
                    data=[],
                    success=False,
                    error_message=str(result)
                )
            else:
                response_dict[key] = result
                
        return response_dict
        
    async def get_basic_data(self) -> Dict[str, APIResponse]:
        """Get basic rally data (entry list, start list, route sheet) concurrently."""
        tasks = {
            'entry_list': self.get_entry_list(),
            'start_list': self.get_start_list(),
            'route_sheet': self.get_route_sheet()
        }
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        response_dict = {}
        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get {key}: {result}")
                # Create appropriate endpoint enum
                endpoint_map = {
                    'entry_list': APIEndpoint.ENTRY_LIST,
                    'start_list': APIEndpoint.START_LIST,
                    'route_sheet': APIEndpoint.ROUTE_SHEET
                }
                response_dict[key] = APIResponse(
                    endpoint=endpoint_map[key],
                    data=[],
                    success=False,
                    error_message=str(result)
                )
            else:
                response_dict[key] = result
                
        return response_dict
