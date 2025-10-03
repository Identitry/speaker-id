"""Common Pydantic schemas used across the API.

These models are intentionally small and stable so that both the FastAPI
endpoints and the web UI can rely on a consistent JSON shape.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class StatusOK(BaseModel):
    """Simple OK response used by health checks."""

    status: str = Field("ok", description="Health status string")


class Message(BaseModel):
    """A generic message wrapper."""

    ok: bool = Field(True, description="Operation succeeded")
    message: Optional[str] = Field(None, description="Optional human text")


class EnrollResponse(BaseModel):
    """Response returned by the /enroll endpoint."""

    ok: bool = Field(True, description="Enrollment succeeded")
    name: str = Field(..., description="User name that was enrolled")


class ErrorResponse(BaseModel):
    """Standard error envelope for 4xx/5xx paths when needed."""

    ok: bool = Field(False, description="Always false for errors")
    detail: str = Field(..., description="Reason for the error")
