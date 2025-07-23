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
from autogen_agentchat.agents import AssistantAgent
from halo import Halo
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager
from superchat.utils.parser import parse_input
from superchat.utils.identifiers import get_model_identifier


class ChatSession:
    """Manages a single chat session using modern AutoGen AssistantAgent."""
    
    def __init__(self, config: SessionConfig):
        self.config = config
        self.model_name = None
        self.model_client_manager = ModelClientManager()
        self.assistant = None
        
    def initialize_agent(self):
        """Initialize the AutoGen assistant agent for the selected model."""
        if not self.config.models or len(self.config.models) != 1:
            raise ValueError("Exactly one model required for chat session")
        
        self.model_name = self.config.models[0]
        
        # Create model client using modern AutoGen approach
        # Skip API key validation since it was already checked at startup
        model_client = self.model_client_manager.create_model_client(self.model_name, skip_validation=True)
        
        # Create AutoGen assistant agent (replace hyphens for valid Python identifier)
        safe_name = self.model_name.replace("-", "_")
        self.assistant = AssistantAgent(
            name=f"assistant_{safe_name}",
            model_client=model_client,
            system_message=self.config.get_system_prompt() or "You are a helpful assistant that answers questions accurately and concisely. Be concise and straightforward in your responses. Do not use emojis, bold text, italics, or other stylistic formatting. Never ask the user questions - provide direct answers to their queries."
        )
    
    def start_chat_loop(self):
        """Start the interactive chat loop with >> prompt."""
        # Initialize agent if not already done
        if not self.assistant:
            self.initialize_agent()
        
        model_config = self.model_client_manager.get_model_config(self.model_name)
        if model_config:
            model = model_config.get("model", self.model_name)
            print(f"Starting chat with [{model}]")
        else:
            print(f"Starting chat with [{self.model_name}]")
        print()
        
        # Run the async chat loop
        asyncio.run(self._async_chat_loop())
    
    async def _async_chat_loop(self):
        """Async chat loop using AutoGen's modern API."""
        while True:
            try:
                user_input = input(">> ")
                parsed = parse_input(user_input)
                
                if parsed['type'] == 'empty':
                    continue
                    
                if parsed['type'] == 'command':
                    if parsed['command'] == 'exit':
                        print()
                        self._display_exit_summary()
                        print("Terminating connection")
                        break
                    elif parsed['command'] == 'stats':
                        print()
                        self._display_stats()
                        print()
                        continue
                    else:
                        print()
                        print(f"Unknown command: /{parsed['command']}")
                        print()
                        continue
                        
                # Handle regular messages
                if parsed['type'] == 'message':
                    print()  # Add line break after user message
                    try:
                        # Show loading spinner while waiting for response
                        with Halo(text="Processing", spinner="dots"):
                            response = await self._send_message_async(parsed['message'])
                        
                        model_config = self.model_client_manager.get_model_config(self.model_name)
                        if model_config:
                            model = model_config.get("model", self.model_name)
                            # Get Russian letter identifier
                            model_index = self.config.models.index(self.model_name) if self.model_name in self.config.models else 0
                            identifier = get_model_identifier(model_index)
                            print(f"{identifier} [{model}]: {response}\n")
                        else:
                            print(f"[{self.model_name}]: {response}\n")
                    except Exception as e:
                        print(f"Error: {e}\n")
                    
            except KeyboardInterrupt:
                print("\nTerminating connection")
                break
            except EOFError:
                print("\nTerminating connection")  
                break
    
    async def _send_message_async(self, message: str) -> str:
        """Send message to assistant using modern AutoGen async API."""
        # Use direct API call to get usage data
        system_message = self.config.get_system_prompt() or "You are a helpful assistant that answers questions accurately and concisely. Be concise and straightforward in your responses. Do not use emojis, bold text, italics, or other stylistic formatting. Never ask the user questions - provide direct answers to their queries."
        response_content, usage_data = await self.model_client_manager.send_message_with_usage(
            self.model_name, 
            message, 
            system_message
        )
        
        # Track usage data in session config
        self.config.add_usage_data(usage_data)
        
        return response_content
    
    def _display_stats(self):
        """Display session statistics including token counts and costs."""
        stats = self.config.get_stats()
        model_config = self.model_client_manager.get_model_config(self.model_name)
        
        print("Session Statistics:")
        print(f"  Time elapsed: {stats['duration']}")
        print(f"  Conversation rounds: {stats['conversation_rounds']}")
        print()
        print("Token Usage:")
        print(f"  Input tokens:  {stats['total_input_tokens']:,}")
        print(f"  Output tokens: {stats['total_output_tokens']:,}")
        print(f"  Total tokens:  {stats['total_tokens']:,}")
        
        if model_config:
            # Calculate costs
            input_cost_per_million = model_config.get("input_cost", 0)
            output_cost_per_million = model_config.get("output_cost", 0)
            
            input_cost = (stats['total_input_tokens'] / 1_000_000) * input_cost_per_million
            output_cost = (stats['total_output_tokens'] / 1_000_000) * output_cost_per_million
            total_cost = input_cost + output_cost
            
            print()
            print("Estimated Costs:")
            print(f"  Input cost:  ${input_cost:.6f}")
            print(f"  Output cost: ${output_cost:.6f}")
            print(f"  Total cost:  ${total_cost:.6f}")
    
    def _display_exit_summary(self):
        """Display session summary on exit with tokens and costs."""
        stats = self.config.get_stats()
        model_config = self.model_client_manager.get_model_config(self.model_name)
        
        print("Session Summary:")
        print(f"  Time elapsed: {stats['duration']}")
        print(f"  Conversation rounds: {stats['conversation_rounds']}")
        print(f"  Total tokens: {stats['total_tokens']:,}")
        
        if model_config:
            # Calculate total cost
            input_cost_per_million = model_config.get("input_cost", 0)
            output_cost_per_million = model_config.get("output_cost", 0)
            
            input_cost = (stats['total_input_tokens'] / 1_000_000) * input_cost_per_million
            output_cost = (stats['total_output_tokens'] / 1_000_000) * output_cost_per_million
            total_cost = input_cost + output_cost
            
            print(f"  Total cost: ${total_cost:.6f}")
        print()