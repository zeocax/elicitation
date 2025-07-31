"""Data models for Human in the Loop interactions"""

from enum import Enum
from typing import Optional, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime
import uuid


def clean_unicode_string(value: Any) -> Any:
    """Clean Unicode surrogates from strings that might cause encoding errors"""
    if isinstance(value, str):
        return value.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    elif isinstance(value, dict):
        return {k: clean_unicode_string(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [clean_unicode_string(item) for item in value]
    else:
        return value


class RequestType(Enum):
    """Types of HITL requests"""
    FEEDBACK = "feedback"    # Request feedback from user
    NOTIFY = "notify"        # Notify user without requiring feedback


@dataclass
class HITLRequest:
    """Request sent from tool to HITL server"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: RequestType = RequestType.FEEDBACK
    prompt: str = ""
    tool_name: str = ""
    context: Optional[Dict[str, Any]] = None
    timeout: int = 300  # Timeout in seconds
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "type": self.type.value,
            "prompt": clean_unicode_string(self.prompt),
            "tool_name": self.tool_name,
            "context": clean_unicode_string(self.context),
            "timeout": self.timeout,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HITLRequest':
        """Create from dictionary"""
        data = data.copy()
        if "type" in data:
            data["type"] = RequestType(data["type"])
        if "created_at" in data:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        # Only keep fields that are defined in the dataclass
        valid_fields = {"id", "type", "prompt", "tool_name", "context", "timeout", "created_at"}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)


@dataclass
class HITLResponse:
    """Response sent from user back to tool"""
    request_id: str
    success: bool = True
    value: Optional[Any] = None
    error: Optional[str] = None
    responded_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "request_id": self.request_id,
            "success": self.success,
            "value": clean_unicode_string(self.value),
            "error": clean_unicode_string(self.error),
            "responded_at": self.responded_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HITLResponse':
        """Create from dictionary"""
        data = data.copy()
        if "responded_at" in data:
            data["responded_at"] = datetime.fromisoformat(data["responded_at"])
        
        # Only keep fields that are defined in the dataclass
        valid_fields = {"request_id", "success", "value", "error", "responded_at"}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)


@dataclass
class PendingRequest:
    """Internal model for tracking pending requests in server"""
    request: HITLRequest
    response_future: Any  # asyncio.Future
    expires_at: datetime