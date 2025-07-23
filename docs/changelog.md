# Changelog

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