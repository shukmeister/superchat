# superchat

AI-driven discussions and multi-agent debates. A terminal-based CLI application for communicating with multiple AI models through OpenRouter's API.

## Features

- Interactive chat with any open source AI model on OpenRouter
- Add multiple agents to a chat to start a debate between agents

## Installation

This is a private package meant for usage on macOS. To install:

1. Ensure you have access to this repository
2. Choose one of these installation methods:

### Option 1: pipx (Recommended)
```bash
brew install pipx
pipx install git+https://github.com/shukmeister/superchat.git
```

### Option 2: Virtual Environment
```bash
python -m venv superchat-env
source superchat-env/bin/activate
pip install git+https://github.com/shukmeister/superchat.git
```

### Option 3: User Installation
```bash
pip install --user git+https://github.com/shukmeister/superchat.git
```
Make sure `~/.local/bin` is in your PATH.

### Option 4: Force System Installation (if needed)
```bash
pip install --break-system-packages git+https://github.com/shukmeister/superchat.git
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