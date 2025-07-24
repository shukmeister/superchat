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


class ChatSession:
    """Manages chat sessions using modern AutoGen - supports both single agent and multi-agent modes."""
    
    def __init__(self, config: SessionConfig):
        self.config = config
        self.model_client_manager = ModelClientManager()
        self.agents = []
        self.is_multi_agent = len(config.models) > 1
        self.team = None  # Will hold RoundRobinGroupChat for multi-agent mode
        
    def initialize_agents(self):
        """Initialize AutoGen agents for the selected models."""
        if not self.config.models:
            raise ValueError("At least one model required for chat session")
        
        self.agents = []
        
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
    
    def get_system_prompt(self, model_name, index, is_multi_agent):
        """Get appropriate system prompt for single or multi-agent mode."""
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
    
    def _make_safe_identifier(self, name):
        """Convert any string to a valid Python identifier."""
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
    
    def start_chat_loop(self):
        """Start the interactive chat loop with >> prompt."""
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
    
    async def _async_chat_loop(self):
        """Async chat loop using AutoGen's modern API."""
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
    
    async def _handle_single_agent_response(self, message):
        """Handle response from single agent."""
        agent = self.agents[0]
        model_name = self.config.models[0]
        
        # For single agent, only pass the current user message - no context needed
        current_conversation = [TextMessage(content=message, source="user")]
        
        
        # Show loading spinner while waiting for response
        with Halo(text="Processing", spinner="dots"):
            task_result = await agent.run(task=current_conversation)
        
        # Extract usage data from TaskResult
        usage_data = self._extract_usage_from_task_result(task_result)
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
    
    async def _handle_group_chat(self, message, is_user_initiated=True):
        """Handle multi-agent conversation with proper turn control."""
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
                # Use a limited message count for brief extended discussion
                termination = MaxMessageTermination(max_messages=4)
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
            usage_data = self._extract_usage_from_task_result(task_result)
            if usage_data:
                self.config.add_usage_data(usage_data)
                
        except Exception as e:
            print(f"Group chat error: {e}")
            print()
    
    def _find_agent_index_by_name(self, agent_name):
        """Find the index of an agent by its name."""
        for i, agent in enumerate(self.agents):
            if agent.name == agent_name:
                return i
        return -1

    async def _handle_multi_agent_response(self, message):
        """Handle responses from multiple agents using RoundRobinGroupChat."""
        await self._handle_group_chat(message, is_user_initiated=True)
    
    async def _handle_agent_discussion(self):
        """Handle empty input to trigger agent discussion."""
        # Create a prompt for agents to continue discussing among themselves
        discussion_prompt = "Continue the discussion. Share your thoughts on the topic or respond to what other agents have said."
        
        await self._handle_group_chat(discussion_prompt, is_user_initiated=False)
    
    
    def _extract_usage_from_message(self, message):
        """Extract token usage data from a single message."""
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        if hasattr(message, 'models_usage') and message.models_usage:
            usage_items = message.models_usage if isinstance(message.models_usage, list) else [message.models_usage]
            
            for usage in usage_items:
                if hasattr(usage, 'prompt_tokens'):
                    total_prompt_tokens += usage.prompt_tokens
                if hasattr(usage, 'completion_tokens'):
                    total_completion_tokens += usage.completion_tokens
        
        if total_prompt_tokens > 0 or total_completion_tokens > 0:
            return {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens
            }
        return None
    
    def _extract_usage_from_task_result(self, task_result):
        """Extract token usage data from AutoGen TaskResult."""
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        for message in task_result.messages:
            if hasattr(message, 'models_usage') and message.models_usage:
                # Handle both single RequestUsage object and list of RequestUsage objects
                usage_items = message.models_usage if isinstance(message.models_usage, list) else [message.models_usage]
                
                for usage in usage_items:
                    if hasattr(usage, 'prompt_tokens'):
                        total_prompt_tokens += usage.prompt_tokens
                    if hasattr(usage, 'completion_tokens'):
                        total_completion_tokens += usage.completion_tokens
        
        if total_prompt_tokens > 0 or total_completion_tokens > 0:
            return {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_prompt_tokens + total_completion_tokens
            }
        return None
    
    def _get_response_from_task_result(self, task_result):
        """Extract the response content from AutoGen TaskResult."""
        # Get the last message which should be the assistant's response
        if task_result.messages:
            last_message = task_result.messages[-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            elif hasattr(last_message, 'text'):
                return last_message.text
        return "No response received"
    
    def _display_stats(self):
        """Display session statistics including token counts and costs."""
        stats = self.config.get_stats()
        
        print("Session Statistics:")
        print(f"  Time elapsed: {stats['duration']}")
        print(f"  Conversation rounds: {stats['conversation_rounds']}")
        print()
        print("Token Usage:")
        print(f"  Input tokens:  {stats['total_input_tokens']:,}")
        print(f"  Output tokens: {stats['total_output_tokens']:,}")
        print(f"  Total tokens:  {stats['total_tokens']:,}")
        
        # Calculate costs for all models
        total_cost = 0
        print()
        print("Estimated Costs:")
        
        for model_name in self.config.models:
            model_config = self.model_client_manager.get_model_config(model_name)
            if model_config:
                input_cost_per_million = model_config.get("input_cost", 0)
                output_cost_per_million = model_config.get("output_cost", 0)
                
                # For simplicity, distribute tokens evenly across models
                # In a more sophisticated version, we'd track per-agent usage
                input_tokens = stats['total_input_tokens'] / len(self.config.models)
                output_tokens = stats['total_output_tokens'] / len(self.config.models)
                
                input_cost = (input_tokens / 1_000_000) * input_cost_per_million
                output_cost = (output_tokens / 1_000_000) * output_cost_per_million
                model_cost = input_cost + output_cost
                total_cost += model_cost
                
                model = model_config.get("model", model_name)
                print(f"  {model}: ${model_cost:.6f}")
        
        print(f"  Total cost: ${total_cost:.6f}")
    
    def _display_exit_summary(self):
        """Display session summary on exit with tokens and costs."""
        stats = self.config.get_stats()
        
        print("Session Summary:")
        print(f"  Time elapsed: {stats['duration']}")
        print(f"  Conversation rounds: {stats['conversation_rounds']}")
        print(f"  Total tokens: {stats['total_tokens']:,}")
        
        # Calculate total cost for all models
        total_cost = 0
        for model_name in self.config.models:
            model_config = self.model_client_manager.get_model_config(model_name)
            if model_config:
                input_cost_per_million = model_config.get("input_cost", 0)
                output_cost_per_million = model_config.get("output_cost", 0)
                
                # For simplicity, distribute tokens evenly across models
                input_tokens = stats['total_input_tokens'] / len(self.config.models)
                output_tokens = stats['total_output_tokens'] / len(self.config.models)
                
                input_cost = (input_tokens / 1_000_000) * input_cost_per_million
                output_cost = (output_tokens / 1_000_000) * output_cost_per_million
                total_cost += input_cost + output_cost
        
        if total_cost > 0:
            print(f"  Total cost: ${total_cost:.6f}")
        print()