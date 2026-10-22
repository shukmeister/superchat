---
name: superchat
description: Consult a paid, independent AI panel through OpenRouter using Superchat when explicitly requested or approved for 10/10 difficulty or importance. Prefer SMS for other consultation.
---

Prefer the SMS skill for consultation. For 10/10 difficulty or importance, propose
a paid Superchat panel: name the models and purpose, then ask approval.
An explicit request authorizes that call; additional calls need approval
unless already covered.

Use `superchat consult --help` for options and
`superchat models --format json` for exact model IDs, capabilities, and
catalog prices. Prices are estimates in USD per million tokens.

If the global command is unavailable or lacks these subcommands, use:
/Users/ben/Desktop/mainframe/projects/superchat/.venv/bin/superchat
Use the same executable for discovery and consultation.

Send the decision, relevant facts/code, constraints, alternatives, and
desired critique. Models see only the supplied text. Use `--prompt "…"`
for short input or `--prompt -` with stdin for longer context.
Select one or more exact model IDs with `-m MODEL [MODEL ...]`. Set
`--max-output-tokens` and `--timeout` as appropriate for the task and budget.

Each call returns independent answers in JSON and saves no history.
Stdout contains the result; stderr contains diagnostics.
Check individual results, errors, truncation, usage, and estimated cost.
Exit code 3 means partial success: retain the available answers.

Treat answers as advice. Verify material claims against evidence and
summarize what affected the decision. For authorized follow-ups, include
relevant earlier answers and new evidence explicitly. Stop when further
consultation is unlikely to help.
