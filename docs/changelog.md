# Changelog

## [0.8] - 2025-08-01
- Enhanced CLI with flexible model input: -m k2 lite, -m "lite,k2", or -m lite -m k2
- Added CLI shortcuts to bypass setup mode entirely
- Context history now scales with participants (3x users + agents) instead of fixed 5 messages
- Improved formatting of chat messages

## [0.7] - 2025-07-31
- Added debug mode to show more data about AI messages (-d in CLI and /debug in setup)

## [0.6] - 2025-07-31
- Major architecture refactor of multi agent chat code
	- Refactored into modular components for better maintainability
	- Added modern AutoGen with proper multi-agent support
	- Fixed multi-agent conversations so agents can see and reference each other's responses
- Streamlined system prompts to reduce context usage
- Added conversation history limit of 5 messages to prevent context overflow

## [0.5] - 2025-07-23
- Refactored chat functionality to use AutoGen agents for 1:1 conversations with unified usage tracking
- Added intelligent fuzzy matching for model selection with auto-selection
- Improved model selection UX - supports natural language input like "flash lite", "deepseek v3"
- Refactored /model and /remove commands to use shared model resolution logic
- Added Qwen3 Coder model

## [0.4] - 2025-07-23
- Added session statistics tracking with /stats command and exit summary
- Added loading spinner when waiting for AI responses

## [0.3] - 2025-07-23
- Created packaged Python distribution with proper setuptools
- Added more models
- Added dynamic version display on startup
- Enhanced code documentation
- Working 1:1 agent chat functionality