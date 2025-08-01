#!/usr/bin/env python3
"""Main entry point for superchat - AI-driven discussions and multi-agent debates.

This is where everything starts. It's the app's "front door" that processes command line
arguments and kicks off the setup process.

Key responsibilities:
- Parse command line arguments (--model, --voice flags, etc.)
- Initialize the setup loop where users configure their session
- Eventually handle direct CLI shortcuts (like starting with models pre-selected)
- Pass control to the appropriate components (setup UI, then chat system)

Think of it as the app's "receptionist" - it greets you when you run superchat,
figures out what you want to do, and routes you to the right place.
"""

import argparse
import sys
from superchat.ui.display import setup_loop, display_banner
from superchat.core.chat import ChatSession
from superchat.core.setup import ChatSetup
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager
from superchat.utils.model_resolver import resolve_model_from_input
from importlib.metadata import version

def create_parser():
    parser = argparse.ArgumentParser(
        prog='superchat',
        description='AI-driven discussions and multi-agent debates'
    )
    
    parser.add_argument(
        '--model', '-m',
        action='append',
        help='Add a model to the chat (can be used multiple times)'
    )

    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug mode for detailed message and token tracking'
    )

    parser.add_argument(
        '--voice', '-v',
        action='store_true',
        help='Enable voice output mode'
    )
    
    return parser


def resolve_cli_models(model_inputs, model_manager):
    """Resolve CLI model arguments using fuzzy logic.
    
    Args:
        model_inputs: List of model strings from --model flags
        model_manager: ModelClientManager instance
        
    Returns:
        tuple: (success: bool, resolved_models: list, errors: list)
    """
    if not model_inputs:
        return False, [], []
    
    resolved_models = []
    errors = []
    models_config = model_manager.models_config
    
    for model_input in model_inputs:
        result = resolve_model_from_input(model_input, models_config)
        
        if result.action_type == "selected":
            resolved_models.append(result.model_key)
        elif result.action_type == "suggest":
            errors.append(result.message)
        else:  # not_found
            errors.append(result.message)
    
    # Success if all models were resolved (no errors)
    success = len(errors) == 0
    return success, resolved_models, errors


def should_use_cli_mode(args, resolved_models, success):
    """Determine if we can skip setup and go direct to chat.
    
    Args:
        args: Parsed command line arguments
        resolved_models: List of resolved model keys
        success: Whether all models were successfully resolved
        
    Returns:
        bool: True if we should bypass setup loop
    """
    # Must have model arguments to use CLI mode
    if not args.model:
        return False
    
    # All models must be successfully resolved (no errors)
    if not success or not resolved_models:
        return False
    
    # Number of resolved models must match number of input models
    if len(resolved_models) != len(args.model):
        return False
    
    return True


def create_cli_config(args, resolved_models):
    """Create session configuration directly from CLI arguments.
    
    Args:
        args: Parsed command line arguments
        resolved_models: List of resolved model keys
        
    Returns:
        SessionConfig: Configured session ready for chat
    """
    config = SessionConfig(debug_enabled=args.debug)
    
    # Add resolved models
    for model_key in resolved_models:
        config.add_model(model_key)
    
    # Set voice mode if specified
    if args.voice:
        config.set_voice_enabled(True)
    
    return config


def main():
    parser = create_parser()
    args = parser.parse_args()
    
    config = None
    
    # Try CLI mode if model arguments provided
    if args.model:
        # Initialize model manager for fuzzy resolution
        model_manager = ModelClientManager()
        
        # Resolve CLI model arguments using existing fuzzy logic  
        success, resolved_models, errors = resolve_cli_models(args.model, model_manager)
        
        if should_use_cli_mode(args, resolved_models, success):
            # Direct CLI mode - create config and start chat
            
            # Display banner and version (same as setup mode)
            display_banner()
            print(f"Version v{version('superchat')}\n")
            
            # Initialize debug logger for CLI mode
            if args.debug:
                from superchat.utils.debug import initialize_debug_logger
                initialize_debug_logger(args.debug)
            
            config = create_cli_config(args, resolved_models)
            if args.voice:
                print("Voice mode enabled")
            if args.debug:
                print("Debug mode enabled")
        else:
            # CLI mode failed - show errors and fall back to setup mode
            print("Unable to resolve all models from CLI arguments:")
            for error in errors:
                print(f"  {error}")
            print("\nEntering interactive setup mode...\n")
            config = setup_loop(debug_enabled=args.debug)
    else:
        # No CLI args - use normal setup loop
        config = setup_loop(debug_enabled=args.debug)
    
    if config is None:
        return 0
    
    # Initialize chat session with pre-configured components
    chat_session = ChatSession(config)
    
    # Use ChatSetup to configure all components
    setup = ChatSetup(config)
    message_handler = setup.setup_complete_session()
    chat_session.set_message_handler(message_handler)
    
    # Start the chat loop
    chat_session.start_chat_loop()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())