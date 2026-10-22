import asyncio
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from autogen_core.models import CreateResult, RequestUsage

from superchat import consult
from superchat.core.model_client import ModelClientManager


CATALOG = {
    "alpha-one": {"openrouter_id": "vendor/alpha-one", "family": "Alpha", "model": "One",
                  "label": "A1", "input_cost": 1, "output_cost": 2,
                  "model_info": {"family": "unknown", "vision": False,
                                 "function_calling": False, "json_output": False,
                                 "structured_output": False}},
    "alpha-two": {"openrouter_id": "vendor/alpha-two", "family": "Alpha", "model": "Two",
                  "label": "A2", "input_cost": 10, "output_cost": 20},
}


def response(text="Independent answer", incoming=100, outgoing=20):
    return CreateResult(content=text, finish_reason="stop", cached=False,
                        usage=RequestUsage(prompt_tokens=incoming, completion_tokens=outgoing))


class FakeClient:
    def __init__(self, behavior=None):
        self.behavior = behavior
        self.messages = []
        self.closed = False
        self.cancelled = False
        self.extra = None

    async def create(self, messages, extra_create_args):
        self.messages.append(messages)
        self.extra = extra_create_args
        if self.behavior:
            return await self.behavior()
        return response()

    async def close(self):
        self.closed = True


class FakeManager:
    def __init__(self, clients=None):
        self.api_key = "fake-test-key"
        self.models_config = {"models": CATALOG}
        self.clients = clients or {model: FakeClient() for model in CATALOG}
        self.options = []

    def get_model_config(self, model):
        return CATALOG[model]

    def create_model_client(self, model, **options):
        self.options.append(options)
        return self.clients[model]


