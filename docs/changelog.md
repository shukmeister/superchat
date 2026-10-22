# Changelog

## [Unreleased] - 2026-10-01
- Added offline `superchat models` discovery with text or JSON output, accepted
  model IDs, capability details, and catalog prices in USD per million tokens.
- Corrected DeepSeek V4.1 Flash catalog rates to $0.30 input / $1.20 output per
  million tokens after checking the live OpenRouter catalog on 2026-10-22.
- Added `superchat consult` for stateless parallel panel requests with explicit
  prompt or stdin input, JSON results, per-model usage and cost estimates,
  configurable timeouts and output limits, and partial-failure handling.
- Updated CLI help and documented programmatic consultations.
- Declared the directly used `httpx` dependency for clean installations.
- Refreshed the model roster against [OpenRouter's live catalog](https://openrouter.ai/api/v1/models):
  - DeepSeek V4 Flash → V4.1 Flash; V4 Pro → V4 Pro 0813 (GA).
  - Grok 4.3 → 4.7.
  - Gemini 2.5 Flash Lite → 3.5 Flash Lite; Gemini 3.5 Flash → 3.8 Flash.
  - MiMo V2.5 → V2.6 Flash; Qwen3 Coder → Qwen3 Coder Next.
- Consolidated older Kimi entries into Kimi K3 and older Gemini Flash entries into Gemini 3.8 Flash.
- Verified Kimi K3, DeepSeek R1 0528, Llama 4 Maverick, and Gemini 3.1 Pro Preview are the latest in their respective lines.
- Updated all model prices, catalog dates, context lengths, and capability flags from OpenRouter. Prices are catalog rates per million tokens; provider and tier-specific rates may differ.
- Updated CLI examples to use the current model roster.

## [0.11] - 2025-11-25
- Updated `gemini-2.5-pro` to `gemini-3-pro-preview`

## [0.10] - 2025-08-12
- Added interactive API key setup wizard for seamless onboarding
- Added graceful error handling for OpenRouter credits errors
- Number of debate rounds is now configurable with the /rounds command in setup mode, or with -r/--rounds as a CLI variable
- Improved labeling of each model name in chats
- Improved usage examples in README

## [0.9] - 2025-08-04
- Added staged chat flow system with 1:1 conversations followed by team debate
	- Implemented /promote command to advance through agents in staged mode
- Enhanced terminal input to handle multi-line prompts

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
