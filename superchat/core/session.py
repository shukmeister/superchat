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
    
    def __init__(self):
        self.models = []
        self.voice_enabled = False
        self.session_active = False
        self.current_model = None
        self.debate_prompt = self._create_debate_prompt()
        
        # Token tracking
        self.session_start_time = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.conversation_rounds = 0
    
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
            self.session_start_time = time.time()
            return True
        return False
    
    def stop_session(self):
        """Mark session as inactive."""
        self.session_active = False
        self.current_model = None
    
    def add_usage_data(self, usage_data):
        """Add token usage data from a conversation round."""
        self.total_input_tokens += usage_data.get("prompt_tokens", 0)
        self.total_output_tokens += usage_data.get("completion_tokens", 0)
        self.total_tokens += usage_data.get("total_tokens", 0)
        self.conversation_rounds += 1
    
    def get_session_duration(self):
        """Get session duration in seconds."""
        if self.session_start_time:
            return time.time() - self.session_start_time
        return 0
    
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
    
    def is_multi_agent(self):
        """Check if session has multiple agents."""
        return len(self.models) > 1
    
    def get_system_prompt(self):
        """Get the appropriate system prompt based on agent count."""
        if self.is_multi_agent():
            return self.debate_prompt
        return ""
    
    def _create_debate_prompt(self):
        """Create the debate background prompt for multi-agent conversations."""
        return """You are participating in a multi-agent discussion with a user and other AI agents. Your role is to contribute to a collaborative, truth-seeking conversation by following these guidelines:

- Take turns sharing well-researched opinions on the given topic
- If you lack knowledge on something, research it thoroughly or acknowledge your uncertainty
- Always say "I don't know" rather than providing false or uncertain information
- Ask questions to the group when you need more information or clarification
- Focus on finding truth through solid reasoning and evidence-based arguments
- Provide clear reasoning for supporting or challenging other agents' opinions
- Break down complex topics using first principles thinking
- Always verify and double-check your responses before sharing
- Be maximally truth-seeking in all your contributions

The goal is constructive debate that leads to better understanding and well-reasoned conclusions."""
    
    def __str__(self):
        return f"SessionConfig(models={self.models}, voice={self.voice_enabled}, active={self.session_active})"