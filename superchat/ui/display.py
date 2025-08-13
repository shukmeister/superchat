"""Display functions and setup loop for the superchat UI.

This module handles all the visual elements and user interaction before starting a chat.
It's the "setup wizard" that helps users configure their session.

Key responsibilities:
- Display the ASCII art banner and session info
- Run the interactive setup loop (where users type /model, /start, etc.)
- Process setup commands and validate user input
- Check API key availability before allowing chat to start
- Provide help and error messages during setup

Think of it as the app's "front desk" - it greets users, helps them get set up,
and hands them off to the chat system once everything is configured properly.
"""

from superchat.utils.parser import parse_input
from superchat.utils.identifiers import get_model_identifier
from superchat.utils.model_resolver import resolve_model_from_input, get_available_models_list, get_display_name
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager
from importlib.metadata import version

def display_banner():
    """Display the ASCII art banner."""
    banner = """
 ______   __  __   ______  ______   ______   ______   __  __   ______   ______  
/\\  ___\\ /\\ \\/\\ \\ /\\  == \\/\\  ___\\ /\\  == \\ /\\  ___\\ /\\ \\_\\ \\ /\\  __ \\ /\\__  _\\ 
\\ \\___  \\\\ \\ \\_\\ \\\\ \\  _-/\\ \\  __\\ \\ \\  __< \\ \\ \\____\\ \\  __ \\\\ \\  __ \\\\/_/\\ \\/ 
 \\/\\_____\\\\ \\_____\\\\ \\_\\   \\ \\_____\\\\ \\_\\ \\_\\\\ \\_____\\\\ \\_\\ \\_\\\\ \\_\\ \\_\\  \\ \\_\\ 
  \\/_____/ \\/_____/ \\/_/    \\/_____/ \\/_/ /_/ \\/_____/ \\/_/\\/_/ \\/_/\\/_/   \\/_/ 
                                                                                
"""
    print(banner)



