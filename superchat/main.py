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

import sys
from superchat.ui.display import setup_loop, display_banner
from superchat.core.chat import ChatSession
from superchat.core.setup import ChatSetup
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager
from superchat.utils.cli import create_parser, resolve_cli_models, should_use_cli_mode, create_cli_config
from importlib.metadata import version


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
            if args.flow:
                print(f"Chat flow: {args.flow}")
        else:
            # CLI mode failed - show errors and fall back to setup mode
            print("Unable to resolve all models from CLI arguments:")
            for error in errors:
                print(f"  {error}")
            print("\nEntering interactive setup mode...\n")
            config = setup_loop(debug_enabled=args.debug)
    else:
        # No CLI args - use normal setup loop, but pass flow if specified
        config = setup_loop(debug_enabled=args.debug)
        # If flow was specified via CLI but no models, apply it to the setup config
        if config and args.flow:
            config.set_chat_flow(args.flow)
    
    if config is None:
        return 0
    
    # Start the session timer
    config.start_session()
    
    # Initialize chat session with pre-configured components
    chat_session = ChatSession(config)
    
    # Use ChatSetup to configure all components
    setup = ChatSetup(config)
    setup_result = setup.setup_complete_session()
    chat_session.set_message_handler(setup_result['message_handler'])
    
    # Set up staged flow manager if needed
    chat_session.setup_staged_flow_manager(setup_result['agents'], setup_result['agent_mapping'])
    
    # Set up command handler
    chat_session.setup_command_handler()
    
    # Start the chat loop
    chat_session.start_chat_loop()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())