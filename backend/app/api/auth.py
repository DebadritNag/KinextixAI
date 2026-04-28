"""Mock authentication API endpoints.

Requirements: 15.1, 15.2
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from app.models.api import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _envelope(data: object) -> dict:
    """Wrap response data in the standard ApiEnvelope format."""
    return {
        "status": "success",
        "data": data,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/login")
async def login(request: LoginRequest):
    """Mock login — accepts any credentials and returns a token."""
    return _envelope({
        "token": str(uuid4()),
        "user": {
            "username": request.username,
            "role": "operator",
        },
    })


@router.post("/logout")
async def logout():
    """Mock logout — returns a simple success status."""
    return _envelope({"message": "Logged out successfully"})
