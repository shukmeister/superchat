# superchat

AI-driven discussions and multi-agent debates. A terminal-based CLI application for communicating with multiple AI models through OpenRouter's API.

## Features

- Interactive chat with any open source AI model on OpenRouter
- Add multiple agents to a chat to start a debate between agents

## Installation

This is a private package meant for usage on macOS. To install:

1. Go to the [Releases page](https://github.com/shukmeister/superchat/releases)
2. Download the latest `superchat-X.X-py3-none-any.whl` file
3. Install using pip:

```bash
pip install --user superchat-X.X-py3-none-any.whl
```

Make sure `~/.local/bin` is in your PATH for the `superchat` and `sc` commands to work.

## Usage

After installation, run from any terminal:

```bash
superchat
```

Or use the short alias:

```bash
sc
```

## Requirements

- Python 3.8+
- OpenRouter API key (get one at https://openrouter.ai/keys)

## Configuration

Create a `.env` file or set environment variables with your OpenRouter API key:

```
OPENROUTER_API_KEY=your_key_here
```

Or place your API key in `~/.superchat/config`.

## Updating

To update to the latest version:

1. Download the latest wheel file from the [Releases page](https://github.com/shukmeister/superchat/releases)
2. Uninstall the current version: `pip uninstall superchat`
3. Install the new version: `pip install --user superchat-X.X-py3-none-any.whl`