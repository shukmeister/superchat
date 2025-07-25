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
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager
from superchat.utils.parser import parse_input
from superchat.utils.identifiers import get_model_identifier
from superchat.utils.model_resolver import get_display_name
from superchat.utils.stats import display_stats, display_exit_summary
from superchat.core.message_handler import MessageHandler


# Chat session manager that handles both single and multi-agent conversations
class ChatSession:
    
    # Initialize chat session with configuration
    def __init__(self, config: SessionConfig):
        self.config = config
        self.model_client_manager = ModelClientManager()
        self.agents = []
        self.is_multi_agent = len(config.models) > 1
        self.team = None
        # Maps agent names to their model info (model_name, index, identifier)
        self.agent_model_mapping = {}
        # Message handler for processing agent responses
        self.message_handler = None
        
    # Initialize AutoGen agents for the selected models
    def initialize_agents(self):
        if not self.config.models:
            raise ValueError("At least one model required for chat session")
        
        self.agents = []
        # Clear the mapping when reinitializing agents
        self.agent_model_mapping = {}
        
        # Create an agent for each configured model
        for i, model_name in enumerate(self.config.models):
            # Create model client using modern AutoGen approach
            # Skip API key validation since it was already checked at startup
            model_client = self.model_client_manager.create_model_client(model_name, skip_validation=True)
            
            # Create AutoGen assistant agent with valid Python identifier name
            safe_name = self._make_safe_identifier(model_name)
            
            # Get debate-specific system prompt for multi-agent or regular prompt for single agent
            system_prompt = self.get_system_prompt(model_name, i, self.is_multi_agent)
            
            agent_name = f"agent_{safe_name}_{i}"
            agent = AssistantAgent(
                name=agent_name,
                model_client=model_client,
                system_message=system_prompt
            )
            
            self.agents.append(agent)
            
            # Store mapping from agent name to model info for easy lookup
            identifier = get_model_identifier(i)
            self.agent_model_mapping[agent_name] = {
                'model_name': model_name,
                'index': i,
                'identifier': identifier
            }
        
        # Create RoundRobinGroupChat for multi-agent mode
        if self.is_multi_agent:
            # Set up termination to stop after one complete round (each agent responds once)
            max_messages = len(self.agents) + 1  # +1 for the user message
            termination = MaxMessageTermination(max_messages=max_messages)
            self.team = RoundRobinGroupChat(self.agents, termination_condition=termination)
        
        # Initialize message handler with all necessary dependencies
        self.message_handler = MessageHandler(
            self.config, 
            self.agents, 
            self.model_client_manager, 
            self.agent_model_mapping
        )
        # Pass the team reference to message handler for multi-agent mode
        self.message_handler.team = self.team
    
    # Get appropriate system prompt for single or multi-agent mode
    def get_system_prompt(self, model_name, index, is_multi_agent):
        if is_multi_agent:
            # Get the full display name for the agent to include in their system prompt
            model_config = self.model_client_manager.get_model_config(model_name)
            display_name = get_display_name(model_config) if model_config else model_name
            
            # Get names of other agents in the conversation
            other_agents = []
            for i, other_model_name in enumerate(self.config.models):
                if i != index:  # Skip the current agent
                    other_config = self.model_client_manager.get_model_config(other_model_name)
                    other_display_name = get_display_name(other_config) if other_config else other_model_name
                    other_agents.append(other_display_name)
            
            other_agents_list = ", ".join(other_agents)
            
            return f"""You are {display_name}, participating in a live multi-agent debate with these other AI assistants: {other_agents_list}.

CRITICAL MULTI-AGENT SETUP:
- There are {len(self.config.models)} AI agents total in this conversation (including you)
- The other agents ({other_agents_list}) will ALSO respond to user messages
- You will see their actual responses in the conversation history
- DO NOT simulate, predict, or write responses for other agents
- Each agent responds independently, then the user decides if they want another round

CONVERSATION STRUCTURE:
- User asks a question or gives a prompt
- You respond with your perspective
- Other agents also respond with their perspectives  
- User can then ask follow-up questions or request another round
- You can reference what other agents actually said in previous rounds

Guidelines:
- BE CONCISE
- DONT USE STYLIZED FORMATTING LIKE BOLDING, ITALICS, EMOJIS, ETC
- Provide thoughtful, well-reasoned responses to user questions
- Reference other agents' actual previous responses when relevant
- If you disagree with another agent, explain your reasoning clearly
- Build upon ideas from previous messages in the conversation
- Be concise and direct in your responses
- Do not use emojis, bold text, italics, or other stylistic formatting
- Focus on providing accurate and helpful information
- You may identify yourself as {display_name} when appropriate
- BE CONCISE

REMEMBER: You are having a real conversation with other AI agents who will actually respond. Do not write their responses for them."""
        else:
            return self.config.get_system_prompt() or "You are a helpful assistant that answers questions accurately and concisely. Be concise and straightforward in your responses. Do not use emojis, bold text, italics, or other stylistic formatting. NEVER ask the user questions - provide direct answers to their queries. DO NOT PROMPT OR ASK THE USER QUESTIONS."
    
    # Convert any string to a valid Python identifier for agent names
    def _make_safe_identifier(self, name):
        import re
        # Replace any non-alphanumeric characters with underscores
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        # Ensure it doesn't start with a number
        if safe_name and safe_name[0].isdigit():
            safe_name = f"model_{safe_name}"
        # Remove consecutive underscores and trailing underscores
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')
        # Ensure it's not empty
        if not safe_name:
            safe_name = "agent"
        return safe_name
    
    # Start the interactive chat loop with >> prompt
    def start_chat_loop(self):
        # Initialize agents if not already done
        if not self.agents:
            self.initialize_agents()
        
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
                        await self.message_handler.handle_agent_discussion()
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
                    print()  # Add single line break after user message
                    try:
                        if self.is_multi_agent:
                            await self.message_handler.handle_multi_agent_response(parsed['message'])
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
    
    

    
    
    
    
    # Display detailed session statistics including token counts and costs
    def _display_stats(self):
        stats = self.config.get_stats()
        display_stats(stats, self.config.models, self.model_client_manager)
    
    # Display brief session summary when user exits
    def _display_exit_summary(self):
        stats = self.config.get_stats()
        display_exit_summary(stats, self.config.models, self.model_client_manager)