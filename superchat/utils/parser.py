"""Input parsing utilities for commands and chat messages."""

def parse_input(user_input):
    """
    Parse user input to separate commands from chat messages.
    
    Args:
        user_input (str): Raw user input
        
    Returns:
        dict: {
            'type': 'command' or 'message',
            'command': command name (if type='command'),
            'args': list of command arguments (if type='command'),
            'message': original input (if type='message')
        }
    """
    if not user_input or not user_input.strip():
        return {
            'type': 'empty',
            'message': user_input
        }
    
    stripped_input = user_input.strip()
    
    if stripped_input.startswith('/'):
        # Parse as command
        parts = stripped_input.split()
        command = parts[0][1:]  # Remove the '/' prefix
        args = parts[1:] if len(parts) > 1 else []
        
        return {
            'type': 'command',
            'command': command,
            'args': args,
            'raw': user_input
        }
    else:
        # Parse as chat message
        return {
            'type': 'message',
            'message': stripped_input,
            'raw': user_input
        }