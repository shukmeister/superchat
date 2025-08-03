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

## Getting Your API Key

Before using superchat, you need an OpenRouter API key:

1. Go to https://openrouter.ai/keys
2. Sign up for a free account
3. Create a new API key
4. Copy the key (starts with `sk-or-`)

## Configuration

Replace `ADD-YOUR-KEY-HERE` with your real API key and run:

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
