

"""Identify endpoint request/response models.

Kept separate from common models because this schema may evolve (e.g.,
additional telemetry, diarization metadata, calibration hints).
"""
from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class TopCandidate(BaseModel):
    """One of the top-K nearest candidates from Qdrant search."""

    name: str = Field(..., description="Candidate speaker name")
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity score in [0..1], higher is better"
    )


class IdentifyResult(BaseModel):
    """Response model for /identify endpoint."""

    speaker: str = Field(
        ..., description="Predicted speaker name, or 'unknown' if below threshold"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence for the predicted speaker"
    )
    topN: List[TopCandidate] = Field(
        default_factory=list, description="Top-K candidates for inspection"
    )
