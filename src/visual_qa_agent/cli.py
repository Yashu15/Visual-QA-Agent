"""Command-line interface for the visual QA agent."""

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from visual_qa_agent.ollama_client import analyze_screenshots
from visual_qa_agent.report import write_scenario_reports
from visual_qa_agent.scenario import CHECKPOINT_NAMES, DEFECT_STYLES, SCENARIO_NAME, run_storefront_flow


def _add_scenario_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--width", type=int, default=1440, help="Browser viewport width in CSS pixels")
    parser.add_argument("--height", type=int, default=1000, help="Browser viewport height in CSS pixels")
    parser.add_argument("--headed", action="store_true", help="Show the Chromium window while the scenario runs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="visual-qa", description="Test the local Fieldwork Supply storefront visually.")
    commands = parser.add_subparsers(dest="command", required=True)

    scenario_parser = commands.add_parser("scenario", help="Run the local Fieldwork Supply login-to-checkout journey")
    scenario_commands = scenario_parser.add_subparsers(dest="scenario_action", required=True)

    baseline_parser = scenario_commands.add_parser("baseline", help="Capture clean screenshots for each journey checkpoint")
    _add_scenario_options(baseline_parser)
    baseline_parser.add_argument("--baseline-dir", type=Path, default=Path("artifacts/baselines/fieldwork-supply"))
    baseline_parser.add_argument("--force", action="store_true", help="Replace existing baseline screenshots")

    scenario_compare_parser = scenario_commands.add_parser("compare", help="Compare a new local storefront journey against baselines")
    _add_scenario_options(scenario_compare_parser)
    scenario_compare_parser.add_argument("--baseline-dir", type=Path, default=Path("artifacts/baselines/fieldwork-supply"))
    scenario_compare_parser.add_argument("--run-dir", type=Path, help="Output directory (defaults to a timestamped run folder)")
    scenario_compare_parser.add_argument(
        "--inject-defect",
        choices=sorted(DEFECT_STYLES),
        help="Inject a screenshot-only visual defect to verify regression detection",
    )
    scenario_compare_parser.add_argument("--model", default="qwen2.5vl:3b", help="Installed Ollama vision model")
    scenario_compare_parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama server base URL")
    return parser


def _run_scenario(args: argparse.Namespace) -> int:
    username = os.environ.get("STOREFRONT_USERNAME")
    password = os.environ.get("STOREFRONT_PASSWORD")
    if not username or not password:
        raise ValueError(
            "Set STOREFRONT_USERNAME and STOREFRONT_PASSWORD in the environment before running the scenario."
        )

    if args.scenario_action == "baseline":
        existing = [args.baseline_dir / f"{name}.png" for name in CHECKPOINT_NAMES if (args.baseline_dir / f"{name}.png").exists()]
        if existing and not args.force:
            raise FileExistsError(
                f"Baseline files already exist in {args.baseline_dir}; use --force to replace them."
            )
        dimensions = run_storefront_flow(
            args.baseline_dir,
            username=username,
            password=password,
            width=args.width,
            height=args.height,
            headed=args.headed,
        )
        print(f"Saved {len(dimensions)} baseline screenshots to {args.baseline_dir}.")
        for name in dimensions:
            print(f"  {name}: {args.baseline_dir / f'{name}.png'}")
        return 0

    missing = [args.baseline_dir / f"{name}.png" for name in CHECKPOINT_NAMES if not (args.baseline_dir / f"{name}.png").is_file()]
    if missing:
        raise FileNotFoundError("Missing baseline checkpoints: " + ", ".join(str(path) for path in missing))

    run_dir = args.run_dir or Path("artifacts/runs/fieldwork-supply") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dimensions = run_storefront_flow(
        run_dir / "screenshots",
        username=username,
        password=password,
        width=args.width,
        height=args.height,
        headed=args.headed,
        inject_defect=args.inject_defect,
    )
    checkpoints = []
    for name in dimensions:
        baseline = args.baseline_dir / f"{name}.png"
        current = run_dir / "screenshots" / f"{name}.png"
        analysis = analyze_screenshots(
            baseline,
            current,
            model=args.model,
            ollama_url=args.ollama_url,
        )
        checkpoints.append(
            {
                **analysis,
                "name": name,
                "baseline": str(baseline),
                "current": str(current),
                "dimensions": dimensions[name],
            }
        )

    markdown_path = run_dir / "visual-qa-report.md"
    json_path = run_dir / "visual-qa-report.json"
    result = write_scenario_reports(
        SCENARIO_NAME,
        args.model,
        checkpoints,
        markdown_path,
        json_path,
        injected_defect=args.inject_defect,
    )
    status = "PASS" if result["passed"] else "FAIL"
    print(f"{status}: {sum(checkpoint['passed'] for checkpoint in checkpoints)}/{len(checkpoints)} checkpoints passed.")
    print(f"Markdown: {markdown_path}\nJSON: {json_path}")
    return 0 if result["passed"] else 1


def main() -> int:
    args = build_parser().parse_args()
    try:
        return _run_scenario(args)
    except Exception as error:
        print(f"visual-qa: error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
