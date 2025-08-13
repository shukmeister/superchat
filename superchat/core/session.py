"""Session configuration and state management.

This module manages the runtime state of a superchat session - what the user has configured
and the current status of their chat session.

Key responsibilities:
- Track which models the user has selected for their chat
- Store session settings (voice mode, active/inactive status)
- Provide different system prompts for single vs multi-agent conversations
- Validate session configuration before starting a chat
- Manage session lifecycle (start/stop)
- Track token usage and conversation statistics

Think of it as the app's "memory" - it remembers what you've configured
and keeps track of the current session state throughout your conversation.
"""

import time

class SessionConfig:
    """Manages in-memory configuration for a chat session."""
    
    # Initialize session configuration with default values
    def __init__(self, debug_enabled=False):
        self.models = []
        self.voice_enabled = False
        self.session_active = False
        self.current_model = None
        self.debug_enabled = debug_enabled
        self.chat_flow = "default"  # "default" (immediate team) or "staged" (staged chat)
        self.debate_rounds = 1  # Number of rounds for multi-agent debates (default: 1)
        
        # Token tracking
        self.session_start_time = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.conversation_rounds = 0
    
    # Add a model to the session configuration
    def add_model(self, model_name):
        """Add a model to the session if not already present."""
        if model_name not in self.models:
            self.models.append(model_name)
            return True
        return False
    
    # Remove a model from the session configuration
    def remove_model(self, model_name):
        """Remove a model from the session."""
        if model_name in self.models:
            self.models.remove(model_name)
            if self.current_model == model_name:
                self.current_model = None
            return True
        return False
    
    # Configure voice output setting
    def set_voice_enabled(self, enabled):
        """Enable or disable voice output."""
        self.voice_enabled = enabled
    
    # Configure debug mode setting
    def set_debug_enabled(self, enabled):
        """Enable or disable debug mode."""
        self.debug_enabled = enabled
        
        # Update global debug logger
        from superchat.utils.debug import set_debug_enabled
        set_debug_enabled(enabled)
    
    # Configure chat flow setting
    def set_chat_flow(self, flow):
        """Set chat flow mode: 'default' or 'staged'."""
        if flow in ["default", "staged"]:
            self.chat_flow = flow
            return True
        return False
    
    # Get current chat flow setting
    def get_chat_flow(self):
        """Get current chat flow mode."""
        return self.chat_flow
    
    # Check if using staged flow
    def is_staged_flow(self):
        """Check if session is using staged chat flow."""
        return self.chat_flow == "staged"
    
    # Configure debate rounds setting
    def set_debate_rounds(self, rounds):
        """Set number of debate rounds for multi-agent conversations."""
        if isinstance(rounds, int) and 1 <= rounds <= 5:
            self.debate_rounds = rounds
            return True
        return False
    
    # Get current debate rounds setting
    def get_debate_rounds(self):
        """Get current number of debate rounds."""
        return self.debate_rounds
    
    # Start the session and begin timing
    def start_session(self):
        """Mark session as active and set current model."""
        if self.models:
            self.session_active = True
            self.current_model = self.models[0]  # Default to first model
            self.session_start_time = time.time()
            return True
        return False
    
    # Stop the session and clean up state
    def stop_session(self):
        """Mark session as inactive."""
        self.session_active = False
        self.current_model = None
    
    # Track token usage from a conversation round
    def add_usage_data(self, usage_data):
        """Add token usage data from a conversation round."""
        self.total_input_tokens += usage_data.get("prompt_tokens", 0)
        self.total_output_tokens += usage_data.get("completion_tokens", 0)
        self.total_tokens += usage_data.get("total_tokens", 0)
        self.conversation_rounds += 1
    
    # Calculate how long the session has been running
    def get_session_duration(self):
        """Get session duration in seconds."""
        if self.session_start_time:
            return time.time() - self.session_start_time
        return 0
    
    # Get formatted session statistics
    def get_stats(self):
        """Get session statistics."""
        duration = self.get_session_duration()
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        
        return {
            "duration": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "conversation_rounds": self.conversation_rounds,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens
        }
    
    # Export configuration as dictionary
    def get_config_dict(self):
        """Return configuration as dictionary."""
        return {
            'models': self.models.copy(),
            'voice': self.voice_enabled,
            'active': self.session_active,
            'current_model': self.current_model,
            'debug': self.debug_enabled,
            'chat_flow': self.chat_flow,
            'debate_rounds': self.debate_rounds
        }
    
    # Check if session has required configuration to start
    def is_valid_for_start(self):
        """Check if configuration is valid to start a session."""
        return len(self.models) > 0
    
    # Determine if this is a multi-agent conversation
    def is_multi_agent(self):
        """Check if session has multiple agents."""
        return len(self.models) > 1
    
    # Get appropriate system prompt based on agent count
    def get_system_prompt(self):
        """Get the appropriate system prompt based on agent count."""
        return ""
    
    
    def __str__(self):
        return f"SessionConfig(models={self.models}, voice={self.voice_enabled}, active={self.session_active}, debug={self.debug_enabled}, chat_flow={self.chat_flow}, debate_rounds={self.debate_rounds})"