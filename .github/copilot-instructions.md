# Visual QA Agent Workspace Guidance

- Keep browser capture and vision analysis local by default; do not add hosted AI services or transmit screenshots to third parties.
- Preserve the `visual-qa` CLI and its structured Markdown/JSON reports.
- Keep dynamic-region masking opt-in and avoid silently hiding page content beyond explicit masks and `data-visual-qa-mask` elements.
- Add tests for changes to screenshot capture, model-response validation, or report formatting.
- Run `python -m unittest discover -s tests -v` after Python changes.
