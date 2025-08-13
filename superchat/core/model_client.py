"""Modern AutoGen model client for OpenRouter integration.

This module acts as the "phone system" between superchat and AI models.
It handles the technical details of API communication so the rest of the app doesn't have to.

Key responsibilities:
- Load model configurations from models.json (which models are available, their settings)
- Manage API key authentication (from .env, environment, or local config file)
- Create OpenAI-compatible clients that can talk to OpenRouter's API
- Abstract away the complexity of different model providers

Think of it as your app's "AI service representative" - it knows how to properly
format requests, handle authentication, and communicate with external AI services.
"""

import json
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        pass
from autogen_ext.models.openai import OpenAIChatCompletionClient
from superchat.utils.api_key_wizard import run_api_key_wizard


class ModelClientManager:
    """Manages model clients using modern AutoGen architecture."""
    
    # Initialize model client manager and load configuration
    def __init__(self):
        self.models_config = None
        self.api_key = None
        self._load_models_config()
        self._load_api_key()
    
    def _load_models_config(self):
        """Load model configurations from models.json."""
        config_path = Path(__file__).parent.parent / "config" / "models.json"
        try:
            with open(config_path, 'r') as f:
                self.models_config = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load models config: {e}")
    
    def _load_api_key(self):
        """Load OpenRouter API key from environment."""
        # Load from .env file if it exists
        load_dotenv()
        self.api_key = os.getenv('OPENROUTER_API_KEY')
    
    
    # Validate that API key is properly configured
    def validate_setup(self):
        """Validate that API key is available, with interactive setup wizard."""
        if not self.api_key:
            # Run the API key wizard
            api_key = run_api_key_wizard()
            if api_key:
                # Update our instance with the new key
                self.api_key = api_key
                return True
            else:
                return False
        
        return True
    
    # Get list of all configured model names
    def get_available_models(self):
        """Get list of available model names."""
        if not self.models_config:
            return []
        return list(self.models_config["models"].keys())
    
    # Get configuration details for a specific model
    def get_model_config(self, model_name):
        """Get configuration for a specific model."""
        if not self.models_config or model_name not in self.models_config["models"]:
            return None
        return self.models_config["models"][model_name]
    
    # Get the display label for a specific model (for chat)
    def get_model_label(self, model_name):
        """Get the display label for a specific model."""
        model_config = self.get_model_config(model_name)
        if model_config and "label" in model_config:
            return model_config["label"]
        # Fallback to model field or model name if label not found
        if model_config and "model" in model_config:
            return model_config["model"]
        return model_name
    
    # Get the display name for setup/configuration (detailed name)
    def get_model_display_name(self, model_name):
        """Get the detailed display name for setup/configuration screens."""
        model_config = self.get_model_config(model_name)
        if model_config:
            from superchat.utils.model_resolver import get_display_name
            return get_display_name(model_config)
        return model_name
    
    # Create AutoGen client for communicating with a specific model
    def create_model_client(self, model_name, skip_validation=False):
        """Create OpenAI chat completion client for the specified model."""
        if not skip_validation and not self.validate_setup():
            raise RuntimeError("API key not configured")
            
        model_config = self.get_model_config(model_name)
        if not model_config:
            raise ValueError(f"Unknown model: {model_name}")
        
        return OpenAIChatCompletionClient(
            base_url="https://openrouter.ai/api/v1",
            model=model_config["openrouter_id"],
            api_key=self.api_key,
            model_info=model_config["model_info"]
        )
    
