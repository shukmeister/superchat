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
from prompt_toolkit.shortcuts import PromptSession
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager
from superchat.utils.parser import parse_input
from superchat.utils.identifiers import get_model_identifier
from superchat.core.setup import ChatSetup
from superchat.core.staged_flow import StagedFlowManager
from superchat.core.command_handler import ChatCommandHandler
from superchat.core.message_router import MessageRouter


# Chat session coordinator that manages runtime conversation flow
class ChatSession:
    
    # Setup - Initialize chat session to receive pre-configured components from setup
    def __init__(self, config: SessionConfig):
        self.config = config
        self.model_client_manager = ModelClientManager()
        self.is_multi_agent = len(config.models) > 1
        # Message handler will be injected by setup.py after initialization
        self.message_handler = None
        # Staged flow manager for staged conversations
        self.staged_flow_manager = None
        # Command handler for processing chat commands
        self.command_handler = None
        # Message router for routing messages to appropriate handlers
        self.message_router = None
    
    # Setup - Inject pre-configured message handler from setup
    def set_message_handler(self, message_handler):
        self.message_handler = message_handler
    
    # Setup - Initialize staged flow manager for multi-agent staged conversations
    def setup_staged_flow_manager(self, agents, agent_model_mapping):
        """Initialize staged flow manager with agents and mapping."""
        if self.config.is_staged_flow() and self.is_multi_agent:
            self.staged_flow_manager = StagedFlowManager(
                self.config, 
                agents, 
                self.message_handler, 
                agent_model_mapping
            )
    
    # Setup - Initialize command handler for processing chat commands
    def setup_command_handler(self):
        """Initialize command handler with required dependencies."""
        self.command_handler = ChatCommandHandler(
            self.config,
            self.staged_flow_manager,
            self.model_client_manager,
            self  # Pass reference to this ChatSession
        )
        
        # Initialize message router with required dependencies
        self.message_router = MessageRouter(
            self.config,
            self.message_handler,
            self.staged_flow_manager,
            self.is_multi_agent
        )
        # Set reference to this ChatSession for calling conversation methods
        self.message_router.set_chat_session(self)
    
    # Setup - Welcome screen - start the interactive chat loop with model display and >> prompt
    def start_chat_loop(self):
        # Validate that components were properly configured by setup
        if not self.message_handler:
            raise RuntimeError("Message handler not configured. Use setup.py to initialize session.")
        
        # Display session information based on flow mode and agent count
        if self.is_multi_agent:
            if self.config.is_staged_flow():
                print("Starting staged chat with:")
                for i, model_name in enumerate(self.config.models):
                    label = self.model_client_manager.get_model_label(model_name)
                    identifier = get_model_identifier(i)
                    print(f"  {identifier} [{label}]")
                if self.staged_flow_manager:
                    status_display = self.staged_flow_manager.get_status_display()
                    if self.staged_flow_manager.awaiting_initial_question:
                        print(f"\n{status_display}")
                    else:
                        print(f"\nStatus: {status_display}")
            else:
                print("Starting multi-agent debate with:")
                for i, model_name in enumerate(self.config.models):
                    label = self.model_client_manager.get_model_label(model_name)
                    identifier = get_model_identifier(i)
                    print(f"  {identifier} [{label}]")
        else:
            model_name = self.config.models[0]
            label = self.model_client_manager.get_model_label(model_name)
            print(f"Starting chat with [{label}]")
        print()
        
        # Start the main runtime conversation loop
        asyncio.run(self._async_chat_loop())
    
    # Main async chat loop that coordinates user input and conversation flow  
    async def _async_chat_loop(self):
        while True:
            try:
                # Get user input (displays in default orange color while typing)
                session = PromptSession()
                user_input = await session.prompt_async(">> ")
                
                # After Enter is pressed, overwrite with grey version
                if user_input.strip():
                    import os
                    terminal_width = os.get_terminal_size().columns
                    lines = user_input.split('\n')
                    
                    # Calculate total lines including wrapped lines for all cases
                    total_lines = 0
                    for i, line in enumerate(lines):
                        # First line has ">> " (3 chars), others have "   " (3 chars)
                        line_length = len(line) + 3
                        wrapped_lines = (line_length + terminal_width - 1) // terminal_width
                        total_lines += max(1, wrapped_lines)
                    
                    # Clear all the lines that were displayed
                    for _ in range(total_lines):
                        print(f"\033[A\033[2K", end="")
                    
                    # Display all lines in grey using consistent ANSI escape codes
                    if len(lines) > 1:
                        # Multi-line case
                        print(f"\033[90m>> {lines[0]}\033[0m")
                        for line in lines[1:]:
                            print(f"\033[90m   {line}\033[0m")
                    else:
                        # Single-line case
                        print(f"\033[90m>> {user_input}\033[0m")
                
                # Add spacing after input
                print()
                
                parsed = parse_input(user_input)
                
                # Handle empty input (do nothing for now)
                if parsed['type'] == 'empty':
                    continue
                
                # Handle chat commands (/exit, /stats, etc.)    
                if parsed['type'] == 'command':
                    should_continue, should_exit = await self.command_handler.handle_command(
                        parsed['command'], parsed.get('args', [])
                    )
                    if should_exit:
                        break
                    if should_continue:
                        continue
                
                # Handle regular user messages to AI agents        
                if parsed['type'] == 'message':
                    await self.message_router.route_message(parsed['message'])
                    
            except KeyboardInterrupt:
                print("\nTerminating connection")
                break
            except EOFError:
                print("\nTerminating connection")  
                break
    
    ## conversation handler methods:
    
    # Transition from staged flow to team debate with assembled context
    async def transition_staged_to_team_debate(self):
        """Handle transition from staged 1:1 conversations to team debate."""
        if not self.staged_flow_manager:
            raise RuntimeError("Staged flow manager not initialized")
            
        # Execute the transition
        transition_result = await self.staged_flow_manager.transition_to_team_phase()
        
        if not transition_result['success']:
            print(f"Transition failed: {transition_result['message']}")
            return False
            
        # Update message handler with new team
        if 'team' in transition_result:
            self.message_handler.team = transition_result['team']
            
        # Send assembled context to team to establish shared knowledge
        assembled_context = transition_result['assembled_context']
        print(f"Transitioning to team debate with {len(transition_result['promoted_agents'])} agents")
        print("Sharing conversation context\n")
        
        # Send the assembled context as the first team message
        await self.message_handler.send_to_team(self.message_handler.team, assembled_context)
        
        print("Team debate ready. Continue with your questions or comments.\n")
        return True

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
    
