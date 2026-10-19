"""Minimal Ollama chat client for vision analysis."""

import base64
import json
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageChops

_ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}
_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "passed": {"type": "boolean"},
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "issue": {"type": "string"},
                    "location": {"type": "string"},
                    "reasoning": {"type": "string"},
                },
                "required": ["severity", "issue", "location", "reasoning"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["passed", "summary", "findings"],
    "additionalProperties": False,
}


def parse_analysis(content: str) -> dict:
    """Parse and validate the model's JSON response."""
    try:
        result = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError("Ollama returned invalid JSON for the visual analysis.") from error

    if not isinstance(result, dict) or not isinstance(result.get("findings"), list):
        raise ValueError("Analysis must be a JSON object containing a findings list.")
    if not isinstance(result.get("passed"), bool) or not isinstance(result.get("summary"), str):
        raise ValueError("Analysis must include boolean 'passed' and string 'summary' fields.")

    findings = []
    for finding in result["findings"]:
        if not isinstance(finding, dict):
            raise ValueError("Each finding must be a JSON object.")
        severity = finding.get("severity")
        if severity not in _ALLOWED_SEVERITIES:
            raise ValueError(f"Finding severity must be one of: {', '.join(sorted(_ALLOWED_SEVERITIES))}.")
        findings.append(
            {
                "severity": severity,
                "issue": str(finding.get("issue", "Unspecified visual issue")),
                "location": str(finding.get("location", "Not specified")),
                "reasoning": str(finding.get("reasoning", "")),
            }
        )

    if result["passed"] and findings:
        raise ValueError("A passing analysis must not contain findings.")
    if not result["passed"] and not findings:
        raise ValueError("A failing analysis must contain at least one finding.")
    return {"passed": result["passed"], "summary": result["summary"], "findings": findings}


def analyze_screenshots(
    baseline: Path,
    current: Path,
    *,
    model: str,
    ollama_url: str,
) -> dict:
    """Ask a local Ollama vision model to compare two screenshots."""
    with Image.open(baseline) as baseline_image, Image.open(current) as current_image:
        if baseline_image.size == current_image.size:
            difference = ImageChops.difference(
                baseline_image.convert("RGB"),
                current_image.convert("RGB"),
            )
            if difference.getbbox() is None:
                return {
                    "passed": True,
                    "summary": "Screenshots are pixel-identical; no visual regressions detected.",
                    "findings": [],
                }

    prompt = """Act as a careful visual QA engineer. Compare the BASELINE image (first) with the CURRENT image (second).
Report only meaningful regressions in interface structure or usability: missing/added controls, broken or shifted layout, overlapping or clipped content, unreadable text, and major style changes that impair use. Ignore changing text/data, clocks, counters, avatars, ads, and small rendering or anti-aliasing differences unless they cause a real usability problem. Do not infer issues that are not visible. For each finding, give a concise page location using visible landmarks and explain the impact. Return only JSON matching this schema:
{"passed": true, "summary": "...", "findings": [{"severity": "low|medium|high|critical", "issue": "...", "location": "...", "reasoning": "..."}]}
Set passed to false only when at least one meaningful regression is present. If there are none, use an empty findings list."""
    images = [base64.b64encode(path.read_bytes()).decode("ascii") for path in (baseline, current)]
    payload = {
        "model": model,
        "stream": False,
        "format": _ANALYSIS_SCHEMA,
        "messages": [{"role": "user", "content": prompt, "images": images}],
        "options": {"temperature": 0, "num_ctx": 8192},
    }
    endpoint = f"{ollama_url.rstrip('/')}/api/chat"
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=300) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except OSError as error:
        raise RuntimeError(f"Could not reach Ollama at {endpoint}: {error}") from error

    try:
        content = response_data["message"]["content"]
    except (KeyError, TypeError) as error:
        raise ValueError("Ollama response did not contain message content.") from error
    return parse_analysis(content)
