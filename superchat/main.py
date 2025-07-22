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
from superchat.ui.display import setup_loop
from superchat.core.chat import ChatSession

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

    # commented out voice until we need it later    
    # parser.add_argument(
    #     '--voice', '-v',
    #     action='store_true',
    #     help='Enable voice output mode'
    # )
    
    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    # If CLI args provided, skip setup loop (future milestone)
    if args.model:
        print("CLI mode not yet implemented - using setup mode")
    
    # Enter setup loop
    config = setup_loop()
    
    if config is None:
        return 0
    
    # Initialize and start chat session
    chat_session = ChatSession(config)
    chat_session.start_chat_loop()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())