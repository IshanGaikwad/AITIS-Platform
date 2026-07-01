"""
AITIS Playwright Execution Container — Python Runner Utilities.

Provides:
  - Result summarization from Playwright JSON output
  - Artifact collection and metadata generation
  - Exit code interpretation
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone


def summarize_results(results_file: str, exit_code: int, output: str) -> None:
    """Read Playwright JSON reporter output and produce a summary."""
    results_path = Path(results_file)
    summary = {
        "status": "passed" if exit_code == 0 else "failed",
        "exit_code": exit_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "timed_out": 0,
        "flaky": 0,
        "duration_ms": 0,
        "tests": [],
    }

    if not results_path.exists():
        summary["status"] = "error"
        summary["error"] = f"Results file not found: {results_file}"
        _write_json(output, summary)
        return

    try:
        data = json.loads(results_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        summary["status"] = "error"
        summary["error"] = f"Failed to parse results: {exc}"
        _write_json(output, summary)
        return

    # Playwright JSON reporter structure
    # { "config": {...}, "suites": [...], "stats": {...} }
    suites = data.get("suites", [])
    _extract_tests(suites, summary)

    # Override stats from Playwright reporter if available
    stats = data.get("stats", {})
    if stats:
        summary["duration_ms"] = stats.get("duration", summary["duration_ms"])

    _write_json(output, summary)


def _extract_tests(suites: list, summary: dict) -> None:
    """Recursively extract test results from Playwright suite structure."""
    for suite in suites:
        for test in suite.get("tests", []):
            test_info = {
                "title": test.get("title", "Unknown"),
                "file": test.get("file", ""),
                "duration_ms": test.get("duration", 0),
                "status": "unknown",
                "retries": test.get("retry", 0),
                "annotations": test.get("annotations", []),
            }

            # Determine test status from results
            results = test.get("results", [])
            if results:
                last_result = results[-1]
                status = last_result.get("status", "unknown")
                test_info["status"] = status
                test_info["error"] = last_result.get("error", {}).get("message")

                if status == "passed":
                    summary["passed"] += 1
                elif status == "failed":
                    summary["failed"] += 1
                elif status == "timedOut":
                    summary["timed_out"] += 1
                elif status == "skipped":
                    summary["skipped"] += 1

                # Check if flaky (passed after retry)
                if len(results) > 1 and status == "passed":
                    summary["flaky"] += 1
                    test_info["flaky"] = True

            summary["total_tests"] += 1
            summary["tests"].append(test_info)

        # Recurse into nested suites
        _extract_tests(suite.get("suites", []), summary)


def _write_json(path: str, data: dict) -> None:
    """Write JSON data to file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def collect_artifacts(artifacts_dir: str) -> list:
    """Scan artifacts directory and return metadata for each file."""
    artifacts = []
    artifacts_path = Path(artifacts_dir)

    if not artifacts_path.exists():
        return artifacts

    for file_path in artifacts_path.rglob("*"):
        if file_path.is_file():
            stat = file_path.stat()
            artifacts.append({
                "name": file_path.name,
                "relative_path": str(file_path.relative_to(artifacts_path)),
                "size_bytes": stat.st_size,
                "content_type": _guess_content_type(file_path),
            })

    return artifacts


def _guess_content_type(path: Path) -> str:
    """Guess content type from file extension."""
    ext = path.suffix.lower()
    content_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".json": "application/json",
        ".html": "text/html",
        ".txt": "text/plain",
        ".log": "text/plain",
        ".zip": "application/zip",
        ".trace": "application/octet-stream",
        ".har": "application/json",
    }
    return content_types.get(ext, "application/octet-stream")


def main():
    parser = argparse.ArgumentParser(description="AITIS Playwright Runner Utilities")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Summarize command
    summarize_parser = subparsers.add_parser("summarize", help="Summarize Playwright results")
    summarize_parser.add_argument("--results-file", required=True, help="Path to Playwright JSON results")
    summarize_parser.add_argument("--exit-code", type=int, default=0, help="Test process exit code")
    summarize_parser.add_argument("--output", required=True, help="Output summary JSON path")

    # Artifacts command
    artifacts_parser = subparsers.add_parser("artifacts", help="Collect artifact metadata")
    artifacts_parser.add_argument("--artifacts-dir", required=True, help="Path to artifacts directory")
    artifacts_parser.add_argument("--output", required=True, help="Output metadata JSON path")

    args = parser.parse_args()

    if args.command == "summarize":
        summarize_results(args.results_file, args.exit_code, args.output)
    elif args.command == "artifacts":
        artifacts = collect_artifacts(args.artifacts_dir)
        _write_json(args.output, {"artifacts": artifacts})
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
