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
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from halo import Halo
from superchat.core.session import SessionConfig
from superchat.core.model_client import ModelClientManager
from superchat.utils.parser import parse_input
from superchat.utils.identifiers import get_model_identifier
from superchat.utils.model_resolver import get_display_name
from superchat.utils.stats import display_stats, display_exit_summary, extract_usage_from_task_result


# Chat session manager that handles both single and multi-agent conversations
class ChatSession:
    
    # Initialize chat session with configuration
    def __init__(self, config: SessionConfig):
        self.config = config
        self.model_client_manager = ModelClientManager()
        self.agents = []
        self.is_multi_agent = len(config.models) > 1
        self.team = None
        
    # Initialize AutoGen agents for the selected models
    def initialize_agents(self):
        if not self.config.models:
            raise ValueError("At least one model required for chat session")
        
        self.agents = []
        
        # Create an agent for each configured model
        for i, model_name in enumerate(self.config.models):
            # Create model client using modern AutoGen approach
            # Skip API key validation since it was already checked at startup
            model_client = self.model_client_manager.create_model_client(model_name, skip_validation=True)
            
            # Create AutoGen assistant agent with valid Python identifier name
            safe_name = self._make_safe_identifier(model_name)
            
            # Get debate-specific system prompt for multi-agent or regular prompt for single agent
            system_prompt = self.get_system_prompt(model_name, i, self.is_multi_agent)
            
            agent = AssistantAgent(
                name=f"agent_{safe_name}_{i}",
                model_client=model_client,
                system_message=system_prompt
            )
            
            self.agents.append(agent)
        
        # Create RoundRobinGroupChat for multi-agent mode
        if self.is_multi_agent:
            # Set up termination to stop after one complete round (each agent responds once)
            max_messages = len(self.agents) + 1  # +1 for the user message
            termination = MaxMessageTermination(max_messages=max_messages)
            self.team = RoundRobinGroupChat(self.agents, termination_condition=termination)
    
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
                        await self._handle_agent_discussion()
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
                            await self._handle_multi_agent_response(parsed['message'])
                        else:
                            await self._handle_single_agent_response(parsed['message'])
                    except Exception as e:
                        print(f"Error: {e}\n")
                    
            except KeyboardInterrupt:
                print("\nTerminating connection")
                break
            except EOFError:
                print("\nTerminating connection")  
                break
    
    # Handle response from single agent (no group chat needed)
    async def _handle_single_agent_response(self, message):
        agent = self.agents[0]
        model_name = self.config.models[0]
        
        # For single agent, only pass the current user message - no context needed
        current_conversation = [TextMessage(content=message, source="user")]
        
        
        # Show loading spinner while waiting for response
        with Halo(text="Processing", spinner="dots"):
            task_result = await agent.run(task=current_conversation)
        
        # Extract usage data from TaskResult
        usage_data = extract_usage_from_task_result(task_result)
        if usage_data:
            self.config.add_usage_data(usage_data)
        
        # Get the response content from the last message
        response_content = self._get_response_from_task_result(task_result)
        
        # For single agent mode, no need to track conversation history
        
        model_config = self.model_client_manager.get_model_config(model_name)
        if model_config:
            model = model_config.get("model", model_name)
            # Get Russian letter identifier
            model_index = self.config.models.index(model_name) if model_name in self.config.models else 0
            identifier = get_model_identifier(model_index)
            print(f"{identifier} [{model}]: {response_content}\n")
        else:
            print(f"[{model_name}]: {response_content}\n")
    
    # Handle multi-agent conversation with proper turn control
    async def _handle_group_chat(self, message, is_user_initiated=True):
        if not self.team:
            raise RuntimeError("RoundRobinGroupChat team not initialized")
        
        print()  # Add line break before group chat
        
        try:
            if is_user_initiated:
                # User provided input - run exactly one round (each agent responds once)
                with Halo(text="Processing", spinner="dots"):
                    task_result = await self.team.run(task=message)
                
                # Reset the team for next round by creating a new instance
                max_messages = len(self.agents) + 1
                termination = MaxMessageTermination(max_messages=max_messages)
                self.team = RoundRobinGroupChat(self.agents, termination_condition=termination)
                
            else:
                # Empty input - let agents continue discussing
                # Allow each agent one more exchange (2 messages per agent)
                termination = MaxMessageTermination(max_messages=len(self.agents) * 2)
                temp_team = RoundRobinGroupChat(self.agents, termination_condition=termination)
                
                with Halo(text="Processing agent discussion", spinner="dots"):
                    task_result = await temp_team.run(task=message)
            
            # Display only the new agent responses (skip the user message echo)
            agent_response_count = 0
            for msg in task_result.messages:
                if hasattr(msg, 'source') and msg.source != "user":
                    # This is an agent response - display it
                    agent_name = getattr(msg, 'source', 'agent')
                    content = getattr(msg, 'content', str(msg))
                    
                    # Find which agent this is and get identifier
                    agent_index = self._find_agent_index_by_name(agent_name)
                    if agent_index >= 0:
                        identifier = get_model_identifier(agent_index)
                        model_name = self.config.models[agent_index]
                        model_config = self.model_client_manager.get_model_config(model_name)
                        if model_config:
                            model = model_config.get("model", model_name)
                            print(f"{identifier} [{model}]: {content}")
                        else:
                            print(f"{identifier} [{model_name}]: {content}")
                    else:
                        print(f"[{agent_name}]: {content}")
                    print()
                    agent_response_count += 1
            
            # Extract usage data from the group chat result
            usage_data = extract_usage_from_task_result(task_result)
            if usage_data:
                self.config.add_usage_data(usage_data)
                
        except Exception as e:
            print(f"Group chat error: {e}")
            print()
    
    # Find the index of an agent by matching its name
    def _find_agent_index_by_name(self, agent_name):
        for i, agent in enumerate(self.agents):
            if agent.name == agent_name:
                return i
        return -1

    # Handle responses from multiple agents using RoundRobinGroupChat
    async def _handle_multi_agent_response(self, message):
        await self._handle_group_chat(message, is_user_initiated=True)
    
    # Handle empty input to trigger agent discussion
    async def _handle_agent_discussion(self):
        # Create a prompt for agents to continue discussing among themselves
        discussion_prompt = "Continue the discussion. Share your thoughts on the topic or respond to what other agents have said."
        
        await self._handle_group_chat(discussion_prompt, is_user_initiated=False)
    
    
    # Extract the actual response text from AutoGen TaskResult
    def _get_response_from_task_result(self, task_result):
        # Get the last message which should be the assistant's response
        if task_result.messages:
            last_message = task_result.messages[-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            elif hasattr(last_message, 'text'):
                return last_message.text
        return "No response received"
    
    # Display detailed session statistics including token counts and costs
    def _display_stats(self):
        stats = self.config.get_stats()
        display_stats(stats, self.config.models, self.model_client_manager)
    
    # Display brief session summary when user exits
    def _display_exit_summary(self):
        stats = self.config.get_stats()
        display_exit_summary(stats, self.config.models, self.model_client_manager)