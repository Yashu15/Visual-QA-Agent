"""Repeatable local storefront login, cart, and checkout scenario."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

STOREFRONT_URL = Path(__file__).with_name("storefront.html").as_uri()
SCENARIO_NAME = "fieldwork-supply-checkout"
CHECKPOINT_NAMES = (
    "login",
    "inventory",
    "product_added",
    "cart",
    "checkout_info",
    "checkout_overview",
    "checkout_complete",
)

DEFECT_STYLES = {
    "missing-add-to-cart": {
        "checkpoint": "inventory",
        "css": '.add-button { visibility: hidden !important; }',
    },
    "missing-order-confirmation": {
        "checkpoint": "checkout_complete",
        "css": '.complete-header { visibility: hidden !important; }',
    },
}


def run_storefront_flow(
    output_dir: Path,
    *,
    username: str,
    password: str,
    width: int = 1440,
    height: int = 1000,
    headed: bool = False,
    inject_defect: str | None = None,
) -> dict[str, dict[str, int]]:
    """Run the local storefront purchase journey and save each screenshot checkpoint."""
    if inject_defect is not None and inject_defect not in DEFECT_STYLES:
        raise ValueError(f"Unknown defect '{inject_defect}'. Choose from: {', '.join(DEFECT_STYLES)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    dimensions: dict[str, dict[str, int]] = {}

    def capture(page, checkpoint: str) -> None:
        path = output_dir / f"{checkpoint}.png"
        css = '[data-visual-qa-mask] { visibility: hidden !important; }'
        if inject_defect and DEFECT_STYLES[inject_defect]["checkpoint"] == checkpoint:
            css += "\n" + DEFECT_STYLES[inject_defect]["css"]
        style = page.add_style_tag(content=css)
        page.screenshot(path=str(path), full_page=True, animations="disabled")
        style.evaluate("element => element.remove()")
        with Image.open(path) as image:
            dimensions[checkpoint] = {"width": image.width, "height": image.height}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed)
        try:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            page = context.new_page()
            page.goto(STOREFRONT_URL, wait_until="domcontentloaded", timeout=60_000)
            page.locator("#login-button").wait_for(state="visible", timeout=15_000)
            capture(page, "login")

            page.locator("#user-name").fill(username)
            page.locator("#password").fill(password)
            page.locator("#login-button").click()
            page.locator("#inventory-page").wait_for(state="visible", timeout=10_000)
            capture(page, "inventory")

            page.locator('[data-test="add-to-cart-trail-pack"]').click()
            page.locator("#cart-count").wait_for(state="visible", timeout=5_000)
            capture(page, "product_added")

            page.locator("#header-cart").click()
            page.locator("#cart-page").wait_for(state="visible", timeout=10_000)
            page.locator(".cart_item").wait_for(state="visible", timeout=10_000)
            capture(page, "cart")

            page.locator("#checkout").click()
            page.locator("#checkout-info-page").wait_for(state="visible", timeout=10_000)
            page.locator("#first-name").fill("Visual")
            page.locator("#last-name").fill("QA")
            page.locator("#postal-code").fill("94000")
            capture(page, "checkout_info")

            page.locator("#continue").click()
            page.locator("#checkout-overview-page").wait_for(state="visible", timeout=10_000)
            capture(page, "checkout_overview")

            page.locator("#finish").click()
            page.locator("#checkout-complete-page").wait_for(state="visible", timeout=10_000)
            page.locator(".complete-header").wait_for(state="visible", timeout=10_000)
            capture(page, "checkout_complete")
            context.close()
        finally:
            browser.close()

    return dimensions