class InputTests(unittest.TestCase):
    def test_exact_ids_aliases_and_commas(self):
        self.assertEqual(consult.resolve_models([["vendor/alpha-one,A2"]], CATALOG),
                         ["alpha-one", "alpha-two"])
        self.assertEqual(consult.resolve_models([["Alpha One"]], CATALOG), ["alpha-one"])

    def test_reject_ambiguous_unknown_duplicate_and_empty_models(self):
        for names in ([["alpha"]], [["missing"]], [["A1", "alpha-one"]], [["A1,"]]):
            with self.subTest(names=names), self.assertRaises(consult.ConsultInputError):
                consult.resolve_models(names, CATALOG)

    def test_prompt_preserves_whitespace_and_unicode(self):
        text = "  Review:\nπ = 3\n"
        self.assertEqual(consult.read_prompt(text, None), text)
        stream = io.TextIOWrapper(io.BytesIO(text.encode("utf-8")), encoding="utf-8")
        self.assertEqual(consult.read_prompt("-", stream), text)

    def test_stdin_is_not_read_for_argument(self):
        self.assertEqual(consult.read_prompt("question", object()), "question")

    def test_empty_invalid_utf8_and_size_limit(self):
        for data in (b" \n", b"\xff", b"x" * (consult.MAX_INPUT_BYTES + 1)):
            with self.subTest(data_length=len(data)):
                with self.assertRaises((consult.ConsultInputError, UnicodeError)):
                    consult.read_prompt("-", io.TextIOWrapper(io.BytesIO(data)))
        with self.assertRaises(consult.ConsultInputError):
            consult.read_prompt("é" * (consult.MAX_INPUT_BYTES // 2 + 1), None)
        self.assertEqual(len(consult.read_prompt("x" * consult.MAX_INPUT_BYTES, None)),
                         consult.MAX_INPUT_BYTES)

    def test_stdin_read_is_bounded(self):
        class BoundedBuffer:
            def read(self, size):
                self.size = size
                return b"prompt"
        buffer = BoundedBuffer()
        consult.read_prompt("-", SimpleNamespace(isatty=lambda: False, buffer=buffer))
        self.assertEqual(buffer.size, consult.MAX_INPUT_BYTES + 1)

    def test_tty_stdin_fails_without_prompting(self):
        with self.assertRaises(consult.ConsultInputError):
            consult.read_prompt("-", SimpleNamespace(isatty=lambda: True))

    def test_parser_rejects_missing_invalid_and_unknown_options(self):
        base = ["-m", "A1", "--prompt", "question"]
        for args in ([], base + ["--timeout", "nan"], base + ["--timeout", "inf"],
                     base + ["--timeout", "0"], base + ["--max-output-tokens", "0"],
                     base + ["--max-output-tokens", "bad"], base + ["--prompt-file", "x"]):
            with self.subTest(args=args), self.assertRaises(consult.ConsultInputError):
                consult.create_parser().parse_args(args)


class PanelTests(unittest.IsolatedAsyncioTestCase):
    async def test_parallel_independent_answers_order_usage_and_cleanup(self):
        arrived = 0
        ready = asyncio.Event()

        async def wait_for_both():
            nonlocal arrived
            arrived += 1
            if arrived == 2:
                ready.set()
            await ready.wait()
            return response()

        clients = {model: FakeClient(wait_for_both) for model in CATALOG}
        manager = FakeManager(clients)
        results = await consult.consult_panel(manager, list(CATALOG), "question", 1, 300)
        self.assertEqual([item["model"] for item in results], list(CATALOG))
        self.assertTrue(all(item["status"] == "success" for item in results))
        self.assertAlmostEqual(results[0]["estimated_cost_usd"], 0.00014)
        self.assertAlmostEqual(results[1]["estimated_cost_usd"], 0.0014)
        self.assertEqual(results[0]["usage"]["total_tokens"], 120)
        for client in clients.values():
            self.assertTrue(client.closed)
            self.assertEqual([message.content for message in client.messages[0]],
                             [consult.SYSTEM_PROMPT, "question"])
            self.assertEqual(client.extra, {"max_tokens": 300})
        self.assertTrue(all(option == {"skip_validation": True, "max_retries": 0}
                            for option in manager.options))

    async def test_timeout_cancels_request_and_preserves_other_answer(self):
        async def stalled():
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                slow.cancelled = True
                raise
        slow = FakeClient(stalled)
        manager = FakeManager({"alpha-one": FakeClient(), "alpha-two": slow})
        results = await consult.consult_panel(manager, list(CATALOG), "q", 0.01)
        self.assertEqual(results[0]["status"], "success")
        self.assertEqual(results[1]["error"]["code"], "timeout")
        self.assertTrue(slow.cancelled)
        self.assertTrue(slow.closed)

    async def test_provider_failure_is_isolated_and_key_redacted(self):
        async def fail():
            raise RuntimeError("Bad credentials: fake-test-key")
        manager = FakeManager({"alpha-one": FakeClient(fail), "alpha-two": FakeClient()})
        results = await consult.consult_panel(manager, list(CATALOG), "q", 1)
        self.assertEqual(results[0]["error"]["code"], "provider_error")
        self.assertNotIn(manager.api_key, json.dumps(results))
        self.assertEqual(results[1]["status"], "success")

    async def test_empty_response_retains_usage(self):
        async def empty():
            return response("  ")
        results = await consult.consult_panel(
            FakeManager({"alpha-one": FakeClient(empty)}), ["alpha-one"], "q", 1)
        self.assertEqual(results[0]["error"]["code"], "invalid_response")
        self.assertEqual(results[0]["usage"]["total_tokens"], 120)

    async def test_client_creation_failure_preserves_other_answer(self):
        manager = FakeManager()
        create = manager.create_model_client

        def fail_one(model, **options):
            if model == "alpha-one":
                raise ValueError("Unsupported model configuration")
            return create(model, **options)

        manager.create_model_client = fail_one
        results = await consult.consult_panel(manager, list(CATALOG), "q", 1)
        self.assertEqual(results[0]["error"]["code"], "provider_error")
        self.assertEqual(results[1]["status"], "success")

    async def test_cleanup_failure_does_not_discard_answer(self):
        class CloseFailure(FakeClient):
            async def close(self):
                raise RuntimeError("close failed")

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            results = await consult.consult_panel(
                FakeManager({"alpha-one": CloseFailure()}), ["alpha-one"], "q", 1)
        self.assertEqual(results[0]["status"], "success")
        self.assertIn("Could not close client", stderr.getvalue())

    async def test_actual_sdk_request_with_privacy_transport(self):
        requests = []

        async def handle(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "test", "object": "chat.completion", "created": 0,
                "model": "vendor/alpha-one", "choices": [{"index": 0,
                    "message": {"role": "assistant", "content": "SDK answer"},
                    "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            })

        manager = ModelClientManager.__new__(ModelClientManager)
        manager.api_key = "fake-key"
        manager.models_config = {"models": CATALOG}
        with patch("superchat.core.model_client.httpx.AsyncHTTPTransport",
                   return_value=httpx.MockTransport(handle)):
            results = await consult.consult_panel(manager, ["alpha-one"], "Review π", 1, 300)
        self.assertEqual(results[0]["answer"], "SDK answer", results)
        self.assertEqual(results[0]["usage"]["total_tokens"], 15)
        self.assertEqual(requests[0]["provider"],
                         {"data_collection": "deny", "allow_fallbacks": False})
        self.assertEqual(requests[0]["max_tokens"], 300)
        self.assertEqual(requests[0]["messages"][-1]["content"], "Review π")


class CommandTests(unittest.TestCase):
    def invoke(self, args, manager=None, stdin=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(consult, "ModelClientManager", return_value=manager or FakeManager()), \
             patch.object(sys, "stdin", stdin or io.TextIOWrapper(io.BytesIO())), \
             redirect_stdout(stdout), redirect_stderr(stderr):
            code = consult.main(args)
        return code, json.loads(stdout.getvalue()), stderr.getvalue()

    def test_success_and_stdin(self):
        code, payload, _ = self.invoke(
            ["-m", "A1", "--prompt", "-"], stdin=io.TextIOWrapper(io.BytesIO(b"question")))
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(len(payload["results"]), 1)

    def test_missing_key_never_opens_wizard(self):
        manager = FakeManager()
        manager.api_key = None
        code, payload, _ = self.invoke(["-m", "A1", "--prompt", "q"], manager)
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"]["code"], "invalid_input")
        self.assertEqual(manager.options, [])

    def test_invalid_arguments_are_json(self):
        code, payload, stderr = self.invoke(["-m", "A1"])
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "failed")
        self.assertIn("--prompt", stderr)

    def test_partial_and_total_failure_exit_codes(self):
        async def fail():
            raise RuntimeError("provider unavailable")
        for clients, expected_code, expected_status in (
            ({"alpha-one": FakeClient(), "alpha-two": FakeClient(fail)}, 3, "partial"),
            ({model: FakeClient(fail) for model in CATALOG}, 1, "failed"),
        ):
            code, payload, _ = self.invoke(["-m", "A1", "A2", "--prompt", "q"], FakeManager(clients))
            self.assertEqual(code, expected_code)
            self.assertEqual(payload["status"], expected_status)

    def test_actual_entry_point_and_help(self):
        root = Path(__file__).resolve().parents[1]
        for args in (["--help"], ["consult", "--help"], ["consult"]):
            result = subprocess.run([sys.executable, "-m", "superchat.main"] + args,
                                    cwd=root, capture_output=True, text=True)
            if args == ["consult"]:
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)["status"], "failed")
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("consult", result.stdout)
                if args[0] == "consult":
                    for flag in ("--prompt", "--timeout", "--max-output-tokens", "--format"):
                        self.assertIn(flag, result.stdout)
                    self.assertNotIn("--prompt-file", result.stdout)


if __name__ == "__main__":
    unittest.main()
