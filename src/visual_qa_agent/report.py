"""Structured report generation."""

from __future__ import annotations

import json
from pathlib import Path


def write_scenario_reports(
    scenario: str,
    model: str,
    checkpoints: list[dict],
    markdown_path: Path,
    json_path: Path,
    *,
    injected_defect: str | None = None,
) -> dict:
    """Write one Markdown and JSON report for all scenario checkpoints."""
    result = {
        "scenario": scenario,
        "model": model,
        "passed": all(checkpoint["passed"] for checkpoint in checkpoints),
        "injected_defect": injected_defect,
        "checkpoints": checkpoints,
    }
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    status = "PASS" if result["passed"] else "FAIL"
    lines = [
        f"# Visual QA Scenario: {status}",
        "",
        f"**Scenario:** `{scenario}`",
        f"**Model:** `{model}`",
    ]
    if injected_defect:
        lines.append(f"**Injected visual defect:** `{injected_defect}`")
    lines.extend(["", "## Checkpoints"])

    for checkpoint in checkpoints:
        checkpoint_status = "PASS" if checkpoint["passed"] else "FAIL"
        lines.extend(
            [
                "",
                f"### {checkpoint['name']}: {checkpoint_status}",
                checkpoint["summary"],
                f"Baseline: `{checkpoint['baseline']}`",
                f"Current: `{checkpoint['current']}`",
            ]
        )
        for finding in checkpoint["findings"]:
            lines.extend(
                [
                    f"- **{finding['severity'].upper()}: {finding['issue']}**",
                    f"  Location: {finding['location']}. {finding['reasoning']}",
                ]
            )

    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result
