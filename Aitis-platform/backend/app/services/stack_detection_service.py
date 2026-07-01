"""Stack detection — fetch a candidate System Under Test URL and ask the configured
AI provider to infer its technology stack from the response.

Security note: the URL comes directly from a user, and this service fetches it from
the server, so it is a textbook SSRF surface. ``validate_target_url`` resolves the
hostname and rejects anything pointing at loopback/private/link-local/reserved
address space (including the 169.254.169.254 cloud metadata endpoint) before any
request is made, and redirects are followed manually so every hop is re-validated.
"""

import ipaddress
import json
import logging
import socket
from typing import List, Optional
from urllib.parse import urlparse, urljoin

import httpx
from pydantic import BaseModel, Field

from app.services.ai.factory import get_ai_provider

logger = logging.getLogger("aitis.stack_detection")

FETCH_TIMEOUT_SECONDS = 8.0
MAX_RESPONSE_BYTES = 500_000
MAX_REDIRECTS = 5
MAX_HTML_CHARS_FOR_AI = 12_000


class StackDetectionError(ValueError):
    """Raised when a URL can't be validated or fetched."""


class StackDetectionResult(BaseModel):
    frontend_framework: Optional[str] = Field(None, description="e.g. React, Angular, Vue, Next.js, plain HTML")
    backend_hints: Optional[str] = Field(None, description="Server/runtime hints inferred from headers, e.g. nginx, Express, Django")
    language: Optional[str] = Field(None, description="Primary language guess, e.g. JavaScript, Python, Ruby")
    css_framework: Optional[str] = Field(None, description="e.g. Tailwind, Bootstrap, Material UI, none detected")
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    summary: str = ""
    suggested_application_type: str = Field("WEB", description="WEB | MOBILE_WEB | ANDROID | IOS | HYBRID")
    page_title: Optional[str] = None
    final_url: str
    http_status: Optional[int] = None


def validate_target_url(url: str) -> httpx.URL:
    """Parse + validate a user-supplied URL. Raises StackDetectionError if unsafe."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise StackDetectionError("URL must use http or https.")
    if not parsed.hostname:
        raise StackDetectionError("URL must include a hostname.")

    try:
        addr_infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise StackDetectionError(f"Could not resolve host '{parsed.hostname}'.") from exc

    for info in addr_infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise StackDetectionError(
                "URL resolves to a private, loopback, or link-local address and cannot be analyzed."
            )

    return httpx.URL(url)


async def _fetch(url: str) -> tuple[str, dict, int, str]:
    """Fetch a URL, manually following redirects so every hop is re-validated.

    Returns (html, headers_dict, status_code, final_url).
    """
    current = str(validate_target_url(url))
    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            try:
                resp = await client.get(
                    current,
                    headers={"User-Agent": "AITIS-StackDetector/1.0"},
                )
            except httpx.HTTPError as exc:
                raise StackDetectionError(f"Failed to fetch URL: {exc}") from exc

            if resp.is_redirect:
                location = resp.headers.get("location")
                if not location:
                    break
                current = str(validate_target_url(urljoin(current, location)))
                continue

            body = resp.text[:MAX_RESPONSE_BYTES]
            return body, dict(resp.headers), resp.status_code, current

        raise StackDetectionError("Too many redirects.")


def _extract_title(html: str) -> Optional[str]:
    lower = html.lower()
    start = lower.find("<title")
    if start == -1:
        return None
    start = lower.find(">", start)
    end = lower.find("</title>", start)
    if start == -1 or end == -1:
        return None
    return html[start + 1 : end].strip()[:200]


def _signal_summary(html: str, headers: dict) -> str:
    """Cheap, deterministic signals to ground the AI prompt (and to use verbatim
    in the mock-provider fallback when no AI key is configured)."""
    lower = html.lower()
    signals: List[str] = []
    checks = {
        "react": ["data-reactroot", "react-dom", "_next/static", "__next"],
        "angular": ["ng-version", "ng-app", "angular"],
        "vue": ["data-v-", "__vue__", "vue.js", "vue.global"],
        "svelte": ["svelte-"],
        "wordpress": ["wp-content", "wp-includes"],
        "tailwind": ["tailwind"],
        "bootstrap": ["bootstrap"],
    }
    for label, needles in checks.items():
        if any(n in lower for n in needles):
            signals.append(label)

    server = headers.get("server") or headers.get("Server")
    powered_by = headers.get("x-powered-by") or headers.get("X-Powered-By")
    if server:
        signals.append(f"server header: {server}")
    if powered_by:
        signals.append(f"x-powered-by: {powered_by}")

    return ", ".join(signals) if signals else "no strong signature detected"


async def detect_stack(url: str) -> StackDetectionResult:
    """Fetch ``url`` and ask the configured AI provider to infer its tech stack."""
    html, headers, status_code, final_url = await _fetch(url)
    title = _extract_title(html)
    signals = _signal_summary(html, headers)

    truncated_html = html[:MAX_HTML_CHARS_FOR_AI]
    prompt = (
        f"URL: {final_url}\n"
        f"HTTP status: {status_code}\n"
        f"Page title: {title or 'unknown'}\n"
        f"Response headers: {json.dumps(headers, default=str)[:1500]}\n"
        f"Heuristic signals already detected: {signals}\n\n"
        f"HTML (truncated):\n{truncated_html}"
    )
    system_instruction = (
        "You are a senior QA automation engineer analyzing a web application before "
        "writing automated tests for it. Given a fetched page's HTML, HTTP headers, and "
        "heuristic signals, infer its technology stack. Respond ONLY with a JSON object "
        "matching this shape: {\"frontend_framework\": string|null, \"backend_hints\": "
        "string|null, \"language\": string|null, \"css_framework\": string|null, "
        "\"confidence\": number between 0 and 1, \"summary\": string (1-2 sentences), "
        "\"suggested_application_type\": one of WEB, MOBILE_WEB, ANDROID, IOS, HYBRID}. "
        "Be honest about uncertainty — use a low confidence value when signals are weak."
    )

    provider = get_ai_provider()
    response = await provider.generate_structured_data(
        prompt=prompt,
        system_instruction=system_instruction,
        response_model=StackDetectionResult,
        temperature=0.1,
    )

    try:
        parsed = json.loads(response.content)
    except (json.JSONDecodeError, TypeError):
        parsed = {}

    return StackDetectionResult(
        frontend_framework=parsed.get("frontend_framework"),
        backend_hints=parsed.get("backend_hints"),
        language=parsed.get("language"),
        css_framework=parsed.get("css_framework"),
        confidence=float(parsed.get("confidence") or 0.0),
        summary=parsed.get("summary") or f"Detected via heuristics: {signals}",
        suggested_application_type=parsed.get("suggested_application_type") or "WEB",
        page_title=title,
        final_url=final_url,
        http_status=status_code,
    )
