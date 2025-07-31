"""Debug utilities for superchat - clean, readable API call logging."""

import os
import logging


class DebugLogger:
    """Simple debug logger for API calls and token usage."""
    
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