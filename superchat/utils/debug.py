"""Comprehensive debug utilities for superchat - API call logging and AutoGen context analysis."""

import os
import logging
import tiktoken


# Global debug logger instance
_debug_logger = None

def get_debug_logger():
    """Get the global debug logger instance."""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger.from_env()
    return _debug_logger

def set_debug_enabled(enabled):
    """Enable or disable debug logging globally."""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger(enabled=enabled)
    else:
        _debug_logger.enabled = enabled
        # Set up AutoGen logging if enabling debug
        if enabled and not hasattr(_debug_logger, '_autogen_setup'):
            _debug_logger._setup_autogen_logging()
            _debug_logger._autogen_setup = True

def initialize_debug_logger(cli_debug_flag=False):
    """Initialize the global debug logger with CLI and environment settings."""
    global _debug_logger
    _debug_logger = DebugLogger.from_env_and_args(cli_debug_flag)
    return _debug_logger


# Token counting helper functions using tiktoken
def get_tokenizer():
    """Get tiktoken encoding for token counting (using cl100k_base as baseline)."""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        # Fallback to a default encoding if cl100k_base is not available
        return tiktoken.get_encoding("gpt2")


def count_tokens_in_text(text: str) -> int:
    """Count tokens in a text string using tiktoken."""
    try:
        encoding = get_tokenizer()
        return len(encoding.encode(text))
    except Exception:
        # Fallback: rough estimate of 1 token per 4 characters
        return len(text) // 4


def count_tokens_in_message(message) -> int:
    """Count tokens in an AutoGen message object."""
    try:
        # Extract content from message
        content = ""
        if hasattr(message, 'content'):
            content = str(message.content)
        else:
            content = str(message)

        # Count tokens in content
        token_count = count_tokens_in_text(content)

        # Add overhead for message structure (role, name, etc.)
        # OpenAI format adds ~4 tokens per message for structure
        token_count += 4

        return token_count
    except Exception:
        return 0


def count_tokens_in_message_list(messages: list) -> dict:
    """Count tokens in a list of messages with per-message breakdown."""
    total_tokens = 0
    per_message = []

    for i, msg in enumerate(messages):
        token_count = count_tokens_in_message(msg)
        total_tokens += token_count

        # Get role/source for display
        role = getattr(msg, 'source', 'unknown')

        per_message.append({
            'index': i,
            'role': role,
            'tokens': token_count
        })

    # Add 2 tokens for priming the response (assistant:)
    total_tokens += 2

    return {
        'total_tokens': total_tokens,
        'per_message': per_message
    }


