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
superchat -m llama claude deepseek
```

#### Staged Mode
In staged mode, you first have individual 1:1 conversations with each agent, then transition to a team debate with shared context from all conversations.

```bash
# Start staged mode with multiple models
superchat --flow staged -m llama claude deepseek
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
superchat -r 3 -m llama claude
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
