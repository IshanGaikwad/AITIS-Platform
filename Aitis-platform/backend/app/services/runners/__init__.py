"""Pluggable test runners — simulated (default) or container-based (stub)."""

from app.services.runners.base import (
    CaseResult,
    RunnerCase,
    RunnerRequest,
    RunnerResult,
    RunnerScript,
    TestRunner,
)
from app.services.runners.factory import get_runner

__all__ = [
    "TestRunner",
    "RunnerScript",
    "RunnerCase",
    "RunnerRequest",
    "RunnerResult",
    "CaseResult",
    "get_runner",
]
