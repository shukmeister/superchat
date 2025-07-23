# superchat

AI-driven discussions and multi-agent debates. A terminal-based CLI application for communicating with multiple AI models through OpenRouter's API.

## Features

- Interactive chat with any open source AI model on OpenRouter
- Add multiple agents to a chat to start a debate between agents

## Installation

This is only tested on zsh on macOS. To install:

```bash
pip install --user git+https://github.com/shukmeister/superchat.git
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

```bash
pip install --upgrade --user git+https://github.com/shukmeister/superchat.git
```

## Roadmap

Planned features:

```
- Web search
- Multi agent debate
- CLI flag shortcuts
- Prompt caching
- Image processing
- Voice mode
```
