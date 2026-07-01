"""Runner selection — vendor-neutral, configured via settings.execution_runner."""

from app.core.config import settings
from app.services.runners.base import TestRunner
from app.services.runners.simulated import SimulatedRunner


def get_runner() -> TestRunner:
    """Return the configured test runner. Defaults to the simulated runner."""
    if settings.execution_runner == "docker":
        from app.services.runners.docker_runner import DockerRunner

        return DockerRunner()
    return SimulatedRunner()
