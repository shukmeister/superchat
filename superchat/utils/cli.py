"""CLI utilities for superchat - argument parsing and CLI mode logic."""

import argparse
from superchat.core.session import SessionConfig
from superchat.utils.model_resolver import resolve_model_from_input


def create_parser():
    """Create and configure the argument parser for superchat CLI."""
    parser = argparse.ArgumentParser(
        prog='superchat',
        description='AI-driven discussions and multi-agent debates',
        usage='superchat [-h] [-m|--model MODEL] [-d|--debug] [-v|--voice] [-f|--flow FLOW]'
    )
    
    parser.add_argument(
        '--model', '-m',
        nargs='*',
        action='append',
        metavar='MODEL',
        help='Add models to the chat. Examples: -m k2 lite (space-separated), -m "lite,k2" (comma-separated), -m lite -m k2 (multiple flags)'
    )

    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug mode with detailed message and token tracking (-d or --debug)'
    )

    parser.add_argument(
        '--voice', '-v',
        action='store_true',
        help='Enable voice output mode (-v or --voice)'
    )
    
    parser.add_argument(
        '--flow', '-f',
        choices=['default', 'staged'],
        metavar='FLOW',
        help='Set chat flow mode: default or staged. Examples: -f staged, --flow default'
    )
    
    return parser


def parse_model_arguments(model_args):
    """Parse model arguments supporting space-separated, comma-separated, and multiple -m flags.
    
    Args:
        model_args: List from argparse with nargs='*' + action='append' 
                   (nested lists from multiple -m flags)
        
    Returns:
        List of individual model names with whitespace stripped
        
    Examples:
        [["lite", "k2"]] -> ["lite", "k2"]                    # -m lite k2
        [["lite,k2"]] -> ["lite", "k2"]                      # -m "lite,k2"  
        [["lite"], ["k2"]] -> ["lite", "k2"]                 # -m lite -m k2
        [["lite", "k2"], ["deepseek"]] -> ["lite", "k2", "deepseek"]  # -m lite k2 -m deepseek
    """
    if not model_args:
        return []
    
    # Flatten nested lists from nargs='*' + action='append'
    flattened_models = []
    for arg_group in model_args:
        if isinstance(arg_group, list):
            # Handle space-separated values from single -m flag
            for arg in arg_group:
                # Also handle comma-separated values within each argument
                models = [model.strip() for model in arg.split(',')]
                # Filter out empty strings
                models = [model for model in models if model]
                flattened_models.extend(models)
        else:
            # Handle single string (shouldn't happen with nargs='*' but be safe)
            models = [model.strip() for model in str(arg_group).split(',')]
            models = [model for model in models if model]
            flattened_models.extend(models)
    
    return flattened_models


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
    
    # Parse comma-separated models
    parsed_models = parse_model_arguments(model_inputs)
    
    resolved_models = []
    errors = []
    models_config = model_manager.models_config
    
    for model_input in parsed_models:
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
    parsed_models = parse_model_arguments(args.model)
    if len(resolved_models) != len(parsed_models):
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
    
    # Set chat flow if specified
    if args.flow:
        config.set_chat_flow(args.flow)
    
    return config