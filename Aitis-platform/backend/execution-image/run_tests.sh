#!/usr/bin/env bash
# ── AITIS Playwright Test Runner ─────────────────────────────────────
# Entry point for the execution container.
# Expects:
#   /workspace/tests/       — Playwright test spec files
#   /workspace/playwright.config.ts — (optional) Playwright config
#   ENV vars: TEST_TIMEOUT, BROWSER, HEADLESS, BASE_URL, etc.
# Produces:
#   /workspace/results/results.json  — Playwright JSON reporter output
#   /workspace/artifacts/            — Screenshots, traces, videos
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

WORKSPACE="/workspace"
TESTS_DIR="${WORKSPACE}/tests"
RESULTS_DIR="${WORKSPACE}/results"
ARTIFACTS_DIR="${WORKSPACE}/artifacts"

# Ensure output directories exist
mkdir -p "${RESULTS_DIR}" "${ARTIFACTS_DIR}"

echo "═══════════════════════════════════════════════════════════════"
echo " AITIS Playwright Execution Container"
echo "═══════════════════════════════════════════════════════════════"
echo " Time:       $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo " Tests dir:  ${TESTS_DIR}"
echo " Results:    ${RESULTS_DIR}/results.json"
echo " Artifacts:  ${ARTIFACTS_DIR}"
echo " Browser:    ${BROWSER:-chromium}"
echo " Headless:   ${HEADLESS:-true}"
echo " Base URL:   ${BASE_URL:-http://localhost:3000}"
echo " Timeout:    ${TEST_TIMEOUT:-30000}ms"
echo "═══════════════════════════════════════════════════════════════"

# Check if tests directory has any test files
if [ -z "$(find "${TESTS_DIR}" -name '*.spec.ts' -o -name '*.test.ts' -o -name '*.spec.js' -o -name '*.test.js' 2>/dev/null | head -1)" ]; then
    echo "ERROR: No test files found in ${TESTS_DIR}"
    echo '{"status":"error","message":"No test files found","results":[]}' > "${RESULTS_DIR}/results.json"
    exit 1
fi

# Build Playwright command
PLAYWRIGHT_CMD="npx playwright test"

# Add reporter flags
PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD} --reporter=json:${RESULTS_DIR}/results.json"

# Add timeout if specified
if [ -n "${TEST_TIMEOUT:-}" ]; then
    PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD} --timeout=${TEST_TIMEOUT}"
fi

# Add retries
if [ -n "${RETRIES:-}" ] && [ "${RETRIES}" -gt 0 ]; then
    PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD} --retries=${RETRIES}"
fi

# Add workers (parallelism)
if [ -n "${WORKERS:-}" ]; then
    PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD} --workers=${WORKERS}"
else
    PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD} --workers=1"
fi

# Add project (browser) if specified
if [ -n "${BROWSER:-}" ] && [ "${BROWSER}" != "chromium" ]; then
    PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD} --project=${BROWSER}"
fi

# Run the tests
echo ""
echo "Running: ${PLAYWRIGHT_CMD}"
echo ""

EXIT_CODE=0
${PLAYWRIGHT_CMD} || EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " Test execution completed with exit code: ${EXIT_CODE}"
echo "═══════════════════════════════════════════════════════════════"

# Copy any Playwright-generated artifacts (screenshots, traces, videos)
if [ -d "${WORKSPACE}/test-results" ]; then
    echo "Copying Playwright artifacts..."
    cp -r "${WORKSPACE}/test-results/"* "${ARTIFACTS_DIR}/" 2>/dev/null || true
fi

# Generate summary
python3 "${WORKSPACE}/runner.py" --summarize \
    --results-file="${RESULTS_DIR}/results.json" \
    --exit-code="${EXIT_CODE}" \
    --output="${RESULTS_DIR}/summary.json" 2>/dev/null || true

echo "Done. Results at ${RESULTS_DIR}/results.json"
exit ${EXIT_CODE}