def setup_loop(debug_enabled=False, initial_flow=None, initial_rounds=None):
    """Main setup loop for configuring chat parameters."""
    display_banner()
    
    # Initialize debug logger with CLI flag
    from superchat.utils.debug import initialize_debug_logger
    initialize_debug_logger(debug_enabled)
    
    # Initialize session config and model client manager
    config = SessionConfig(debug_enabled=debug_enabled)
    
    # Apply initial CLI arguments
    if initial_flow:
        config.set_chat_flow(initial_flow)
    if initial_rounds and initial_rounds != 1:
        config.set_debate_rounds(initial_rounds)
    model_manager = ModelClientManager()
    
    # Check for API key on startup
    if not model_manager.validate_setup():
        print()
        return None
    
    # Get available models
    available_models = model_manager.get_available_models()
    
    print(f"Version v{version('superchat')}\n")
    print("Configure your session before starting")
    print("Type /help for commands")
    print()
    
    while True:
        try:
            user_input = input("> ")
            parsed = parse_input(user_input)
            
            if parsed['type'] == 'empty':
                continue
            
            if parsed['type'] == 'message':
                print()
                print("Not in chat mode yet. Use commands to configure session.")
                print()
                continue
                
            # Handle commands
            command = parsed['command']
            args = parsed['args']
            
            if command == "exit":
                print()
                print("Terminating connection")
                return None
                
            elif command == "start":
                if not config.is_valid_for_start():
                    print()
                    print("Please select at least one model first using /model")
                    print()
                    continue
                print()  # Add line break after /start command
                config.start_session()
                return config
                
            elif command == "help":
                print()
                print("Available commands:")
                print("  /model <name> - Add a model to the chat")
                print("  /model <name1, name2, name3> - Add multiple models at once")
                print("  /remove <name> - Remove a model from the chat")
                print("  /list - Show available models")
                print("  /status - Show current configuration")
                print("  /flow <default|staged> - Set chat flow mode")
                print("  /rounds <1-5> - Set number of debate rounds for multi-agent conversations")
                print("  /debug - Toggle debug mode for detailed message/token tracking")
                print("  /start - Begin the chat session")
                print("  /help - Show this help")
                print("  /exit - Exit superchat")
                print()
                print("Examples:")
                print("  /model v3, flash lite, k2")
                print("  /model deepseek")
                print("  /flow staged")
                print("  /rounds 3")
                print()
                print("Chat commands (available after /start):")
                print("  /stats - Show session statistics")
                print("  /exit - Exit superchat")
                print()
                print("CLI shortcuts (skip setup entirely):")
                print("  superchat -m k2 lite              # Space-separated models")
                print("  superchat -m \"lite,k2\"            # Comma-separated models")
                print("  superchat -m lite -m k2           # Multiple -m flags")
                print("  superchat --flow staged -m k2     # Set flow and models")
                print()
                
            elif command == "list":
                print()
                print("Available models:")
                print()
                for model_name in available_models:
                    model_config = model_manager.get_model_config(model_name)
                    if model_config:
                        company = model_config.get("company", "")
                        family = model_config.get("family", "")
                        model = model_config.get("model", "")
                        release = model_config.get("release", "")
                        description = model_config.get("description", "")
                        full_name = model_manager.get_model_display_name(model_name)
                        input_cost = model_config.get("input_cost", "N/A")
                        output_cost = model_config.get("output_cost", "N/A")
                        context_length = model_config.get("context_length", "N/A")
                        
                        # Format context length 
                        if context_length != "N/A":
                            if context_length >= 1000:
                                context_str = f"{context_length // 1000}k tokens"
                            else:
                                context_str = f"{context_length} tokens"
                        else:
                            context_str = "N/A"
                        
                        print(f"- {full_name}:")
                        if description:
                            print(f"    {description}")
                        print(f"    Input   ${input_cost}/M")
                        print(f"    Output  ${output_cost}/M")
                        print(f"    Context {context_str}")
                        print()
                    else:
                        print(f"- {model_name}")
                        print()
                print()
                
            elif command == "status":
                print()
                print("Configuration:")
                print()
                print("- Models:")
                if config.models:
                    for i, model_key in enumerate(config.models):
                        identifier = get_model_identifier(i)
                        display_name = model_manager.get_model_display_name(model_key)
                        print(f"  - {identifier}: {display_name}")
                else:
                    print("  - No models selected")
                
                # Show chat flow mode
                print(f"- Chat flow: {config.get_chat_flow()}")
                
                # Show debate rounds
                print(f"- Debate rounds: {config.get_debate_rounds()}")
                
                # Show debug mode status
                debug_status = "enabled" if config.debug_enabled else "disabled"
                print(f"- Debug mode: {debug_status}")
                print()
                
            elif command == "model":
                if len(args) < 1:
                    print()
                    print("Usage: /model <name1, name2, name3> or /model <name>")
                    print("Examples:")
                    print("  /model v3, flash lite, k2")
                    print("  /model deepseek")
                    available_models_list = get_available_models_list(model_manager)
                    print(f"Available models: {available_models_list}")
                    print()
                    continue
                
                user_input = " ".join(args)
                
                # Check if input contains commas for multi-model selection
                if ',' in user_input:
                    # Split by commas and process each model
                    model_inputs = [model_input.strip() for model_input in user_input.split(',')]
                    print()
                    added_models = []
                    already_selected = []
                    not_found = []
                    
                    for model_input in model_inputs:
                        if not model_input:  # Skip empty strings
                            continue
                            
                        # Resolve each model using helper function
                        result = resolve_model_from_input(model_input, model_manager.models_config)
                        
                        if result.action_type == "selected":
                            model_key = result.model_key
                            if config.add_model(model_key):
                                display_name = model_manager.get_model_display_name(model_key)
                                added_models.append(display_name)
                            else:
                                display_name = model_manager.get_model_display_name(model_key)
                                already_selected.append(display_name)
                        else:
                            not_found.append(f"'{model_input}' - {result.message}")
                    
                    # Display results summary
                    if added_models:
                        print(f"Added models: {', '.join(added_models)}")
                    if already_selected:
                        print(f"Already selected: {', '.join(already_selected)}")
                    if not_found:
                        print("Not found:")
                        for error in not_found:
                            print(f"  {error}")
                        available_models_list = get_available_models_list(model_manager)
                        print(f"\nAvailable models: {available_models_list}")
                    print()
                else:
                    # Single model selection (existing logic)
                    result = resolve_model_from_input(user_input, model_manager.models_config)
                    
                    if result.action_type == "selected":
                        model_key = result.model_key
                    elif result.action_type == "suggest":
                        print()
                        print(result.message)
                        print()
                        continue
                    else:  # not_found
                        print()
                        print(result.message)
                        available_models_list = get_available_models_list(model_manager)
                        print(f"Available models: {available_models_list}")
                        print()
                        continue
                    
                    if config.add_model(model_key):
                        print()
                        display_name = model_manager.get_model_display_name(model_key)
                        print(f"Added model: {display_name}")
                        print()
                    else:
                        print()
                        display_name = model_manager.get_model_display_name(model_key)
                        print(f"Model {display_name} already selected")
                        print()
            
            elif command == "remove":
                if len(args) < 1:
                    print()
                    print("Usage: /remove <name>")
                    if config.models:
                        selected_names = []
                        for model_key in config.models:
                            display_name = model_manager.get_model_display_name(model_key)
                            selected_names.append(display_name)
                        print(f"Currently selected: {', '.join(selected_names)}")
                    else:
                        print("No models currently selected")
                    print()
                    continue
                user_input = " ".join(args)
                
                # Create a subset of models config with only selected models
                selected_models_config = {"models": {}}
                for model_key in config.models:
                    if model_key in model_manager.models_config["models"]:
                        selected_models_config["models"][model_key] = model_manager.models_config["models"][model_key]
                
                # Resolve model using helper function
                result = resolve_model_from_input(user_input, selected_models_config, "current configuration")
                
                if result.action_type == "selected":
                    model_key = result.model_key
                elif result.action_type == "suggest":
                    print()
                    print(result.message)
                    print()
                    continue
                else:  # not_found
                    print()
                    print(result.message)
                    print()
                    continue
                
                if config.remove_model(model_key):
                    print()
                    display_name = model_manager.get_model_display_name(model_key)
                    print(f"Removed model: {display_name}")
                    print()
                else:
                    print()
                    display_name = model_manager.get_model_display_name(model_key)
                    print(f"Model {display_name} was not in configuration")
                    print()
            
            elif command == "debug":
                # Toggle debug mode
                current_debug = config.debug_enabled
                config.set_debug_enabled(not current_debug)
                print()
                if config.debug_enabled:
                    print("Debug mode: enabled")
                    print("You will see detailed message and token information during chat.")
                else:
                    print("Debug mode: disabled")
                print()
                
            elif command == "flow":
                if len(args) < 1:
                    print()
                    print("Usage: /flow <default|staged>")
                    print("  default - Default chat flow")
                    print("  staged  - Staged chat flow")
                    print()
                    print(f"Current flow: {config.get_chat_flow()}")
                    print()
                    continue
                
                flow_type = args[0].lower()
                if flow_type in ["default", "staged"]:
                    if config.set_chat_flow(flow_type):
                        print()
                        if flow_type == "default":
                            print("Chat flow: default")
                        else:
                            print("Chat flow: staged")
                        print()
                    else:
                        print()
                        print("Failed to set chat flow")
                        print()
                else:
                    print()
                    print("Invalid flow type. Use 'default' or 'staged'")
                    print("  default - Default chat flow")
                    print("  staged  - Staged chat flow")
                    print()
                    
            elif command == "rounds":
                if len(args) < 1:
                    print()
                    print("Usage: /rounds <1-5>")
                    print("  Set number of debate rounds for multi-agent conversations")
                    print("  Only affects debates (multi-agent mode)")
                    print()
                    print(f"Current rounds: {config.get_debate_rounds()}")
                    print()
                    continue
                
                try:
                    rounds = int(args[0])
                    if config.set_debate_rounds(rounds):
                        print()
                        print(f"Debate rounds: {rounds}")
                        print()
                    else:
                        print()
                        print("Invalid rounds value. Must be between 1 and 5.")
                        print()
                except ValueError:
                    print()
                    print("Invalid rounds value. Must be a number between 1 and 5.")
                    print()
                    
            elif command == "stats":
                print()
                print("The /stats command is only available during chat sessions.")
                print()
                    
            else:
                print()
                print(f"Unknown command: /{command}")
                print("Type /help for available commands")
                print()
                
        except KeyboardInterrupt:
            print("\nTerminating connection")
            return None
        except EOFError:
            print("\nTerminating connection")
            return None