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
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager
from superchat.utils.parser import parse_input


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
            system_message=self.config.get_system_prompt() or "You are a helpful assistant that answers questions accurately and concisely."
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
                        print("Terminating connection")
                        break
                    else:
                        print(f"Unknown command: /{parsed['command']}")
                        continue
                        
                # Handle regular messages
                if parsed['type'] == 'message':
                    print()  # Add line break after user message
                    try:
                        response = await self._send_message_async(parsed['message'])
                        model_config = self.model_client_manager.get_model_config(self.model_name)
                        if model_config:
                            model = model_config.get("model", self.model_name)
                            print(f"[{model}]: {response}\n")
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
        result = await self.assistant.run(task=message)
        return result.messages[-1].content