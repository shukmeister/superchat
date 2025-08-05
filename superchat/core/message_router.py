"""Message router for handling different chat flow modes.

This module handles routing user messages to the appropriate handler based on
the current chat mode (single agent, multi-agent default, staged individual, staged team).
It's extracted from the main chat loop to separate routing logic from coordination.

Key responsibilities:
- Detect current chat mode based on configuration and state
- Route messages to appropriate handlers
- Handle different conversation flows
- Manage error handling for message routing

Think of it as the "dispatcher" that determines which conversation handler
should process each user message based on the current context.
"""


class MessageRouter:
    """Routes messages to appropriate handlers based on chat mode."""
    
    def __init__(self, config, message_handler, staged_flow_manager, is_multi_agent):
        """Initialize message router with required dependencies."""
        self.config = config
        self.message_handler = message_handler
        self.staged_flow_manager = staged_flow_manager
        self.is_multi_agent = is_multi_agent
        self.chat_session = None  # Will be set by ChatSession
    
    def set_chat_session(self, chat_session):
        """Set reference to ChatSession for calling conversation methods."""
        self.chat_session = chat_session
    
    async def route_message(self, message):
        """Route a message to the appropriate handler based on current chat mode."""
        try:
            chat_mode = self._detect_chat_mode()
            
            if chat_mode == "single":
                await self._handle_single_agent(message)
            elif chat_mode == "staged_individual":
                await self._handle_staged_individual(message)
            elif chat_mode == "staged_team":
                await self._handle_staged_team(message)
            elif chat_mode == "default_team":
                await self._handle_default_team(message)
            else:
                print(f"Unknown chat mode: {chat_mode}")
                
        except Exception as e:
            print(f"Error: {e}\n")
    
    def _detect_chat_mode(self):
        """Detect current chat mode based on configuration and state."""
        if not self.is_multi_agent:
            return "single"
        
        # Multi-agent mode - check if using staged flow
        if self.staged_flow_manager:
            if self.staged_flow_manager.is_individual_phase():
                return "staged_individual"
            elif self.staged_flow_manager.is_team_phase():
                return "staged_team"
        
        # Default multi-agent mode
        return "default_team"
    
    async def _handle_single_agent(self, message):
        """Handle single agent conversation."""
        await self.message_handler.handle_single_agent_response(message)
    
    async def _handle_staged_individual(self, message):
        """Handle staged flow individual conversation."""
        handled = await self.staged_flow_manager.handle_individual_message(message)
        if not handled:
            print()
            print("No more agents for individual conversations. Use /promote to advance.")
            print()
    
    async def _handle_staged_team(self, message):
        """Handle staged flow team phase - route to team conversation."""
        if not self.chat_session:
            raise RuntimeError("ChatSession reference not set in MessageRouter")
        
        # Route to multi-agent team conversation
        await self.chat_session._handle_multi_agent_conversation(message)
    
    async def _handle_default_team(self, message):
        """Handle default multi-agent team conversation."""
        if not self.chat_session:
            raise RuntimeError("ChatSession reference not set in MessageRouter")
        await self.chat_session._handle_multi_agent_conversation(message)