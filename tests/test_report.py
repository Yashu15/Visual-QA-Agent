import json
import tempfile
import unittest
from pathlib import Path

from visual_qa_agent.report import write_scenario_reports


class WriteScenarioReportsTests(unittest.TestCase):
    def test_writes_combined_scenario_result_and_defect_context(self):
        checkpoints = [
            {
                "name": "inventory",
                "passed": False,
                "summary": "The add-to-cart button is missing.",
                "baseline": "baseline/inventory.png",
                "current": "run/inventory.png",
                "findings": [
                    {
                        "severity": "high",
                        "issue": "Missing add-to-cart button",
                        "location": "Product card",
                        "reasoning": "The button is present in the baseline only.",
                    }
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            markdown_path = Path(temporary_directory) / "report.md"
            json_path = Path(temporary_directory) / "report.json"
            result = write_scenario_reports(
                "fieldwork-supply-checkout",
                "test-vision-model",
                checkpoints,
                markdown_path,
                json_path,
                injected_defect="missing-add-to-cart",
            )

            self.assertFalse(result["passed"])
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), result)
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("Visual QA Scenario: FAIL", markdown)
            self.assertIn("missing-add-to-cart", markdown)
            self.assertIn("Missing add-to-cart button", markdown)


if __name__ == "__main__":
    unittest.main()
