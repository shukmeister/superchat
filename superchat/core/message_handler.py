# Message handling utilities for chat sessions

import asyncio
from autogen_agentchat.messages import TextMessage
from halo import Halo
from superchat.utils.stats import extract_usage_from_task_result
from superchat.utils.identifiers import get_model_identifier


class MessageHandler:
    """Handles all message processing and agent response logic."""
    
    # Initialize message handler with references to chat session components
    def __init__(self, config, agents, model_client_manager, agent_model_mapping):
        self.config = config
        self.agents = agents
        self.model_client_manager = model_client_manager
        self.agent_model_mapping = agent_model_mapping
        self.team = None  # Will be set by chat session for multi-agent mode
    
    # Handle response from single agent (no group chat needed)
    async def handle_single_agent_response(self, message):
        agent = self.agents[0]
        model_name = self.config.models[0]
        
        # Create conversation with just the current user message (no history tracking)
        current_conversation = [TextMessage(content=message, source="user")]
        
        # Get agent response with loading indicator
        with Halo(text="Processing", spinner="dots"):
            task_result = await agent.run(task=current_conversation)
        
        # Track token usage for stats
        usage_data = extract_usage_from_task_result(task_result)
        if usage_data:
            self.config.add_usage_data(usage_data)
        
        # Extract the actual response text
        response_content = self._get_response_from_task_result(task_result)
        
        # Display response with proper model identifier and formatting
        model_config = self.model_client_manager.get_model_config(model_name)
        if model_config:
            model = model_config.get("model", model_name)
            # Get unique identifier for this model
            model_index = self.config.models.index(model_name) if model_name in self.config.models else 0
            identifier = get_model_identifier(model_index)
            print(f"{identifier} [{model}]: {response_content}\n")
        else:
            print(f"[{model_name}]: {response_content}\n")
    
    # Send message to a specific team and display formatted responses
    async def send_to_team(self, team, message):
        """Send message to a team and handle response formatting."""
        if not team:
            raise RuntimeError("Team not provided")
        
        try:
            # Send message to team with loading indicator
            with Halo(text="Processing", spinner="dots"):
                task_result = await team.run(task=message)
            
            # Process and display agent responses (filter out user message echoes)
            for msg in task_result.messages:
                # Only display actual agent responses, not user message echoes
                if hasattr(msg, 'source') and msg.source != "user":
                    self._format_and_display_agent_response(msg)
            
            # Track token usage from all agents in this conversation
            usage_data = extract_usage_from_task_result(task_result)
            if usage_data:
                self.config.add_usage_data(usage_data)
                
            return task_result
                
        except Exception as e:
            print(f"Team message error: {e}")
            print()
            raise
    
    # Format and display individual agent response
    def _format_and_display_agent_response(self, msg):
        """Format and display a single agent response with proper model identification."""
        # Extract agent info and response content
        agent_name = getattr(msg, 'source', 'agent')
        content = getattr(msg, 'content', str(msg))
        
        # Get agent info from direct mapping (more reliable than index lookup)
        if agent_name in self.agent_model_mapping:
            agent_info = self.agent_model_mapping[agent_name]
            identifier = agent_info['identifier']
            model_name = agent_info['model_name']
            model_config = self.model_client_manager.get_model_config(model_name)
            if model_config:
                model = model_config.get("model", model_name)
                print(f"{identifier} [{model}]: {content}")
            else:
                print(f"{identifier} [{model_name}]: {content}")
        else:
            print(f"[{agent_name}]: {content}")
        print()
    
    # Handle responses from multiple agents using RoundRobinGroupChat (deprecated - use send_to_team)
    async def handle_multi_agent_response(self, message):
        """Deprecated: Use ChatSession._handle_multi_agent_conversation instead."""
        if self.team:
            return await self.send_to_team(self.team, message)
        else:
            raise RuntimeError("No team configured for multi-agent response")
    
    # Handle empty input to trigger agent discussion (deprecated - use ChatSession._handle_agent_discussion)
    async def handle_agent_discussion(self):
        """Deprecated: Use ChatSession._handle_agent_discussion instead."""
        raise RuntimeError("Agent discussion should be handled by ChatSession")
    
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