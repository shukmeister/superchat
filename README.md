# superchat

AI-driven discussions and multi-agent debates. A terminal-based CLI application for communicating with multiple AI models through OpenRouter's API.

## Features

- Interactive chat with any open source AI model on OpenRouter
- Add multiple agents to a chat to start a debate between agents

## Requirements

- **Python 3.8+** - Check with `python3 --version`
- **pip** - Usually comes with Python, check with `pip --version`
- **OpenRouter API key** - Get one at https://openrouter.ai/keys

### Installing missing dependencies on macOS:
- **Python**: `brew install python` or download from python.org

## Installation

**Install superchat with one command**

```bash
pip install superchat
```

**Test that it worked**

```bash
superchat --help
```

If you see a dialog with instructions, then you're ready to use superchat

**If `superchat command isn't found`**:

Run this command to add the install location to your PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

## Configuration

You'll need an OpenRouter API key to use superchat. The program will guide you through this setup automatically on first run.

**Getting your API key:**

1. Go to https://openrouter.ai/keys
2. Sign up for a free account
3. Create a new API key (starts with `sk-or-`)
4. Add credits to your account at https://openrouter.ai/credits

**Setup:**

When you first run superchat, it will detect that you don't have an API key and automatically prompt you to enter it. The key will be securely saved to your `~/.env` file for future use.

**Manual Setup (Optional):**

If you prefer to set up the API key manually:

```bash
echo "OPENROUTER_API_KEY=ADD-YOUR-KEY-HERE" > ~/.env
```

## Usage

After installation, run from any terminal:

```bash
superchat
```

Or use the short alias:

```bash
sc
```

### Debate Modes

Superchat supports two different debate modes when using multiple AI models:

#### Default Mode
In default mode, all AI agents join a shared conversation immediately. Each user message triggers responses from all agents in a round-robin format.

```bash
# Start default mode with multiple models
superchat -m llama k3 grok
```

#### Staged Mode
In staged mode, you first have individual 1:1 conversations with each agent, then transition to a team debate with shared context from all conversations.

```bash
# Start staged mode with multiple models
superchat --flow staged -m llama k3 grok
```

**Staged Mode Commands:**
- `/promote` - Promote current agent to team debate and move to next agent

**Staged Mode Benefits:**
- Get individual perspectives before group discussion
- Agents share context from 1:1 conversations in team phase

### Debate Rounds

Control how many times each agent responds per user message in team debates:

```bash
# Set debate rounds (1-5, default: 1)
superchat -r 3 -m llama k3
```

### Consult a panel from another program

Discover accepted model IDs and prices before choosing a panel:

```sh
superchat models
superchat models --format json
```

These commands work offline without an API key. JSON includes each model's key,
OpenRouter ID, description, context length, capability flags, and separate input
and output costs in USD per million tokens. Prices come from the bundled catalog;
live provider availability and billing rates can differ. Use the exact `model`
key or `openrouter_id` in `consult -m` to avoid ambiguous aliases.

`consult` sends the same prompt to each selected model independently and in
parallel, returns one JSON document, and exits. Each call is stateless: no
conversation or prompt is saved. Include previous answers in a new prompt when
you want a follow-up. Models do not see each other's answers or local files.

```sh
superchat consult \
  -m k3 grok \
  --prompt "Compare approaches A and B. Identify their main risks."
```

For longer text and code, use `--prompt -` to read UTF-8 stdin until EOF:

```sh
superchat consult -m k3 grok --prompt - <<'PROMPT'
Review this design and identify failure modes.

Constraints:
- Existing sessions must continue working.
- One failed model must not discard other models' answers.
PROMPT
```

From Python, pass input directly without temporary files:

```python
import json
import subprocess

result = subprocess.run(
    ["superchat", "consult", "-m", "k3", "grok", "--prompt", "-"],
    input="Review this design:\n...",
    text=True,
    encoding="utf-8",
    capture_output=True,
)
panel = json.loads(result.stdout)
for answer in panel["results"]:
    if answer["status"] == "success":
        print(answer["model"], answer["answer"])
    else:
        print(answer["model"], answer["error"])
```

Input and configuration:

- `--prompt` is required. Use text or `-`; there is no prompt-file option.
  Stdin is read only with `--prompt -`; terminal input is rejected.
- Input must be valid UTF-8, nonempty, and no larger than 1 MiB (1,048,576 bytes).
- `-m` is required and accepts one or more catalog keys, OpenRouter IDs, or
  unambiguous aliases such as `k3`. Commas and repeated `-m` flags also work.
  Unknown, ambiguous, or duplicate selections fail before requests start.
- Set `OPENROUTER_API_KEY` in the environment or a dotenv file before running.
  Consult never opens the interactive API key wizard.
