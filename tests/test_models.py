from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from superchat.models import catalog_payload, main
from superchat.consult import resolve_models


class ModelDiscoveryTests(unittest.TestCase):
    def test_identifiers_are_accepted_and_prices_match_catalog(self):
        path = Path(__file__).resolve().parents[1] / "superchat/config/models.json"
        catalog = json.loads(path.read_text())["models"]
        payload = catalog_payload()
        self.assertEqual(payload["currency"], "USD")
        self.assertEqual(payload["pricing_source"], "bundled_catalog")
        self.assertEqual(len(payload["models"]), len(catalog))
        for model in payload["models"]:
            for identifier in (model["model"], model["openrouter_id"]):
                self.assertEqual(resolve_models([[identifier]], catalog), [model["model"]])
            self.assertEqual(model["input_cost_per_million_tokens"],
                             catalog[model["model"]]["input_cost"])
            self.assertEqual(model["output_cost_per_million_tokens"],
                             catalog[model["model"]]["output_cost"])

    def test_text_and_json_output(self):
        for args in ([], ["--format", "json"]):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(args), 0)
            if args:
                self.assertEqual(json.loads(output.getvalue()), catalog_payload())
            else:
                self.assertIn("Input $/1M", output.getvalue())
                self.assertIn("Output $/1M", output.getvalue())

    def test_entry_point_does_not_require_credentials(self):
        env = dict(os.environ, OPENROUTER_API_KEY="")
        result = subprocess.run(
            [sys.executable, "-m", "superchat.main", "models", "--format", "json"],
            env=env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["models"])


if __name__ == "__main__":
    unittest.main()
