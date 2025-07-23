# superchat

AI-driven discussions and multi-agent debates. A terminal-based CLI application for communicating with multiple AI models through OpenRouter's API.

## Features

- Interactive chat with any open source AI model on OpenRouter
- Add multiple agents to a chat to start a debate between agents

## Installation

This is a private package. To install:

1. Ensure you have access to this repository
2. Install directly from Git:

```bash
pip install git+https://github.com/shukmeister/superchat.git
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
pip install --upgrade git+https://github.com/shukmeister/superchat.git
```