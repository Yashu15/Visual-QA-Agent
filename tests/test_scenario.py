import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from visual_qa_agent.scenario import CHECKPOINT_NAMES, run_storefront_flow


class FakeStyle:
    def evaluate(self, _script):
        return None


class FakeLocator:
    def __init__(self, selector, actions):
        self.selector = selector
        self.actions = actions

    def wait_for(self, **_kwargs):
        self.actions.append(("wait", self.selector))

    def fill(self, value):
        self.actions.append(("fill", self.selector, value))

    def click(self):
        self.actions.append(("click", self.selector))


class FakePage:
    def __init__(self):
        self.actions = []
        self.styles = []

    def goto(self, url, **_kwargs):
        self.actions.append(("goto", url))

    def locator(self, selector):
        return FakeLocator(selector, self.actions)

    def wait_for_url(self, url, **_kwargs):
        self.actions.append(("url", url))

    def wait_for_function(self, expression, **_kwargs):
        self.actions.append(("wait_for_function", expression))

    def add_style_tag(self, *, content):
        self.styles.append(content)
        return FakeStyle()

    def screenshot(self, *, path, **_kwargs):
        Image.new("RGB", (64, 48), "white").save(path)


class FakeContext:
    def __init__(self, page):
        self.page = page

    def new_page(self):
        return self.page

    def close(self):
        pass


class FakeBrowser:
    def __init__(self, page):
        self.context = FakeContext(page)

    def new_context(self, **_kwargs):
        return self.context

    def close(self):
        pass


class FakePlaywright:
    def __init__(self, page):
        self.chromium = self
        self.page = page
        self.launch_options = None

    def launch(self, **options):
        self.launch_options = options
        return FakeBrowser(self.page)


class FakePlaywrightManager:
    def __init__(self, page):
        self.playwright = FakePlaywright(page)

    def __enter__(self):
        return self.playwright

    def __exit__(self, *_args):
        return False


class LocalStorefrontFlowTests(unittest.TestCase):
    def test_runs_checkout_flow_and_captures_all_checkpoints(self):
        page = FakePage()
        manager = FakePlaywrightManager(page)
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            with patch("visual_qa_agent.scenario.sync_playwright", return_value=manager):
                dimensions = run_storefront_flow(
                    output_dir,
                    username="demo",
                    password="demo",
                    inject_defect="missing-add-to-cart",
                )

            self.assertEqual(tuple(dimensions), CHECKPOINT_NAMES)
            self.assertEqual(len(list(output_dir.glob("*.png"))), len(CHECKPOINT_NAMES))
            self.assertTrue(all(size == {"width": 64, "height": 48} for size in dimensions.values()))
            self.assertIn(("fill", "#user-name", "demo"), page.actions)
            self.assertIn(("fill", "#password", "demo"), page.actions)
            self.assertIn(("wait", "#inventory-page"), page.actions)
            self.assertIn(("click", '[data-test="add-to-cart-trail-pack"]'), page.actions)
            self.assertIn(("click", "#header-cart"), page.actions)
            self.assertIn(("click", "#finish"), page.actions)
            self.assertTrue(any(".add-button" in style for style in page.styles))
            self.assertEqual(manager.playwright.launch_options, {"headless": True})

    def test_headed_mode_launches_visible_browser(self):
        page = FakePage()
        manager = FakePlaywrightManager(page)
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch("visual_qa_agent.scenario.sync_playwright", return_value=manager):
                run_storefront_flow(
                    Path(temporary_directory),
                    username="demo",
                    password="demo",
                    headed=True,
                )

        self.assertEqual(manager.playwright.launch_options, {"headless": False})

    def test_rejects_unknown_defect_without_starting_browser(self):
        with patch("visual_qa_agent.scenario.sync_playwright") as playwright:
            with self.assertRaisesRegex(ValueError, "Unknown defect"):
                run_storefront_flow(
                    Path("unused"),
                    username="demo",
                    password="demo",
                    inject_defect="not-a-real-defect",
                )
            playwright.assert_not_called()


if __name__ == "__main__":
    unittest.main()
