"""Container (Docker) test runner — STUB.

This is the integration point for real execution. It conforms to the TestRunner
interface so it can replace SimulatedRunner without touching the execution flow.

To implement a live run, fill in `run()` to, for each case with scripts:
  1. Materialize the script(s) + a config/scaffold into a temp working directory.
  2. Pick the runner image for the framework (e.g. settings.execution_container_image
     for Playwright) and start a container with the working dir mounted, constrained by
     settings.execution_cpu_limit / execution_memory_limit / execution_timeout_default
     and settings.execution_network_mode.
  3. Run the framework command (`playwright test`, `pytest`, `cypress run`, `robot`, …),
     capture stdout/stderr and the exit code.
  4. Map exit code → status (0 → passed, non-zero → failed), collect artifacts
     (screenshots, videos, traces) into settings.execution_artifacts_dir, and return a
     CaseResult per case.

Until implemented, `run()` raises NotImplementedError; the execution service catches it
and falls back to the simulated runner so runs never fail.
"""

from app.services.runners.base import RunnerRequest, RunnerResult, TestRunner


class DockerRunner(TestRunner):
    name = "docker"

    async def run(self, request: RunnerRequest) -> RunnerResult:
        raise NotImplementedError(
            "DockerRunner is not implemented yet. "
            "Set EXECUTION_RUNNER=simulated (default), or implement container execution "
            "in app/services/runners/docker_runner.py."
        )
