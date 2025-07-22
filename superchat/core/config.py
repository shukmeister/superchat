"""Session configuration management."""

class SessionConfig:
    """Manages in-memory configuration for a chat session."""
    
    def __init__(self):
        self.models = []
        self.voice_enabled = False
        self.session_active = False
        self.current_model = None
    
    def add_model(self, model_name):
        """Add a model to the session if not already present."""
        if model_name not in self.models:
            self.models.append(model_name)
            return True
        return False
    
    def remove_model(self, model_name):
        """Remove a model from the session."""
        if model_name in self.models:
            self.models.remove(model_name)
            if self.current_model == model_name:
                self.current_model = None
            return True
        return False
    
    def set_voice_enabled(self, enabled):
        """Enable or disable voice output."""
        self.voice_enabled = enabled
    
    def start_session(self):
        """Mark session as active and set current model."""
        if self.models:
            self.session_active = True
            self.current_model = self.models[0]  # Default to first model
            return True
        return False
    
    def stop_session(self):
        """Mark session as inactive."""
        self.session_active = False
        self.current_model = None
    
    def get_config_dict(self):
        """Return configuration as dictionary."""
        return {
            'models': self.models.copy(),
            'voice': self.voice_enabled,
            'active': self.session_active,
            'current_model': self.current_model
        }
    
    def is_valid_for_start(self):
        """Check if configuration is valid to start a session."""
        return len(self.models) > 0
    
    def __str__(self):
        return f"SessionConfig(models={self.models}, voice={self.voice_enabled}, active={self.session_active})"