"""Stateless panel consultations with bounded input and machine-readable output."""

import argparse
import asyncio
from contextlib import redirect_stdout
import json
import math
import re
import sys
import time

from superchat.core.model_client import ModelClientManager
from superchat.utils.stats import calculate_model_cost


MAX_INPUT_BYTES = 1024 * 1024
SYSTEM_PROMPT = "Answer the user's request accurately and independently. State uncertainty when relevant."


class ConsultInputError(ValueError):
    pass


class ConsultParser(argparse.ArgumentParser):
    # Return argument errors through the same JSON envelope as other failures.
    def error(self, message):
        raise ConsultInputError(message)


# Reject NaN and infinity so timeout enforcement cannot be disabled by accident.
def positive_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return number


def positive_integer(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be an integer greater than zero")
    return number


def create_parser():
    parser = ConsultParser(
        prog="superchat consult",
        description="Get independent panel answers and exit. No conversation is saved.",
        epilog=("Discover model IDs and catalog costs with: superchat models --format json. "
                "JSON is written to stdout; diagnostics go to stderr. Set OPENROUTER_API_KEY "
                "before running; no interactive setup is used. Exit codes: 0 success, "
                "1 failed, 2 invalid input/configuration, 3 partial results, 130 interrupted."),
        allow_abbrev=False,
    )
    parser.add_argument("-m", "--model", nargs="+", action="append", required=True,
                        help="Catalog keys, OpenRouter IDs, or unambiguous aliases; commas also accepted")
    parser.add_argument("--prompt", required=True,
                        help="Prompt text, or '-' to read UTF-8 stdin until EOF (maximum 1 MiB)")
    parser.add_argument("--format", choices=["json"], default="json",
                        help="Output format (default: json)")
    parser.add_argument("--timeout", type=positive_seconds, default=120.0,
                        help="Timeout in seconds per model request (default: 120)")
    parser.add_argument("--max-output-tokens", type=positive_integer,
                        help="Maximum output tokens per model; otherwise use the provider default")
    return parser


# Read stdin only when explicitly requested; bound the read before decoding.
def read_prompt(value, stdin):
    if value == "-":
        if stdin.isatty():
            raise ConsultInputError("--prompt - requires piped stdin")
        data = stdin.buffer.read(MAX_INPUT_BYTES + 1)
    else:
        data = value.encode("utf-8", errors="strict")
    if len(data) > MAX_INPUT_BYTES:
        raise ConsultInputError("Prompt exceeds the 1 MiB UTF-8 input limit")
    prompt = data.decode("utf-8", errors="strict")
    if not prompt.strip():
        raise ConsultInputError("Prompt must not be empty or whitespace-only")
    return prompt


# Exact identifiers take priority; aliases must match whole words in one model only.
def resolve_models(groups, catalog):
    selected = []
    for group in groups:
        for argument in group:
            for name in argument.split(","):
                name = name.strip()
                if not name:
                    raise ConsultInputError("Model names must not be empty")
                exact = [key for key, config in catalog.items()
                         if name.casefold() in (key.casefold(), config["openrouter_id"].casefold())]
                words = set(re.findall(r"\w+", name.casefold()))
                matches = exact or [
                    key for key, config in catalog.items()
                    if words and words.issubset(set(re.findall(
                        r"\w+", " ".join(str(config.get(field, "")) for field in
                                          ("company", "family", "model", "release", "label")).casefold()
                    )))
                ]
                if not matches:
                    raise ConsultInputError("Unknown model: {}".format(name))
                if len(matches) != 1:
                    raise ConsultInputError("Ambiguous model '{}'; use one of: {}".format(
                        name, ", ".join(matches)))
                if matches[0] in selected:
                    raise ConsultInputError("Duplicate model: {}".format(matches[0]))
                selected.append(matches[0])
    return selected


# Query fresh clients independently and retain slot order regardless of completion order.
async def consult_panel(manager, models, prompt, timeout, max_output_tokens=None):
    from autogen_core.models import SystemMessage, UserMessage

    async def query(model):
        started = time.monotonic()
        config = manager.get_model_config(model)
        result = {
            "model": model,
            "openrouter_id": config["openrouter_id"],
            "status": "failed",
            "answer": None,
            "finish_reason": None,
            "usage": None,
            "estimated_cost_usd": None,
            "error": None,
        }
        client = None
        try:
            client = manager.create_model_client(model, skip_validation=True, max_retries=0)
            extra = {} if max_output_tokens is None else {"max_tokens": max_output_tokens}
            response = await asyncio.wait_for(client.create(
                [SystemMessage(content=SYSTEM_PROMPT), UserMessage(content=prompt, source="user")],
                extra_create_args=extra,
            ), timeout=timeout)
            if response.usage is not None:
                incoming = response.usage.prompt_tokens
                outgoing = response.usage.completion_tokens
                result["usage"] = {"prompt_tokens": incoming, "completion_tokens": outgoing,
                                   "total_tokens": incoming + outgoing}
                result["estimated_cost_usd"] = calculate_model_cost(config, incoming, outgoing)
            result["finish_reason"] = response.finish_reason
            if not isinstance(response.content, str) or not response.content.strip():
                result["error"] = {"code": "invalid_response", "message": "Model returned no text answer"}
            else:
                result.update(status="success", answer=response.content)
        except asyncio.TimeoutError:
            result["error"] = {"code": "timeout", "message": "Request exceeded {} seconds".format(timeout)}
        except Exception as exc:
            message = str(exc)
            if manager.api_key:
                message = message.replace(manager.api_key, "[redacted]")
            result["error"] = {"code": "provider_error", "message": message}
        finally:
            if client is not None:
                try:
                    await asyncio.wait_for(client.close(), timeout=5)
                except Exception:
                    print("Could not close client for {}".format(model), file=sys.stderr)
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        return result

    return await asyncio.gather(*(query(model) for model in models))


def result_envelope(results, elapsed, error=None):
    successes = sum(result["status"] == "success" for result in results)
    status = "success" if results and successes == len(results) else "partial" if successes else "failed"
    return {"schema_version": 1, "status": status, "results": results,
            "elapsed_seconds": round(elapsed, 3), "error": error}


# Keep stdout as a single JSON document, including on validation and runtime failures.
def main(argv=None):
    started = time.monotonic()
    results = []
    error = None
    try:
        args = create_parser().parse_args(argv)
        with redirect_stdout(sys.stderr):
            manager = ModelClientManager()
            models = resolve_models(args.model, manager.models_config["models"])
            if not manager.api_key:
                raise ConsultInputError("OPENROUTER_API_KEY is not configured; set it before consulting")
            prompt = read_prompt(args.prompt, sys.stdin)
            results = asyncio.run(consult_panel(
                manager, models, prompt, args.timeout, args.max_output_tokens))
        successes = sum(result["status"] == "success" for result in results)
        exit_code = 0 if successes == len(results) else 3 if successes else 1
    except (ConsultInputError, UnicodeError, OSError) as exc:
        error = {"code": "invalid_input", "message": str(exc)}
        exit_code = 2
    except KeyboardInterrupt:
        error = {"code": "interrupted", "message": "Consultation interrupted"}
        exit_code = 130
    except Exception:
        error = {"code": "internal_error", "message": "Consultation failed unexpectedly"}
        exit_code = 1
    payload = result_envelope(results, time.monotonic() - started, error)
    if error:
        print(error["message"], file=sys.stderr)
    print(json.dumps(payload, ensure_ascii=True, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
