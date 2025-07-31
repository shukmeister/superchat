"""Debug utilities for superchat - clean, readable API call logging."""

import os


class DebugLogger:
    """Simple debug logger for API calls and token usage."""
    
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.call_count = 0
    
    @classmethod
    def from_env(cls):
        """Create debug logger based on environment/arguments."""
        # Will be updated to use command line args
        enabled = os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')
        return cls(enabled=enabled)
    
    def log_api_call_start(self, model_name, messages):
        """Log the start of an API call with full message content."""
        if not self.enabled:
            return
            
        self.call_count += 1
        
        print(f"\n{'='*80}")
        print(f"🔍 API CALL #{self.call_count} [{model_name}]")
        print(f"📊 Total messages: {len(messages)}")
        print("-" * 80)
        
        for i, msg in enumerate(messages):
            content = str(msg.content) if hasattr(msg, 'content') else str(msg)
            role = getattr(msg, 'source', 'UNKNOWN').upper()
            
            print(f"[{i}] {role}:")
            print(f"    {content}")
            print()
    
    def log_api_call_end(self, response_content, usage_data=None):
        """Log the end of an API call with response and real token usage."""
        if not self.enabled:
            return
            
        print(f"⚡ RESPONSE:")
        if response_content:
            print(f"   Content: {response_content}")
        
        if usage_data:
            input_tokens = usage_data.get('prompt_tokens', 0)
            output_tokens = usage_data.get('completion_tokens', 0) 
            total_tokens = usage_data.get('total_tokens', input_tokens + output_tokens)
            print(f"📊 REAL TOKENS: {input_tokens} input + {output_tokens} output = {total_tokens} total")
        
        print("=" * 80)
    
    def log_estimated_tokens(self, estimated_tokens):
        """Log estimated tokens before API call (for comparison)."""
        if not self.enabled:
            return
        print(f"📊 ESTIMATED TOKENS: ~{estimated_tokens}")


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