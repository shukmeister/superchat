# API key setup wizard utility for superchat.
#
# This module handles the interactive setup of OpenRouter API keys.
# It provides a clean, user-friendly wizard that prompts users for their API key
# and automatically saves it to their ~/.env file for persistent storage.
#
# Key responsibilities:
# - Display setup instructions and privacy notices
# - Securely prompt for API key input (hidden characters)
# - Validate API key format and save to ~/.env file
# - Handle errors gracefully (file permissions, cancellation, etc.)
# - Provide clear feedback on success/failure

import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        pass
from prompt_toolkit import prompt


def save_api_key_to_env(api_key):
    """Save API key to ~/.env file.
    
    Args:
        api_key (str): The OpenRouter API key to save
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        env_path = Path.home() / ".env"
        
        # Check if .env file exists and read existing content
        existing_content = ""
        if env_path.exists():
            with open(env_path, 'r') as f:
                existing_content = f.read()
        
        # Check if OPENROUTER_API_KEY already exists in the file
        lines = existing_content.split('\n')
        updated_lines = []
        key_found = False
        
        for line in lines:
            if line.strip().startswith('OPENROUTER_API_KEY='):
                # Replace existing key
                updated_lines.append(f'OPENROUTER_API_KEY={api_key}')
                key_found = True
            else:
                updated_lines.append(line)
        
        # If key wasn't found, add it
        if not key_found:
            if existing_content and not existing_content.endswith('\n'):
                updated_lines.append('')  # Add empty line if file doesn't end with newline
            updated_lines.append(f'OPENROUTER_API_KEY={api_key}')
        
        # Write back to file
        with open(env_path, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        return True
        
    except Exception as e:
        print(f"Error saving API key to ~/.env: {e}")
        return False


def run_api_key_wizard():
    """Run the interactive API key setup wizard.
    
    Returns:
        str or None: The API key if successfully entered and saved, None if cancelled or failed
    """
    print("OpenRouter API key not found.")
    print()
    print("To use superchat, you need an OpenRouter API key:")
    print()
    print("1. Go to https://openrouter.ai/keys")
    print("2. Sign up for a free account")
    print("3. Create a new API key")
    print("4. Add credits to your account at https://openrouter.ai/credits")
    print()
    print("Privacy Notice: We do not save or store your API key anywhere.")
    print(" - Feel free to review the source code to verify: https://github.com/shukmeister/superchat")
    print()
    
    try:
        # Prompt for API key with secure input
        api_key = prompt("Input your OpenRouter API key: ", is_password=True)
        
        # Basic validation - check if it looks like an OpenRouter key
        if not api_key or not api_key.strip():
            print("\nNo API key entered. Exiting.")
            return None
        
        api_key = api_key.strip()
        if not api_key.startswith('sk-or-'):
            print("\nWarning: API key should start with 'sk-or-'. Continuing anyway...")
        
        # Save to .env file
        print("\nSaving API key to ~/.env...")
        if save_api_key_to_env(api_key):
            print("✓ API key saved successfully!")
            
            # Reload environment to pick up the new key
            load_dotenv()
            
            # Verify the key was loaded
            loaded_key = os.getenv('OPENROUTER_API_KEY')
            if loaded_key:
                print("✓ API key loaded successfully!")
                print()
                return loaded_key
            else:
                print("✗ Failed to load API key after saving. Please try again.")
                return None
        else:
            print("✗ Failed to save API key. Please check file permissions and try again.")
            return None
            
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        return None
    except Exception as e:
        print(f"Error during setup: {e}")
        return None