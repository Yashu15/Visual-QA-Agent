import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from visual_qa_agent.ollama_client import analyze_screenshots, parse_analysis


class AnalyzeScreenshotsTests(unittest.TestCase):
    def test_identical_images_pass_without_calling_ollama(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            baseline = Path(temporary_directory) / "baseline.png"
            current = Path(temporary_directory) / "current.png"
            Image.new("RGB", (2, 2), "white").save(baseline)
            Image.new("RGB", (2, 2), "white").save(current)

            with patch("visual_qa_agent.ollama_client.urlopen") as mocked_urlopen:
                result = analyze_screenshots(
                    baseline,
                    current,
                    model="test-vision-model",
                    ollama_url="http://localhost:11434",
                )

        mocked_urlopen.assert_not_called()
        self.assertTrue(result["passed"])
        self.assertEqual(result["findings"], [])


class ParseAnalysisTests(unittest.TestCase):
    def test_accepts_clean_pass(self):
        result = parse_analysis('{"passed": true, "summary": "No meaningful regressions.", "findings": []}')
        self.assertTrue(result["passed"])
        self.assertEqual(result["findings"], [])

    def test_normalizes_finding_fields(self):
        result = parse_analysis(
            '{"passed": false, "summary": "Button missing.", "findings": '
            '[{"severity": "high", "issue": "Missing button", "location": "Header", "reasoning": "Visible in baseline only."}]}'
        )
        self.assertFalse(result["passed"])
        self.assertEqual(result["findings"][0]["location"], "Header")

    def test_rejects_inconsistent_pass(self):
        with self.assertRaisesRegex(ValueError, "must not contain findings"):
            parse_analysis(
                '{"passed": true, "summary": "Issue", "findings": '
                '[{"severity": "high", "issue": "Broken", "location": "Header"}]}'
            )

    def test_rejects_unknown_severity(self):
        with self.assertRaisesRegex(ValueError, "severity must be one of"):
            parse_analysis(
                '{"passed": false, "summary": "Issue", "findings": '
                '[{"severity": "urgent", "issue": "Broken"}]}'
            )


if __name__ == "__main__":
    unittest.main()
