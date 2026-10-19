# AI-Powered Visual Regression Testing Agent

A local CLI that captures web pages with Playwright, compares a current screenshot with a baseline using an Ollama vision model, and writes actionable Markdown and JSON reports. Screenshots and analysis stay on your machine; the tool does not call a hosted AI API.

## Requirements

- macOS, Linux, or Windows
- Python 3.9 or newer
- Ollama and a vision model that supports image input (the default is `qwen2.5vl:3b`)

## Setup

1. Install Ollama for your operating system and start it. Its local API should be available at `http://localhost:11434`.
2. Download the model once:

   ```bash
   ollama pull qwen2.5vl:3b
   ```

3. From this project directory, create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell, activate with `.venv\\Scripts\\Activate.ps1`.

4. Install the project and its Python dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install .
   python -m playwright install chromium
   ```

## Local Storefront Scenario

The project includes a local Fieldwork Supply storefront. The scenario runner signs in, adds the Trail Pack to the cart, and completes checkout. It captures seven checkpoints: login, inventory, product added, cart, checkout information, checkout overview, and checkout confirmation. The page, product illustrations, and flow are packaged with the project; no external website or image service is needed.

Set demo credentials in the environment. The local fixture accepts any non-empty username and password.

```bash
export STOREFRONT_USERNAME=demo
export STOREFRONT_PASSWORD=demo
```

In Windows PowerShell, use `$env:STOREFRONT_USERNAME="demo"` and `$env:STOREFRONT_PASSWORD="demo"`.

Capture clean baselines once:

```bash
visual-qa scenario baseline
```

Baseline images are saved in `artifacts/baselines/fieldwork-supply/`. Existing images are not overwritten unless you pass `--force`.

Run the same journey and compare each screenshot with its matching baseline:

```bash
visual-qa scenario compare
```

To watch the local Chromium window, capture a headed baseline and compare in headed mode as well. Keep it separate from the default headless baseline because browser rendering can vary by mode:

```bash
visual-qa scenario baseline --headed --baseline-dir artifacts/baselines/fieldwork-supply-headed
visual-qa scenario compare --headed --baseline-dir artifacts/baselines/fieldwork-supply-headed
```

Each run saves screenshots and combined Markdown/JSON reports in a timestamped folder under `artifacts/runs/fieldwork-supply/`. Exit code `0` means all checkpoints passed, `1` means at least one visual regression was found, and `2` means setup or execution failed.

To verify the failure path, inject a defect into the inventory screenshot. The local page itself is unchanged; the defect is applied only while that checkpoint screenshot is captured:

```bash
visual-qa scenario compare --inject-defect missing-add-to-cart
```

The supported screenshot-only defects are `missing-add-to-cart` and `missing-order-confirmation`. The injected style is removed immediately after its screenshot, so the remaining checkout steps can complete. Baselines should be reviewed and committed intentionally; run output is ignored by Git.

## Scenario Options

- `--width` and `--height`: set the browser viewport (defaults: 1440 by 1000).
- `--baseline-dir PATH`: choose where clean checkpoint baselines are read or written.
- `--run-dir PATH`: choose an output folder instead of the default timestamped run folder.
- `--model MODEL` and `--ollama-url URL`: choose the local Ollama model and server.
- `--inject-defect NAME`: hide a control in one checkpoint screenshot to exercise a known failure.

For deterministic results, capture both versions with the same URL state, viewport, authentication, and browser setup. The model's visual judgment is probabilistic; review findings before treating them as definitive defects.

## Tests

```bash
python -m unittest discover -s tests -v
```

No Ollama server is needed for the unit tests.