- `--timeout SECONDS` limits each model request (default: 120). Timed-out requests
  are cancelled locally; client cleanup can take up to five additional seconds.
- `--max-output-tokens N` sets a per-model output limit. When omitted, the
  provider default applies. A `finish_reason` of `length` indicates truncation.
- Requests use the same provider privacy preferences as interactive chat.
  Automatic retries are disabled.

Output is JSON by default; `--format json` is also accepted. Stdout contains only
the result document; diagnostics go to stderr. `--help` prints normal help text.
The result has `schema_version: 1`, an overall `status` (`success`, `partial`, or
`failed`), a `results` array in selection order, `elapsed_seconds`, and `error`.
Top-level `error` describes input or command failures; model failures appear in
the relevant result's `error` instead.

Each model result contains:

- `model`, `openrouter_id`, and `status` (`success` or `failed`).
- `answer` and `finish_reason`, or `null` when unavailable.
- `usage`: provider-reported `prompt_tokens`, `completion_tokens`, and
  `total_tokens`, or `null` when unavailable.
- `estimated_cost_usd`: cost calculated from that model's reported usage and
  bundled catalog rates, or `null` when unavailable. Actual billing can differ.
- `elapsed_seconds` and `error` (a `code` and `message`, or `null` on success).

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Every selected model returned a text answer |
| `1` | All models failed, or an internal error occurred |
| `2` | Invalid arguments, input, or configuration |
| `3` | Some models succeeded; use the available answers |
| `130` | Interrupted |

For partial results, inspect the JSON even though the exit code is nonzero. Each
model error identifies a `timeout`, `provider_error`, or `invalid_response`.

Run `superchat consult --help` for options. The existing `superchat` and `sc`
interactive commands remain available.

## Development checks

After installing the project dependencies, run the consultation tests with:

```sh
python -m unittest discover -s tests -v
```

The tests use mocked provider responses and do not require API credits.

## Model and skill maintenance

As of **2026-10-22**, `superchat consult` has **no default panel**: each call
must select models with `-m`. The repository's bundled catalog contains:

| Catalog key | OpenRouter model ID |
| --- | --- |
| `kimi-k3` | `moonshotai/kimi-k3` |
| `deepseek-v4.1-flash` | `deepseek/deepseek-v4.1-flash` |
| `deepseek-v4-pro` | `deepseek/deepseek-v4-pro-0813` |
| `deepseek-r1` | `deepseek/deepseek-r1-0528` |
| `grok-4.7` | `x-ai/grok-4.7` |
| `llama-4-maverick` | `meta-llama/llama-4-maverick` |
| `gemini-3.5-flash-lite` | `google/gemini-3.5-flash-lite` |
| `gemini-3.8-flash` | `google/gemini-3.8-flash` |
| `gemini-3.1-pro-preview` | `google/gemini-3.1-pro-preview` |
| `mimo-v2.6-flash` | `xiaomi/mimo-v2.6-flash` |
| `qwen3-coder-next` | `qwen/qwen3-coder-next` |

This is a snapshot of local configuration, not a live availability or pricing
check. Use `superchat models --format json` to inspect the installed catalog.
Review model IDs, capabilities, and prices periodically against OpenRouter;
update `superchat/config/models.json`, examples, and tests when they change.
Reconsider routinely selected panels as quality and cost change. If a default
panel is introduced later, document its models and review date explicitly.

The companion SMS tool currently defaults to Codex `gpt-6-astra` at low effort
for Claude initiators and Claude `claude-opus-5-5` at low effort for Codex
initiators. Those defaults may also need updating as models and CLIs change.

Both **Codex and Claude Code** use the Superchat and SMS skills. Superchat's
source is `skills/superchat/SKILL.md`; after edits, keep both its description
and instructions identical in the installed copies:

- Codex: `~/.codex/skills/superchat/SKILL.md`.
- Claude Code: `~/.claude/skills/superchat/SKILL.md`.

SMS source is `skills/sms/SKILL.md` in the SMS repository. Rebuild/install SMS
and run `sms install-skill` to refresh both harnesses from its embedded copy.
Periodically compare both skills with their sources and current CLI behavior.
Review the consultation rules in `~/.codex/AGENTS.md` and
`~/.claude/CLAUDE.md` together: SMS for difficulty or importance around 7–9/10,
stalled progress, or consequential decisions needing a second opinion;
Superchat for explicit requests or proposed 10/10 panels where several
independent perspectives would materially help, with approval for paid calls.
Review after model, CLI, or policy changes;
no automatic update is scheduled.

## Updating

To update to the latest version:

```bash
pip install --upgrade superchat
```

## Roadmap

Planned features:

```
- Web search
- Image processing
- Voice mode
```
