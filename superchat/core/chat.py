"""Chat session management using modern AutoGen architecture.

This module is the "conversation manager" - it handles the actual chat flow and user interaction.
While model_client.py handles the technical API calls, this module manages the conversation experience.

Key responsibilities:
- Initialize AutoGen agents with the selected models
- Run the interactive chat loop (the >> prompt you see)
- Process user input (regular messages vs commands like /exit)
- Send messages to AI models and display their responses
- Handle conversation state and flow control

Think of it as the "conversation brain" - it decides when to call the AI,
what to send, how to display responses, and when to end the session.
"""

import asyncio
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager
from superchat.utils.parser import parse_input
from superchat.utils.identifiers import get_model_identifier
from superchat.utils.stats import display_stats, display_exit_summary
from superchat.core.setup import ChatSetup
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination


# Chat session manager that handles runtime chat interaction
class ChatSession:
    
    # Initialize chat session with pre-configured components
    def __init__(self, config: SessionConfig):
        self.config = config
        self.model_client_manager = ModelClientManager()
        self.is_multi_agent = len(config.models) > 1
        # Message handler will be set up by setup.py
        self.message_handler = None
    
    # Set the pre-configured message handler from setup
    def set_message_handler(self, message_handler):
        self.message_handler = message_handler
    
    # Start the interactive chat loop with >> prompt
    def start_chat_loop(self):
        # Validate that message handler was configured
        if not self.message_handler:
            raise RuntimeError("Message handler not configured. Use setup.py to initialize session.")
        
        if self.is_multi_agent:
            print("Starting multi-agent debate with:")
            for i, model_name in enumerate(self.config.models):
                model_config = self.model_client_manager.get_model_config(model_name)
                if model_config:
                    model = model_config.get("model", model_name)
                    identifier = get_model_identifier(i)
                    print(f"  {identifier} [{model}]")
                else:
                    identifier = get_model_identifier(i)
                    print(f"  {identifier} [{model_name}]")
        else:
            model_name = self.config.models[0]
            model_config = self.model_client_manager.get_model_config(model_name)
            if model_config:
                model = model_config.get("model", model_name)
                print(f"Starting chat with [{model}]")
            else:
                print(f"Starting chat with [{model_name}]")
        print()
        
        # Run the async chat loop
        asyncio.run(self._async_chat_loop())
    
    # Main async chat loop that processes user input and handles responses
    async def _async_chat_loop(self):
        while True:
            try:
                user_input = input(">> ")
                parsed = parse_input(user_input)
                
                if parsed['type'] == 'empty':
                    if self.is_multi_agent:
                        # Empty input triggers agent discussion in multi-agent mode
                        await self._handle_agent_discussion()
                    continue
                    
                if parsed['type'] == 'command':
                    if parsed['command'] == 'exit':
                        print()
                        stats = self.config.get_stats()
                        display_exit_summary(stats, self.config.models, self.model_client_manager)
                        print("Terminating connection")
                        break
                    elif parsed['command'] == 'stats':
                        print()
                        stats = self.config.get_stats()
                        display_stats(stats, self.config.models, self.model_client_manager)
                        print()
                        continue
                    else:
                        print()
                        print(f"Unknown command: /{parsed['command']}")
                        print()
                        continue
                        
                # Handle regular messages
                if parsed['type'] == 'message':
                    print()  # Add single line break after user message
                    try:
                        if self.is_multi_agent:
                            await self._handle_multi_agent_conversation(parsed['message'])
                        else:
                            await self.message_handler.handle_single_agent_response(parsed['message'])
                    except Exception as e:
                        print(f"Error: {e}\n")
                    
            except KeyboardInterrupt:
                print("\nTerminating connection")
                break
            except EOFError:
                print("\nTerminating connection")  
                break
    
    # Team management methods for multi-agent conversations
    def _reset_team_for_next_round(self):
        """Reset team with standard termination conditions for next user message."""
        if not self.message_handler or not hasattr(self.message_handler, 'agents'):
            return
        
        agents = self.message_handler.agents
        max_messages = len(agents) + 1  # +1 for the user message
        termination = MaxMessageTermination(max_messages=max_messages)
        self.message_handler.team = RoundRobinGroupChat(agents, termination_condition=termination)
    
    def _create_discussion_team(self):
        """Create temporary team for agent-only discussions with extended termination."""
        if not self.message_handler or not hasattr(self.message_handler, 'agents'):
            return None
        
        agents = self.message_handler.agents
        # Allow more extended discussion (2 messages per agent)
        termination = MaxMessageTermination(max_messages=len(agents) * 2)
        return RoundRobinGroupChat(agents, termination_condition=termination)
    
    async def _handle_multi_agent_conversation(self, message):
        """Orchestrate multi-agent conversation with proper team management."""
        if not self.message_handler or not self.message_handler.team:
            raise RuntimeError("Multi-agent team not initialized")
        
        print()  # Add spacing before group responses
        
        try:
            # Send message to current team
            result = await self.message_handler.send_to_team(self.message_handler.team, message)
            
            # Reset team for next round to prevent conversation overflow
            self._reset_team_for_next_round()
            
            return result
            
        except Exception as e:
            print(f"Multi-agent conversation error: {e}")
            print()
    
    async def _handle_agent_discussion(self):
        """Manage agent-only discussions when user sends empty input."""
        discussion_prompt = "Continue the discussion. Share your thoughts on the topic or respond to what other agents have said."
        
        # Create temporary team for extended discussion
        discussion_team = self._create_discussion_team()
        if not discussion_team:
            print("Unable to create discussion team")
            return
        
        print()  # Add spacing before discussion
        
        try:
            # Use temporary team for agent discussion
            await self.message_handler.send_to_team(discussion_team, discussion_prompt)
            
        except Exception as e:
            print(f"Agent discussion error: {e}")
            print()
