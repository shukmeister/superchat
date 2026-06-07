# Pure AI message processing and response formatting utilities

import asyncio
from autogen_agentchat.messages import TextMessage
from halo import Halo
from superchat.utils.stats import extract_usage_from_task_result
from superchat.utils.identifiers import get_model_identifier
from superchat.utils.debug import get_debug_logger


class MessageHandler:
    """Handles pure AI message processing and response formatting (no conversation coordination)."""
    
    # Initialize message handler with pre-configured components from setup
    def __init__(self, config, agents, model_client_manager, agent_model_mapping):
        self.config = config
        self.agents = agents
        self.model_client_manager = model_client_manager
        self.agent_model_mapping = agent_model_mapping
        self.team = None  # Will be set by setup for multi-agent mode
    
    # Process single agent message and display formatted response
    async def handle_single_agent_response(self, message, agent_index=0):
        agent = self.agents[agent_index]
        model_name = self.config.models[agent_index]
        debug_logger = get_debug_logger()

        # Create new message for agent (agent maintains its own conversation history)
        new_message = TextMessage(content=message, source="user")

        # Debug: Estimate token usage before API call
        estimated_tokens = None
        if debug_logger.enabled:
            # Get agent mapping info for debugging
            agent_mapping_info = self.agent_model_mapping.get(agent.name, {})
            await debug_logger.log_full_context(agent, message, agent_mapping_info)

            # Estimate tokens for this request
            estimated_tokens = await debug_logger.estimate_request_tokens(agent, message)

        # Get agent response with loading indicator
        with Halo(text="Processing", spinner="dots"):
            try:
                task_result = await agent.run(task=[new_message])
            except Exception as e:
                if self._handle_openrouter_error(e):
                    return None
                raise

        # Track token usage for stats
        usage_data = extract_usage_from_task_result(task_result)
        if usage_data:
            self.config.add_usage_data(usage_data)

        # Extract the actual response text
        response_content = self._get_response_from_task_result(task_result)

        # Display response with proper model identifier and formatting
        # Get unique identifier for this model
        model_index = self.config.models.index(model_name) if model_name in self.config.models else 0
        identifier = get_model_identifier(model_index)
        agent_header = self._format_agent_display(identifier, model_name)
        print(f"{agent_header}\n> {response_content}\n")

        # Debug: Display token analysis (estimated vs actual)
        if debug_logger.enabled and estimated_tokens:
            debug_logger.display_token_comparison(estimated_tokens, usage_data)
            
        # Return transcript exchange data for staged flow capture
        return {
            'user_message': message,
            'agent_response': response_content,
            'agent_name': agent.name,
            'model_name': model_name,
            'agent_index': agent_index
        }
    
    # Process team message and display all agent responses
    async def send_to_team(self, team, message):
        """Send message to a team and handle response formatting."""
        if not team:
            raise RuntimeError("Team not provided")

        debug_logger = get_debug_logger()

        try:
            # Debug: Log multi-agent team context and estimate tokens
            team_estimates = None
            if debug_logger.enabled:
                debug_logger._log_separator("MULTI-AGENT TEAM DEBUG")
                print(f"Team Size: {len(self.agents)} agents")
                print(f"Message: {message}")

                # Estimate tokens for all agents in team
                if self.agents:
                    team_estimates = await debug_logger.estimate_team_request_tokens(self.agents, message)

                debug_logger._log_separator_end()

            # Send message to team with loading indicator
            with Halo(text="Processing", spinner="dots"):
                try:
                    task_result = await team.run(task=message)
                except Exception as e:
                    if self._handle_openrouter_error(e):
                        return None
                    raise

            # Track token usage from all agents in this conversation
            usage_data = extract_usage_from_task_result(task_result)
            if usage_data:
                self.config.add_usage_data(usage_data)

            # Process and display agent responses (filter out user message echoes)
            for msg in task_result.messages:
                # Only display actual agent responses, not user message echoes
                if hasattr(msg, 'source') and msg.source != "user":
                    self._format_and_display_agent_response(msg)

            # Debug: Display token analysis for multi-agent team
            if debug_logger.enabled:
                if team_estimates:
                    debug_logger.display_team_token_comparison(team_estimates, usage_data, self.agent_model_mapping)
                
            return task_result
                
        except Exception as e:
            print(f"Team message error: {e}")
            print()
            raise
    
    # Format and display individual agent response with model identification
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
            agent_header = self._format_agent_display(identifier, model_name)
            print(f"{agent_header}\n> {content}\n")
        else:
            # Fallback for unknown agents
            print(f"\033[4m[{agent_name}]\033[0m:\n> {content}\n")
    
    # Legacy method - conversation coordination now handled by ChatSession
    async def handle_multi_agent_response(self, message):
        """Deprecated: Use ChatSession._handle_multi_agent_conversation instead."""
        if self.team:
            return await self.send_to_team(self.team, message)
        else:
            raise RuntimeError("No team configured for multi-agent response")
    
    # Legacy method - agent discussions now handled by ChatSession
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
    
    # Format agent header with underlined model label
    def _format_agent_display(self, identifier, model_name):
        """Create formatted agent header with underlined model label."""
        label = self.model_client_manager.get_model_label(model_name)
        return f"[{identifier}] \033[4m{label}\033[0m:"
    
    # Handle OpenRouter-specific errors gracefully
    def _handle_openrouter_error(self, error):
        """Handle known OpenRouter errors. Returns True if handled, False otherwise."""
        if self._is_openrouter_quota_error(error):
            print("\nOpenRouter Credits Error: Insufficient credits to complete this request.")
            print("Add credits at: https://openrouter.ai/credits")
            print()
            return True
        if self._is_no_compliant_provider_error(error):
            print("\nNo available provider met the privacy requirements for this request.")
            print("This can happen during provider outages. Try again in a moment.")
            print()
            return True
        return False

    # Check if error is related to OpenRouter credits/quota
    def _is_openrouter_quota_error(self, error):
        """Check if the error is related to OpenRouter credits or quota limits."""
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in [
            "can only afford",
            "insufficient credits",
            "quota exceeded",
            "402",
            "credit limit",
            "balance"
        ])

    # Check if error is due to no privacy-compliant provider being available
    def _is_no_compliant_provider_error(self, error):
        """Check if the error is due to no provider meeting zdr/data_collection requirements."""
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in [
            "no providers",
            "no available",
            "provider unavailable",
            "503",
            "all providers",
            "data retention",
            "data_collection",
            "zdr",
        ])