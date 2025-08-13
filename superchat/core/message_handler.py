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
        
        # Debug: Log full context before API call
        if debug_logger.enabled:
            # Get agent mapping info for debugging
            agent_mapping_info = self.agent_model_mapping.get(agent.name, {})
            await debug_logger.log_full_context(agent, message, agent_mapping_info)
        
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
        
        # Debug: Log response with comprehensive breakdown after displaying response
        if debug_logger.enabled:
            debug_logger.log_response_with_breakdown(response_content, usage_data, task_result)
            
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
            # Debug: Log multi-agent team context (could log each agent individually if needed)
            if debug_logger.enabled:
                debug_logger._log_separator("MULTI-AGENT TEAM DEBUG")
                print(f"Team Size: {len(self.agents)} agents")
                print(f"Message: {message}")
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
            
            # Debug: Log comprehensive multi-agent response breakdown after displaying responses
            if debug_logger.enabled:
                all_responses = []
                for msg in task_result.messages:
                    if hasattr(msg, 'source') and msg.source != "user":
                        content = getattr(msg, 'content', str(msg))
                        agent_name = getattr(msg, 'source', 'agent')
                        all_responses.append(f"[{agent_name}]: {content}")
                
                combined_response = "\n".join(all_responses)
                debug_logger.log_response_with_breakdown(combined_response, usage_data, task_result)
                
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
        """Handle OpenRouter credits/quota errors. Returns True if handled, False otherwise."""
        if self._is_openrouter_quota_error(error):
            print("\nOpenRouter Credits Error: Insufficient credits to complete this request.")
            print("Add credits at: https://openrouter.ai/credits")
            print()
            return True
        return False
    
    # Check if error is related to OpenRouter credits/quota
    def _is_openrouter_quota_error(self, error):
        """Check if the error is related to OpenRouter credits or quota limits."""
        error_str = str(error).lower()
        # Check for common OpenRouter quota/credits error indicators
        return any(indicator in error_str for indicator in [
            "can only afford",
            "insufficient credits", 
            "quota exceeded",
            "402",  # HTTP status code for payment required
            "credit limit",
            "balance"
        ])