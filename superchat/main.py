#!/usr/bin/env python3

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