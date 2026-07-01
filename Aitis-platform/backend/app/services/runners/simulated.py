"""Simulated test runner.

Records cases with a linked automation script as passed and cases without one as
skipped. There is no real browser/script execution runtime — every result is flagged
`simulated` so it is never mistaken for a live run (see docker_runner.py for the real
execution integration point, currently a stub).

What IS real here: when the execution carries a target `base_url` (resolved from the
workspace's configured Environment), the runner performs one genuine, SSRF-validated
HTTP request against it and reflects actual reachability/status in every case's
result — so a run against a target that's down or misconfigured fails honestly
instead of fabricating a pass.
"""

import logging
import time

import httpx

from app.services.runners.base import (
    ERROR,
    PASSED,
    SKIPPED,
    CaseResult,
    RunnerRequest,
    RunnerResult,
    TestRunner,
)
from app.services.stack_detection_service import StackDetectionError, validate_target_url

logger = logging.getLogger("aitis.runners.simulated")

TARGET_CHECK_TIMEOUT_SECONDS = 8.0


class SimulatedRunner(TestRunner):
    name = "simulated"

    async def run(self, request: RunnerRequest) -> RunnerResult:
        target_check = await self._check_target(request.base_url) if request.base_url else None

        results = []
        for case in request.cases:
            has_automation = bool(case.scripts)
            artifacts = {
                "runner": self.name,
                "simulated": True,
                "scripts": [s.name for s in case.scripts],
                "frameworks": sorted({s.framework for s in case.scripts}),
            }
            if target_check is not None:
                artifacts["target_url"] = request.base_url
                artifacts["target_reachable"] = target_check["reachable"]
                artifacts["target_http_status"] = target_check.get("status")

            if not has_automation:
                status, error = SKIPPED, "No automation script linked to this test case"
            elif target_check is not None and not target_check["reachable"]:
                status, error = ERROR, f"Target unreachable: {target_check['error']}"
            else:
                status, error = PASSED, None

            results.append(
                CaseResult(
                    test_case_id=case.test_case_id,
                    status=status,
                    duration_seconds=target_check.get("duration_seconds", 0.0) if target_check else 0.0,
                    error_message=error,
                    artifacts=artifacts,
                )
            )
        return RunnerResult(runner=self.name, case_results=results)

    @staticmethod
    async def _check_target(base_url: str) -> dict:
        """Make one real, SSRF-validated request to confirm the SUT is actually reachable."""
        start = time.monotonic()
        try:
            validated = validate_target_url(base_url)
        except StackDetectionError as exc:
            return {"reachable": False, "error": str(exc), "duration_seconds": 0.0}

        try:
            async with httpx.AsyncClient(timeout=TARGET_CHECK_TIMEOUT_SECONDS) as client:
                resp = await client.get(str(validated), headers={"User-Agent": "AITIS-Runner/1.0"})
            duration = time.monotonic() - start
            return {
                "reachable": resp.status_code < 500,
                "status": resp.status_code,
                "error": None if resp.status_code < 500 else f"HTTP {resp.status_code}",
                "duration_seconds": duration,
            }
        except httpx.HTTPError as exc:
            return {"reachable": False, "error": str(exc), "duration_seconds": time.monotonic() - start}
