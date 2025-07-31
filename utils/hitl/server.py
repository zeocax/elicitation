"""HITL Server for handling interactive requests from tools"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Optional, List
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import uvicorn

from .models import HITLRequest, HITLResponse, PendingRequest


class HITLServer:
    """Server for managing HITL requests and responses"""
    
    def __init__(self):
        self.pending_requests: Dict[str, PendingRequest] = {}
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self._cleanup_task = None
        
    async def start_cleanup_task(self):
        """Start background task to cleanup expired requests"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self._cleanup_expired_requests()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in cleanup task: {e}")
    
    async def stop_cleanup_task(self):
        """Stop the cleanup background task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def _cleanup_expired_requests(self):
        """Remove expired requests from pending dict"""
        now = datetime.now()
        expired_ids = []
        
        for req_id, pending in self.pending_requests.items():
            if now > pending.expires_at:
                expired_ids.append(req_id)
                # Set error on the future
                if not pending.response_future.done():
                    pending.response_future.set_exception(
                        TimeoutError(f"Request {req_id} timed out")
                    )
        
        # Remove expired requests
        for req_id in expired_ids:
            self.pending_requests.pop(req_id, None)
    
    async def submit_request(self, request: HITLRequest) -> HITLResponse:
        """Submit a request and wait for response"""
        print(f"[DEBUG] submit_request called with request_id: {request.id}")
        
        # Create future for response
        future = asyncio.Future()
        
        # Calculate expiration time
        expires_at = datetime.now() + timedelta(seconds=request.timeout)
        
        # Store pending request
        pending = PendingRequest(
            request=request,
            response_future=future,
            expires_at=expires_at
        )
        self.pending_requests[request.id] = pending
        print(f"[DEBUG] Request {request.id} added to pending requests")
        print(f"[DEBUG] Current pending requests: {list(self.pending_requests.keys())}")
        
        # Add to queue for shell to process
        await self.request_queue.put(request)
        print(f"[DEBUG] Request added to queue")
        
        try:
            # Wait for response with timeout
            print(f"[DEBUG] Waiting for response with timeout: {request.timeout}s")
            response = await asyncio.wait_for(
                future,
                timeout=request.timeout
            )
            print(f"[DEBUG] Got response for request {request.id}")
            return response
        except asyncio.TimeoutError:
            print(f"[ERROR] Request {request.id} timed out after {request.timeout} seconds")
            # Remove from pending if timed out
            self.pending_requests.pop(request.id, None)
            return HITLResponse(
                request_id=request.id,
                success=False,
                error=f"Request timed out after {request.timeout} seconds"
            )
    
    async def get_pending_requests(self) -> List[HITLRequest]:
        """Get list of all pending requests"""
        return [p.request for p in self.pending_requests.values()]
    
    async def get_next_request(self, timeout: Optional[float] = None) -> Optional[HITLRequest]:
        """Get next request from queue (for shell)"""
        try:
            if timeout:
                return await asyncio.wait_for(
                    self.request_queue.get(),
                    timeout=timeout
                )
            else:
                return await self.request_queue.get()
        except asyncio.TimeoutError:
            return None
    
    async def submit_response(self, response: HITLResponse) -> bool:
        """Submit response for a request"""
        print(f"[DEBUG] submit_response called for request_id: {response.request_id}")
        print(f"[DEBUG] Current pending requests: {list(self.pending_requests.keys())}")
        
        pending = self.pending_requests.get(response.request_id)
        if not pending:
            print(f"[ERROR] Request {response.request_id} not found in pending requests")
            print(f"[ERROR] Available request IDs: {list(self.pending_requests.keys())}")
            return False
        
        print(f"[DEBUG] Found pending request, future done: {pending.response_future.done()}")
        
        # Set the response on the future
        if not pending.response_future.done():
            pending.response_future.set_result(response)
            print(f"[DEBUG] Response set on future")
        else:
            print(f"[WARNING] Future already done for request {response.request_id}")
        
        # Remove from pending
        self.pending_requests.pop(response.request_id, None)
        print(f"[DEBUG] Request removed from pending")
        return True


# Global server instance
hitl_server = HITLServer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage server lifecycle"""
    # Startup
    hitl_server._cleanup_task = asyncio.create_task(
        hitl_server.start_cleanup_task()
    )
    yield
    # Shutdown
    await hitl_server.stop_cleanup_task()


# Create FastAPI app
app = FastAPI(
    title="HITL Server",
    description="Human in the Loop server for interactive tool execution",
    lifespan=lifespan
)


@app.post("/request")
async def submit_request(request_data: dict) -> dict:
    """Submit a new HITL request"""
    try:
        request = HITLRequest.from_dict(request_data)
        response = await hitl_server.submit_request(request)
        return response.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/pending")
async def get_pending_requests() -> List[dict]:
    """Get all pending requests"""
    requests = await hitl_server.get_pending_requests()
    return [req.to_dict() for req in requests]


@app.get("/next")
async def get_next_request(timeout: Optional[float] = 30.0) -> Optional[dict]:
    """Get next request from queue (long polling)"""
    request = await hitl_server.get_next_request(timeout)
    if request:
        return request.to_dict()
    return None


@app.post("/response/{request_id}")
async def submit_response(request_id: str, response_data: dict) -> dict:
    """Submit response for a request"""
    try:
        print(f"[DEBUG] Received response for request_id: {request_id}")
        print(f"[DEBUG] Response data: {response_data}")
        
        # Ensure request_id is set
        response_data["request_id"] = request_id
        
        try:
            response = HITLResponse.from_dict(response_data)
            print(f"[DEBUG] Successfully created HITLResponse: {response}")
        except Exception as e:
            print(f"[ERROR] Failed to create HITLResponse from dict: {e}")
            print(f"[ERROR] Response data was: {response_data}")
            raise
        
        success = await hitl_server.submit_response(response)
        if not success:
            print(f"[ERROR] Request {request_id} not found or already responded")
            raise HTTPException(
                status_code=404,
                detail=f"Request {request_id} not found or already responded"
            )
        
        print(f"[DEBUG] Response submitted successfully for request_id: {request_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error in submit_response: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "pending_requests": len(hitl_server.pending_requests)
    }


def run_server(host: str = "0.0.0.0", port: int = 8765):
    """Run the HITL server"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()