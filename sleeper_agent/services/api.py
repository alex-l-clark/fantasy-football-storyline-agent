"""HTTP API client for Sleeper API."""

import asyncio
from typing import Any, Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result
)
from rich.console import Console

console = Console()


class SleeperAPIError(Exception):
    """Exception raised for Sleeper API errors."""
    
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class SleeperAPIClient:
    """HTTP client for Sleeper API with retry logic."""
    
    BASE_URL = "https://api.sleeper.app/v1"
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    def _should_retry(self, response: httpx.Response) -> bool:
        """Check if response should be retried."""
        return response.status_code in [429, 500, 502, 503, 504]
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=(
            retry_if_exception_type(httpx.RequestError) |
            retry_if_result(lambda r: isinstance(r, httpx.Response) and r.status_code in [429, 500, 502, 503, 504])
        )
    )
    async def _make_request(self, url: str, params: Optional[dict] = None) -> httpx.Response:
        """Make HTTP request with retry logic."""
        try:
            response = await self.client.get(url, params=params)
            
            if self._should_retry(response):
                console.print(f"[yellow]Retrying request to {url} (status: {response.status_code})[/yellow]")
                return response  # Will be retried
            
            if response.status_code == 404:
                raise SleeperAPIError(404, f"Resource not found: {url}")
            elif response.status_code >= 400:
                raise SleeperAPIError(response.status_code, f"HTTP {response.status_code}")
            
            return response
            
        except httpx.RequestError as e:
            console.print(f"[red]Request error: {e}[/red]")
            raise
    
    async def get_json(self, endpoint: str, *, params: Optional[dict] = None) -> Any:
        """Get JSON data from API endpoint."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            response = await self._make_request(url, params)
            
            try:
                return response.json()
            except ValueError as e:
                raise SleeperAPIError(response.status_code, f"Invalid JSON response: {e}")
                
        except SleeperAPIError:
            raise
        except Exception as e:
            raise SleeperAPIError(500, f"Unexpected error: {e}")


# Synchronous wrapper for convenience
def get_json(endpoint: str, *, params: Optional[dict] = None) -> Any:
    """Synchronous wrapper for API calls."""
    async def _get():
        async with SleeperAPIClient() as client:
            return await client.get_json(endpoint, params=params)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_get())