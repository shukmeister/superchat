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
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager

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

def display_session_info(config):
    """Display current session configuration."""
    print("Session Configuration:")
    
    if config.models:
        print(f"  Models: {', '.join(config.models)}")
    else:
        print("  Models: None selected")
    
    print()

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
    
    display_session_info(config)
    
    print("Setup Mode - Configure your chat session")
    print(f"Available models: {', '.join(available_models)}")
    print("Commands: /model, /start, /help, /exit")
    print()
    
    while True:
        try:
            user_input = input(">> ")
            parsed = parse_input(user_input)
            
            if parsed['type'] == 'empty':
                continue
            
            if parsed['type'] == 'message':
                print("Not in chat mode yet. Use commands to configure session.")
                continue
                
            # Handle commands
            command = parsed['command']
            args = parsed['args']
            
            if command == "exit":
                print("Terminating connection")
                return None
                
            elif command == "start":
                if not config.is_valid_for_start():
                    print("Please select at least one model first using /model")
                    continue
                if len(config.models) > 1:
                    print("Error: /start requires exactly one model. Multiple models not supported yet.")
                    print(f"Currently selected: {', '.join(config.models)}")
                    print("Use /model to select a single model or wait for multi-agent support.")
                    continue
                config.start_session()
                return config
                
            elif command == "help":
                print("Available commands:")
                print("  /model <name> - Add a model to the chat")
                print("  /start - Begin the chat session")
                print("  /help - Show this help")
                print("  /exit - Exit superchat")
                print()
                
            elif command == "model":
                if len(args) < 1:
                    print("Usage: /model <name>")
                    print(f"Available models: {', '.join(available_models)}")
                    continue
                model_name = args[0]
                if model_name not in available_models:
                    print(f"Unknown model: {model_name}")
                    print(f"Available models: {', '.join(available_models)}")
                    continue
                if config.add_model(model_name):
                    model_config = model_manager.get_model_config(model_name)
                    display_name = model_config["display_name"] if model_config else model_name
                    print(f"Added model: {display_name}")
                    display_session_info(config)
                else:
                    print(f"Model {model_name} already selected")
                    
            else:
                print(f"Unknown command: /{command}")
                print("Type /help for available commands")
                
        except KeyboardInterrupt:
            print("\nTerminating connection")
            return None
        except EOFError:
            print("\nTerminating connection")
            return None