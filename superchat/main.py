#!/usr/bin/env python3

import argparse
import sys

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
    
    print("superchat CLI stub - args:", args)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())