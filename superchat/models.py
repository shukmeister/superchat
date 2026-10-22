"""Offline model discovery for users and programs; no API key is required."""

import argparse
import json
from pathlib import Path
import sys


# Expose accepted identifiers and explicit pricing units without loading credentials.
def catalog_payload():
    path = Path(__file__).parent / "config" / "models.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))["models"]
    models = []
    for key, config in catalog.items():
        models.append({
            "model": key,
            "openrouter_id": config["openrouter_id"],
            "label": config.get("label", key),
            "description": config.get("description", ""),
            "input_cost_per_million_tokens": config.get("input_cost"),
            "output_cost_per_million_tokens": config.get("output_cost"),
            "context_length": config.get("context_length"),
            "capabilities": config.get("model_info", {}),
        })
    return {
        "schema_version": 1,
        "pricing_source": "bundled_catalog",
        "currency": "USD",
        "pricing_note": "Catalog estimates per million tokens; live availability and provider prices may differ.",
        "models": models,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="superchat models",
        description="List configured models and catalog prices. Works offline without an API key.",
        epilog="Pass a model key or OpenRouter ID to superchat consult -m. Prices are bundled estimates, not live quotes.",
        allow_abbrev=False,
    )
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text; use json for programs)")
    args = parser.parse_args(argv)
    payload = catalog_payload()
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=True, allow_nan=False))
    else:
        print("{:<28} {:>14} {:>14}".format("Model key", "Input $/1M", "Output $/1M"))
        for model in payload["models"]:
            print("{:<28} {:>14} {:>14}".format(
                model["model"], model["input_cost_per_million_tokens"],
                model["output_cost_per_million_tokens"]))
        print("\n" + payload["pricing_note"])
        print("Use a model key with: superchat consult -m MODEL --prompt TEXT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
