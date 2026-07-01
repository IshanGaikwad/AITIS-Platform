"""Test runner interface.

A runner takes a set of test cases (each with its linked automation scripts) and an
environment, executes them, and returns per-case results. Runners are DB-agnostic —
they receive plain data and return plain results; persistence is the caller's job.

This lets the execution flow stay identical whether tests run in a simulation, a local
process, or an isolated container — swap the implementation behind `get_runner()`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Result statuses a runner may report for a single case.
PASSED = "passed"
FAILED = "failed"
SKIPPED = "skipped"
ERROR = "error"


@dataclass
class RunnerScript:
    """One automation artifact to execute."""
    name: str
    framework: str
    language: str
    code: str
    file_path: Optional[str] = None


@dataclass
class RunnerCase:
    """A test case to run, with its linked automation scripts (may be empty)."""
    test_case_id: str
    title: str
    scripts: List[RunnerScript] = field(default_factory=list)


@dataclass
class RunnerRequest:
    """Everything a runner needs for one execution session."""
    execution_id: str
    environment: Optional[str]
    cases: List[RunnerCase] = field(default_factory=list)
    base_url: Optional[str] = None


@dataclass
class CaseResult:
    """Outcome for a single test case."""
    test_case_id: str
    status: str  # passed | failed | skipped | error
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunnerResult:
    """Outcome for a whole execution session."""
    runner: str
    case_results: List[CaseResult] = field(default_factory=list)


class TestRunner(ABC):
    """Abstract execution backend. Implementations execute scripts however they like."""

    name: str = "base"

    @abstractmethod
    async def run(self, request: RunnerRequest) -> RunnerResult:
        """Execute all cases in the request and return per-case results."""
        raise NotImplementedError
