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

def setup_loop():
    """Main setup loop for configuring chat parameters."""
    display_banner()
    
    # Initialize session config and model client manager
    config = SessionConfig()
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
                if len(config.models) > 1:
                    print()
                    print("Error: /start requires exactly one model. Multiple models not supported yet.")
                    print(f"Currently selected: {', '.join(config.models)}")
                    print("Use /model to select a single model or wait for multi-agent support.")
                    print()
                    continue
                print()  # Add line break after /start command
                config.start_session()
                return config
                
            elif command == "help":
                print()
                print("Available commands:")
                print("  /model <name> - Add a model to the chat")
                print("  /remove <name> - Remove a model from the chat")
                print("  /list - Show available models")
                print("  /status - Show current configuration")
                print("  /start - Begin the chat session")
                print("  /help - Show this help")
                print("  /exit - Exit superchat")
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
                        full_name = f"{family} {model} {release}".strip()
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
                if config.models:
                    for i, model_key in enumerate(config.models):
                        slot_num = i + 1
                        identifier = get_model_identifier(i)
                        model_config = model_manager.get_model_config(model_key)
                        if model_config:
                            family = model_config.get("family", "")
                            model = model_config.get("model", "")
                            release = model_config.get("release", "")
                            full_name = f"{family} {model} {release}".strip()
                            print(f"- Model {identifier}: {full_name}")
                        else:
                            print(f"- Model {identifier}: {model_key}")
                else:
                    print("  No models selected")
                print()
                
            elif command == "model":
                if len(args) < 1:
                    print()
                    print("Usage: /model <name>")
                    print("Available models: K2, V3, R1")
                    print()
                    continue
                user_input = args[0]
                
                # Try to find model by model name field first, then by key
                model_key = None
                for key in available_models:
                    model_config = model_manager.get_model_config(key)
                    if model_config and model_config.get("model", "").lower() == user_input.lower():
                        model_key = key
                        break
                
                # If not found by model name, try direct key match
                if not model_key and user_input in available_models:
                    model_key = user_input
                
                if not model_key:
                    print()
                    print(f"Unknown model: {user_input}")
                    print("Available models: K2, V3, R1")
                    print()
                    continue
                if config.add_model(model_key):
                    print()
                    model_config = model_manager.get_model_config(model_key)
                    if model_config:
                        company = model_config.get("company", "")
                        family = model_config.get("family", "")
                        model = model_config.get("model", "")
                        release = model_config.get("release", "")
                        full_name = f"{family} {model} {release}".strip()
                        print(f"Added model: {full_name}")
                        print()
                    else:
                        print(f"Added model: {model_key}")
                        print()
                else:
                    print()
                    print(f"Model {model_key} already selected")
                    print()
            
            elif command == "remove":
                if len(args) < 1:
                    print()
                    print("Usage: /remove <name>")
                    print("Available models: K2, V3, R1")
                    print()
                    continue
                user_input = args[0]
                
                # Try to find model by model name field first, then by key
                model_key = None
                for key in config.models:
                    model_config = model_manager.get_model_config(key)
                    if model_config and model_config.get("model", "").lower() == user_input.lower():
                        model_key = key
                        break
                
                # If not found by model name, try direct key match
                if not model_key and user_input in config.models:
                    model_key = user_input
                
                if not model_key:
                    print()
                    print(f"Model {user_input} not found in current configuration")
                    print()
                    continue
                
                if config.remove_model(model_key):
                    print()
                    model_config = model_manager.get_model_config(model_key)
                    if model_config:
                        company = model_config.get("company", "")
                        family = model_config.get("family", "")
                        model = model_config.get("model", "")
                        release = model_config.get("release", "")
                        full_name = f"{family} {model} {release}".strip()
                        print(f"Removed model: {full_name}")
                        print()
                    else:
                        print(f"Removed model: {model_key}")
                        print()
                else:
                    print()
                    print(f"Model {model_key} was not in configuration")
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