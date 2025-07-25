# Message handling utilities for chat sessions

import asyncio
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
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
    
    # Handle multi-agent conversation with proper turn control
    async def handle_group_chat(self, message, is_user_initiated=True):
        if not self.team:
            raise RuntimeError("RoundRobinGroupChat team not initialized")
        
        # Add spacing before group responses
        print()
        
        try:
            # Handle user-initiated messages (one round per agent)
            if is_user_initiated:
                # Run one complete round where each agent responds once
                with Halo(text="Processing", spinner="dots"):
                    task_result = await self.team.run(task=message)
                
                # Reset team for next round to prevent conversation overflow
                max_messages = len(self.agents) + 1
                termination = MaxMessageTermination(max_messages=max_messages)
                self.team = RoundRobinGroupChat(self.agents, termination_condition=termination)
                
            # Handle agent-initiated discussion (empty input from user)
            else:
                # Let agents continue discussing among themselves
                # Allow more extended discussion (2 messages per agent)
                termination = MaxMessageTermination(max_messages=len(self.agents) * 2)
                temp_team = RoundRobinGroupChat(self.agents, termination_condition=termination)
                
                with Halo(text="Processing agent discussion", spinner="dots"):
                    task_result = await temp_team.run(task=message)
            
            # Process and display agent responses (filter out user message echoes)
            agent_response_count = 0
            for msg in task_result.messages:
                # Only display actual agent responses, not user message echoes
                if hasattr(msg, 'source') and msg.source != "user":
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
                    agent_response_count += 1
            
            # Track token usage from all agents in this conversation
            usage_data = extract_usage_from_task_result(task_result)
            if usage_data:
                self.config.add_usage_data(usage_data)
                
        except Exception as e:
            print(f"Group chat error: {e}")
            print()
    
    # Handle responses from multiple agents using RoundRobinGroupChat
    async def handle_multi_agent_response(self, message):
        await self.handle_group_chat(message, is_user_initiated=True)
    
    # Handle empty input to trigger agent discussion
    async def handle_agent_discussion(self):
        # Create a prompt for agents to continue discussing among themselves
        discussion_prompt = "Continue the discussion. Share your thoughts on the topic or respond to what other agents have said."
        
        await self.handle_group_chat(discussion_prompt, is_user_initiated=False)
    
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