class DebugLogger:
    """Comprehensive debug logger for API calls and AutoGen context analysis."""
    
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.call_count = 0
        
        # Set up AutoGen trace logging if debug is enabled
        if self.enabled:
            self._setup_autogen_logging()
    
    @classmethod
    def from_env_and_args(cls, cli_debug_flag=False):
        """Create debug logger based on environment variables and CLI arguments."""
        env_debug = os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')
        enabled = cli_debug_flag or env_debug
        return cls(enabled=enabled)
    
    @classmethod 
    def from_env(cls):
        """Create debug logger based on environment only (legacy method)."""
        enabled = os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')
        return cls(enabled=enabled)
    
    def _setup_autogen_logging(self):
        """Set up AutoGen's trace logging for system-level debugging."""
        try:
            from autogen_core import TRACE_LOGGER_NAME
            
            # Configure AutoGen trace logger
            trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
            
            # Only add handler if one doesn't exist
            if not trace_logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('AUTOGEN: %(message)s')
                handler.setFormatter(formatter)
                trace_logger.addHandler(handler)
            
            trace_logger.setLevel(logging.DEBUG)
            
        except ImportError:
            # AutoGen core not available, skip trace logging
            pass
    
    def log_api_call_start(self, model_name, messages):
        """Log the start of an API call with full message content."""
        if not self.enabled:
            return
            
        self.call_count += 1
        
        print(f"\n{'='*80}")
        print(f"API CALL #{self.call_count} [{model_name}]")
        print(f"Total messages: {len(messages)}")
        print("-" * 80)
        
        for i, msg in enumerate(messages):
            # Get message content - no truncation
            content = str(msg.content) if hasattr(msg, 'content') else str(msg)
            role = getattr(msg, 'source', 'UNKNOWN').upper()
            
            print(f"[{i+1}] {role}:")
            print(f"Content: {content}")
            
            # Show message structure
            msg_type = type(msg).__name__
            print(f"Type: {msg_type}")
            
            # Show additional attributes if present
            if hasattr(msg, 'models_usage') and msg.models_usage:
                print("Has usage data: Yes")
            
            print()
    
    def log_api_call_end(self, response_content, usage_data=None):
        """Log the end of an API call with response and real token usage."""
        if not self.enabled:
            return
            
        print("RESPONSE:")
        if response_content:
            print(f"Content: {response_content}")
        
        if usage_data:
            input_tokens = usage_data.get('prompt_tokens', 0)
            output_tokens = usage_data.get('completion_tokens', 0) 
            total_tokens = usage_data.get('total_tokens', input_tokens + output_tokens)
            print(f"REAL TOKENS: {input_tokens} input + {output_tokens} output = {total_tokens} total")
        else:
            print("No token usage data available")
        
        print("=" * 80)
    
    def log_estimated_tokens(self, estimated_tokens):
        """Log estimated tokens before API call (for comparison)."""
        if not self.enabled:
            return
        print(f"ESTIMATED TOKENS: ~{estimated_tokens}")
    
    def _log_separator(self, title):
        """Print a debug section separator."""
        if not self.enabled:
            return
        print(f"{'='*80}")
        print(f"{title}")
        print("-" * 80)
    
    def _log_separator_end(self):
        """Print end separator."""
        if not self.enabled:
            return
        print("=" * 80)
        print()
    
    async def log_agent_context(self, agent, message_description=""):
        """Log complete agent context including system prompts and conversation history."""
        if not self.enabled:
            return
        
        print(f"AGENT CONTEXT [{getattr(agent, 'name', 'unknown')}]:")
        
        # Get system message if available
        try:
            if hasattr(agent, '_system_messages') and agent._system_messages:
                system_msg = agent._system_messages[0]
                system_content = getattr(system_msg, 'content', str(system_msg))
                print(f"System Message: {system_content}")
            else:
                print("System Message: Not accessible")
        except Exception as e:
            print(f"System Message: Error accessing ({e})")
        
        print()
        
        # Get conversation history from model context
        try:
            if hasattr(agent, '_model_context'):
                context_messages = await agent._model_context.get_messages()
                print(f"CONTEXT HISTORY ({len(context_messages)} messages):")
                
                for i, msg in enumerate(context_messages):
                    content = getattr(msg, 'content', str(msg))
                    source = getattr(msg, 'source', 'unknown')
                    msg_type = type(msg).__name__
                    
                    # Truncate long content for readability
                    display_content = content[:100] + "..." if len(content) > 100 else content
                    print(f"  [{i+1}] {source.upper()} ({msg_type}): {display_content}")
            else:
                print("Context History: Not accessible")
        except Exception as e:
            print(f"Context History: Error accessing ({e})")
        
        print()
        
    def log_agent_configuration(self, agent, agent_mapping_info=None):
        """Log agent model configuration and settings."""
        if not self.enabled:
            return
        
        print(f"AGENT CONFIGURATION [{getattr(agent, 'name', 'unknown')}]:")
        
        # Get model client information
        try:
            if hasattr(agent, '_model_client'):
                model_client = agent._model_client
                model_name = getattr(model_client, 'model', 'unknown')
                print(f"Model: {model_name}")
                
                # Try to get additional model info
                if hasattr(model_client, 'model_info'):
                    model_info = model_client.model_info
                    print(f"Model Info: {model_info}")
                
                if hasattr(model_client, 'base_url'):
                    base_url = model_client.base_url
                    print(f"API Endpoint: {base_url}")
            else:
                print("Model Client: Not accessible")
        except Exception as e:
            print(f"Model Client: Error accessing ({e})")
        
        # Show agent mapping info if provided
        if agent_mapping_info:
            print(f"Agent Mapping: {agent_mapping_info}")
        
        print()
        
    async def log_conversation_buffer(self, agent):
        """Log current state of conversation buffer."""
        if not self.enabled:
            return
        
        print("CONVERSATION BUFFER STATE:")
        
        try:
            if hasattr(agent, '_model_context'):
                context = agent._model_context
                
                # Get buffer size if available
                if hasattr(context, 'buffer_size'):
                    print(f"Buffer Size: {context.buffer_size}")
                
                # Get current messages count
                try:
                    messages = await context.get_messages()
                    print(f"Current Messages: {len(messages)}")
                    
                    # Calculate approximate token usage per message
                    total_chars = sum(len(str(getattr(msg, 'content', str(msg)))) for msg in messages)
                    estimated_tokens = total_chars // 4  # Rough estimate
                    print(f"Estimated Context Tokens: ~{estimated_tokens}")
                    
                except Exception as e:
                    print(f"Messages Count: Error accessing ({e})")
                
                # Skip context state to avoid async issues
                        
            else:
                print("Model Context: Not accessible")
                
        except Exception as e:
            print(f"Buffer State: Error accessing ({e})")
        
        print()
        
    def log_autogen_events(self, task_result):
        """Log AutoGen events from task result including tool calls."""
        if not self.enabled:
            return
        
        print("AUTOGEN EVENTS:")
        
        try:
            if hasattr(task_result, 'messages') and task_result.messages:
                events_found = []
                
                for i, msg in enumerate(task_result.messages):
                    msg_type = type(msg).__name__
                    
                    # Check for different event types
                    if 'Event' in msg_type:
                        events_found.append(f"[{i+1}] {msg_type}")
                        
                        # Try to get event details
                        if hasattr(msg, 'content'):
                            content = str(msg.content)[:100] + "..." if len(str(msg.content)) > 100 else str(msg.content)
                            events_found.append(f"    Content: {content}")
                    
                    # Check for tool-related messages
                    elif 'Tool' in msg_type:
                        events_found.append(f"[{i+1}] {msg_type}")
                        
                        if hasattr(msg, 'content'):
                            content = str(msg.content)[:100] + "..." if len(str(msg.content)) > 100 else str(msg.content)
                            events_found.append(f"    Content: {content}")
                
                if events_found:
                    for event in events_found:
                        print(event)
                else:
                    print("No AutoGen events found in task result")
                    
                # Check for inner_messages if available
                if hasattr(task_result, 'inner_messages'):
                    inner_msgs = task_result.inner_messages
                    if inner_msgs:
                        print(f"Inner Messages: {len(inner_msgs)} found")
                        for i, inner_msg in enumerate(inner_msgs):
                            inner_type = type(inner_msg).__name__
                            print(f"  [{i+1}] {inner_type}")
                    
            else:
                print("No messages found in task result")
                
        except Exception as e:
            print(f"Events: Error accessing ({e})")
        
        print()
        
    def log_token_breakdown(self, usage_data, context_info=None):
        """Log detailed token usage breakdown by component."""
        if not self.enabled:
            return
        
        print("TOKEN BREAKDOWN:")
        
        if usage_data:
            input_tokens = usage_data.get('prompt_tokens', 0)
            output_tokens = usage_data.get('completion_tokens', 0)
            total_tokens = usage_data.get('total_tokens', input_tokens + output_tokens)
            
            print(f"Input Tokens: {input_tokens}")
            print(f"Output Tokens: {output_tokens}")
            print(f"Total Tokens: {total_tokens}")
            
            # If context info provided, try to break down input tokens
            if context_info:
                print("Input Token Breakdown:")
                if 'system_tokens' in context_info:
                    print(f"  System Prompt: {context_info['system_tokens']}")
                if 'context_tokens' in context_info:
                    print(f"  Context History: {context_info['context_tokens']}")
                if 'current_tokens' in context_info:
                    print(f"  Current Message: {context_info['current_tokens']}")
        else:
            print("No usage data available")
        
        print()
        
    async def log_full_context(self, agent, message, agent_mapping_info=None):
        """Orchestrator method for comprehensive context debugging."""
        if not self.enabled:
            return
        
        # Increment call count for this debug session
        self.call_count += 1
        
        self._log_separator(f"CONTEXT DEBUG - CALL #{self.call_count}")
        
        await self.log_agent_context(agent, str(message))
        await self.log_conversation_buffer(agent)
        
        # Show incoming message after buffer state
        print(f"INCOMING MESSAGE: {str(message)}")
        
        self._log_separator_end()
        
    def log_response_with_breakdown(self, response_content, usage_data, task_result=None, context_info=None):
        """Log response with comprehensive breakdown."""
        if not self.enabled:
            return

        self._log_separator("RESPONSE DEBUG")

        print("RESPONSE:")
        if response_content:
            print(f"Content: {response_content}")
            print()

        self.log_token_breakdown(usage_data, context_info)

        if task_result:
            self.log_autogen_events(task_result)

        self._log_separator_end()

    async def estimate_request_tokens(self, agent, current_message: str) -> dict:
        """Estimate token count for upcoming API request with detailed breakdown."""
        result = {
            'system_prompt_tokens': 0,
            'context_tokens': 0,
            'current_message_tokens': 0,
            'total_estimated_tokens': 0,
            'message_count': 0,
            'context_breakdown': []
        }

        try:
            # 1. Count system prompt tokens
            if hasattr(agent, '_system_messages') and agent._system_messages:
                system_msg = agent._system_messages[0]
                result['system_prompt_tokens'] = count_tokens_in_message(system_msg)

            # 2. Count context buffer tokens
            if hasattr(agent, '_model_context'):
                context_messages = await agent._model_context.get_messages()
                result['message_count'] = len(context_messages)

                if context_messages:
                    breakdown = count_tokens_in_message_list(context_messages)
                    result['context_tokens'] = breakdown['total_tokens']
                    result['context_breakdown'] = breakdown['per_message']

            # 3. Count current message tokens
            result['current_message_tokens'] = count_tokens_in_text(current_message) + 4  # +4 for structure

            # 4. Calculate total
            result['total_estimated_tokens'] = (
                result['system_prompt_tokens'] +
                result['context_tokens'] +
                result['current_message_tokens']
            )

        except Exception as e:
            print(f"Error estimating tokens: {e}")

        return result

    def display_token_comparison(self, estimated: dict, actual_usage: dict):
        """Display side-by-side comparison of estimated vs actual token usage."""
        if not self.enabled:
            return

        self._log_separator("TOKEN ANALYSIS")

        # Pre-flight estimate
        print(f"PRE-FLIGHT ESTIMATE: {estimated['total_estimated_tokens']:,} tokens")
        print(f"  - System prompt: {estimated['system_prompt_tokens']:,} tokens")
        print(f"  - Context history: {estimated['context_tokens']:,} tokens ({estimated['message_count']} messages)")
        print(f"  - Current message: {estimated['current_message_tokens']:,} tokens")
        print()

        # Actual API usage
        if actual_usage:
            input_tokens = actual_usage.get('prompt_tokens', 0)
            output_tokens = actual_usage.get('completion_tokens', 0)
            total_actual = actual_usage.get('total_tokens', input_tokens + output_tokens)

            print(f"ACTUAL API USAGE: {total_actual:,} tokens")
            print(f"  - Input (prompt): {input_tokens:,} tokens")
            print(f"  - Output (completion): {output_tokens:,} tokens")
            print()

            # Calculate difference
            input_diff = input_tokens - estimated['total_estimated_tokens']
            diff_percent = (input_diff / estimated['total_estimated_tokens'] * 100) if estimated['total_estimated_tokens'] > 0 else 0

            print(f"DIFFERENCE: {'+' if input_diff >= 0 else ''}{input_diff:,} tokens ({'+' if diff_percent >= 0 else ''}{diff_percent:.1f}%)")

            # Warning if significant difference
            if abs(diff_percent) > 10:
                print(f"WARNING: Difference exceeds 10% - possible tokenizer mismatch or hidden overhead")
        else:
            print("ACTUAL API USAGE: No usage data available")

        print()

        # Optional: Show per-message context breakdown
        if estimated['context_breakdown'] and estimated['message_count'] > 0:
            print("CONTEXT BREAKDOWN:")
            for msg_info in estimated['context_breakdown']:
                print(f"  [{msg_info['index']+1}] {msg_info['role']}: {msg_info['tokens']:,} tokens")
            print()

        self._log_separator_end()

    async def log_token_analysis(self, agent, current_message: str, actual_usage: dict = None):
        """Combined token analysis: estimate, display, and compare with actual usage."""
        if not self.enabled:
            return

        # Get estimation
        estimated = await self.estimate_request_tokens(agent, current_message)

        # Display comparison
        self.display_token_comparison(estimated, actual_usage)

        return estimated

    async def estimate_team_request_tokens(self, agents: list, current_message: str) -> dict:
        """Estimate token count for all agents in a team debate.

        Args:
            agents: List of agent objects in the team
            current_message: User message that will be sent to the team

        Returns:
            dict: Team-wide token estimation with per-agent breakdown
        """
        per_agent = []
        total = 0

        for i, agent in enumerate(agents):
            # Get individual agent estimate
            estimate = await self.estimate_request_tokens(agent, current_message)

            # Get agent name for display
            agent_name = getattr(agent, 'name', f'agent_{i}')

            per_agent.append({
                'agent_name': agent_name,
                'agent_index': i,
                'system_tokens': estimate['system_prompt_tokens'],
                'context_tokens': estimate['context_tokens'],
                'message_tokens': estimate['current_message_tokens'],
                'total_tokens': estimate['total_estimated_tokens'],
                'message_count': estimate['message_count'],
                'context_breakdown': estimate['context_breakdown']
            })

            total += estimate['total_estimated_tokens']

        return {
            'per_agent_estimates': per_agent,
            'total_estimated_tokens': total,
            'agent_count': len(agents)
        }

    def display_team_token_comparison(self, team_estimates: dict, actual_usage: dict, agent_mapping: dict = None):
        """Display per-agent token breakdown and comparison for team debates.

        Args:
            team_estimates: Result from estimate_team_request_tokens()
            actual_usage: Actual token usage from API response
            agent_mapping: Optional mapping of agent names to display info
        """
        if not self.enabled:
            return

        self._log_separator("TEAM TOKEN ANALYSIS")

        # Pre-flight estimate - team summary
        total_estimate = team_estimates['total_estimated_tokens']
        agent_count = team_estimates['agent_count']

        print(f"PRE-FLIGHT ESTIMATE (Team): {total_estimate:,} tokens")
        print(f"Team Size: {agent_count} agents")
        print()

        # Per-agent breakdown
        for agent_est in team_estimates['per_agent_estimates']:
            agent_name = agent_est['agent_name']
            agent_index = agent_est['agent_index']

            # Get display name from agent mapping if available
            display_name = agent_name
            identifier = f"#{agent_index}"
            if agent_mapping and agent_name in agent_mapping:
                mapping_info = agent_mapping[agent_name]
                identifier = mapping_info.get('identifier', f"#{agent_index}")
                model_name = mapping_info.get('model_name', 'unknown')
                # Use identifier format like [K2], [V3], etc.
                display_label = f"[{identifier}]"
            else:
                display_label = f"[{identifier}]"

            print(f"Agent {agent_index + 1} {display_label}: {agent_est['total_tokens']:,} tokens")
            print(f"  - System prompt: {agent_est['system_tokens']:,} tokens")
            print(f"  - Context history: {agent_est['context_tokens']:,} tokens ({agent_est['message_count']} messages)")
            print(f"  - Current message: {agent_est['message_tokens']:,} tokens")
            print()

        # Actual API usage
        if actual_usage:
            input_tokens = actual_usage.get('prompt_tokens', 0)
            output_tokens = actual_usage.get('completion_tokens', 0)
            total_actual = actual_usage.get('total_tokens', input_tokens + output_tokens)

            print(f"ACTUAL API USAGE (Team): {total_actual:,} tokens")
            print(f"  - Total input (all agents): {input_tokens:,} tokens")
            print(f"  - Total output (all agents): {output_tokens:,} tokens")
            print()

            # Calculate difference
            input_diff = input_tokens - total_estimate
            diff_percent = (input_diff / total_estimate * 100) if total_estimate > 0 else 0

            print(f"DIFFERENCE: {'+' if input_diff >= 0 else ''}{input_diff:,} tokens ({'+' if diff_percent >= 0 else ''}{diff_percent:.1f}%)")

            # Warning if significant difference
            if abs(diff_percent) > 10:
                print(f"WARNING: Difference exceeds 10% - possible tokenizer mismatch or hidden overhead")
        else:
            print("ACTUAL API USAGE: No usage data available")

        print()
        self._log_separator_end()