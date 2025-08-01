"""Chat session runtime management using modern AutoGen architecture.

This module is the "conversation coordinator" - it handles runtime chat flow and user interaction.
While setup.py initializes components and message_handler.py processes AI communications, 
this module coordinates the conversation experience and manages team lifecycles.

Key responsibilities:
- Coordinate runtime chat flow and user interaction
- Run the interactive chat loop (the >> prompt you see)
- Process user input (regular messages vs commands like /exit)
- Manage AutoGen team lifecycles for multi-agent conversations
- Control conversation flow between user and AI agents
- Handle session state and statistics during runtime

Think of it as the "conversation coordinator" - it receives pre-configured components
from setup.py and orchestrates the runtime conversation experience.
"""

import asyncio
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager
from superchat.utils.parser import parse_input
from superchat.utils.identifiers import get_model_identifier
from superchat.utils.stats import display_stats, display_exit_summary
from superchat.core.setup import ChatSetup


# Chat session coordinator that manages runtime conversation flow
class ChatSession:
    
    # Setup - Initialize chat session to receive pre-configured components from setup
    def __init__(self, config: SessionConfig):
        self.config = config
        self.model_client_manager = ModelClientManager()
        self.is_multi_agent = len(config.models) > 1
        # Message handler will be injected by setup.py after initialization
        self.message_handler = None
    
    # Setup - Inject pre-configured message handler from setup
    def set_message_handler(self, message_handler):
        self.message_handler = message_handler
    
    # Setup - Welcome screen - start the interactive chat loop with model display and >> prompt
    def start_chat_loop(self):
        # Validate that components were properly configured by setup
        if not self.message_handler:
            raise RuntimeError("Message handler not configured. Use setup.py to initialize session.")
        
        # Display session information based on single or multi-agent mode
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
        
        # Start the main runtime conversation loop
        asyncio.run(self._async_chat_loop())
    
    # Main async chat loop that coordinates user input and conversation flow  
    async def _async_chat_loop(self):
        while True:
            try:
                # Get and parse user input
                user_input = input(">> ")
                
                # Display the submitted message in grey (overwrite the previous line)
                if user_input.strip():  # Only colorize non-empty input
                    print(f"\033[A\033[2K\033[90m>> {user_input}\033[0m")
                    print()
                
                parsed = parse_input(user_input)
                
                # Handle empty input (do nothing for now)
                if parsed['type'] == 'empty':
                    continue
                
                # Handle chat commands (/exit, /stats, etc.)    
                if parsed['type'] == 'command':
                    if parsed['command'] == 'exit':
                        stats = self.config.get_stats()
                        display_exit_summary(stats, self.config.models, self.model_client_manager)
                        print("Terminating connection")
                        break
                    elif parsed['command'] == 'stats':
                        stats = self.config.get_stats()
                        display_stats(stats, self.config.models, self.model_client_manager)
                        print()
                        continue
                    else:
                        print(f"Unknown command: /{parsed['command']}")
                        print()
                        continue
                
                # Handle regular user messages to AI agents        
                if parsed['type'] == 'message':
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
    
    ## conversation handler methods:

    # Orchestrate multi-agent conversation using persistent team
    async def _handle_multi_agent_conversation(self, message):
        """Send message to persistent team that maintains conversation history."""
        if not self.message_handler or not self.message_handler.team:
            raise RuntimeError("Multi-agent team not initialized")
        
        
        try:
            # Send message to current team (team maintains its own history)
            result = await self.message_handler.send_to_team(self.message_handler.team, message)
            return result
            
        except Exception as e:
            print(f"Multi-agent conversation error: {e}")
            print()
    
