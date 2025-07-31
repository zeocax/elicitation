"""HITL Client for tools to request user input"""

import os
import aiohttp
from typing import Optional, Any, List, Dict
from .models import HITLRequest, HITLResponse, RequestType


class HITLClient:
    """Client for interacting with HITL server via HTTP"""
    
    def __init__(self, server_url: Optional[str] = None):
        """Initialize HITL client
        
        Args:
            server_url: URL of HITL server. If not provided, uses HITL_SERVER_URL env var
                       or defaults to http://localhost:8765
        """
        self.server_url = server_url or os.environ.get(
            "HITL_SERVER_URL", 
            "http://localhost:8765"
        )
        self.enabled = os.environ.get("HITL_ENABLED", "true").lower() == "true"
        self.default_timeout = int(os.environ.get("HITL_TIMEOUT", "300"))
    
    async def _make_request(self, request: HITLRequest) -> HITLResponse:
        """Make request to HITL server"""
        if not self.enabled:
            # If HITL is disabled, return a default response
            return HITLResponse(
                request_id=request.id,
                success=True,
                value=None if request.type == RequestType.FEEDBACK else True
            )
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.server_url}/request",
                    json=request.to_dict(),
                    timeout=aiohttp.ClientTimeout(total=request.timeout + 10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return HITLResponse.from_dict(data)
                    else:
                        error_text = await resp.text()
                        return HITLResponse(
                            request_id=request.id,
                            success=False,
                            error=f"Server error: {resp.status} - {error_text}"
                        )
            except aiohttp.ClientError as e:
                return HITLResponse(
                    request_id=request.id,
                    success=False,
                    error=f"Connection error: {str(e)}"
                )
            except Exception as e:
                return HITLResponse(
                    request_id=request.id,
                    success=False,
                    error=f"Unexpected error: {str(e)}"
                )
    
    async def request_feedback(
        self,
        prompt: str,
        tool_name: str = "",
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Optional[str]:
        """Request feedback from user
        
        Args:
            prompt: The prompt to show to user
            tool_name: Name of the tool making the request
            context: Optional context information
            timeout: Timeout in seconds (uses default if not specified)
            
        Returns:
            User feedback string or None if failed/cancelled
        """
        request = HITLRequest(
            type=RequestType.FEEDBACK,
            prompt=prompt,
            tool_name=tool_name,
            context=context,
            timeout=timeout or self.default_timeout
        )
        
        response = await self._make_request(request)
        if response.success:
            return response.value
        return None
    
    async def notify(
        self,
        message: str,
        tool_name: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification to user without requiring feedback
        
        Args:
            message: The message to show to user
            tool_name: Name of the tool making the request
            context: Optional context information
            
        Returns:
            True if notification was sent successfully
        """
        request = HITLRequest(
            type=RequestType.NOTIFY,
            prompt=message,
            tool_name=tool_name,
            context=context,
            timeout=0  # No timeout for notifications
        )
        
        response = await self._make_request(request)
        return response.success