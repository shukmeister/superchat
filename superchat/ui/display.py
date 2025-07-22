"""Display functions for the superchat UI."""

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

def display_session_info(models=None, voice_enabled=False):
    """Display current session configuration."""
    print("Session Configuration:")
    
    if models:
        print(f"  Models: {', '.join(models)}")
    else:
        print("  Models: None selected")
    
    if voice_enabled:
        print("  Voice: Enabled")
    else:
        print("  Voice: Disabled")
    
    print()

def setup_loop():
    """Main setup loop for configuring chat parameters."""
    display_banner()
    
    # Initialize session config
    models = []
    voice_enabled = False
    
    display_session_info(models, voice_enabled)
    
    print("Setup Mode - Configure your chat session")
    print("Commands: /model, /start, /help, /exit")
    print()
    
    while True:
        try:
            user_input = input(">> ").strip()
            
            if not user_input:
                continue
                
            if user_input == "/exit":
                print("Goodbye!")
                return None
                
            elif user_input == "/start":
                if not models:
                    print("Please select at least one model first using /model")
                    continue
                return {"models": models, "voice": voice_enabled}
                
            elif user_input == "/help":
                print("Available commands:")
                print("  /model <name> - Add a model to the chat")
                print("  /start - Begin the chat session")
                print("  /help - Show this help")
                print("  /exit - Exit superchat")
                print()
                
            elif user_input.startswith("/model"):
                parts = user_input.split()
                if len(parts) < 2:
                    print("Usage: /model <name>")
                    continue
                model_name = parts[1]
                if model_name not in models:
                    models.append(model_name)
                    print(f"Added model: {model_name}")
                    display_session_info(models, voice_enabled)
                else:
                    print(f"Model {model_name} already selected")
                    
            else:
                print(f"Unknown command: {user_input}")
                print("Type /help for available commands")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            return None
        except EOFError:
            print("\nGoodbye!")
            return None