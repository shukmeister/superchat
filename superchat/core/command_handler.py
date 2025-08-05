"""Chat command handler for processing user commands.

This module handles all chat commands like /exit, /stats, /promote, etc.
It's extracted from the main chat loop to keep concerns separate and make
commands easier to test and maintain.

Key responsibilities:
- Parse and validate commands
- Execute command logic
- Return results to the chat loop
- Handle command-specific error cases

Think of it as the "waiter" who takes orders (commands) and handles
special requests, while the main chat loop coordinates everything.
"""

from superchat.utils.stats import display_stats, display_exit_summary


class ChatCommandHandler:
    """Handles all chat commands in a focused, testable way."""
    
    def __init__(self, config, staged_flow_manager, model_client_manager):
        """Initialize command handler with required dependencies."""
        self.config = config
        self.staged_flow_manager = staged_flow_manager
        self.model_client_manager = model_client_manager
    
    async def handle_command(self, command, args):
        """Handle a command and return (should_continue, should_exit).
        
        Args:
            command: Command name (without /)
            args: List of command arguments
            
        Returns:
            tuple: (should_continue, should_exit)
                should_continue: True if chat loop should continue to next iteration
                should_exit: True if chat loop should break/exit
        """
        if command == 'exit':
            return await self._handle_exit()
        elif command == 'stats':
            return await self._handle_stats()
        elif command == 'promote':
            return await self._handle_promote()
        else:
            return await self._handle_unknown_command(command)
    
    async def _handle_exit(self):
        """Handle /exit command."""
        stats = self.config.get_stats()
        display_exit_summary(stats, self.config.models, self.model_client_manager)
        print("Terminating connection")
        return False, True  # don't continue, do exit
    
    async def _handle_stats(self):
        """Handle /stats command."""
        stats = self.config.get_stats()
        display_stats(stats, self.config.models, self.model_client_manager)
        print()
        return True, False  # continue, don't exit
    
    async def _handle_promote(self):
        """Handle /promote command."""
        # Check if promote is available
        if not (self.staged_flow_manager and self.staged_flow_manager.is_individual_phase()):
            print()
            print("/promote command is only available in staged flow individual phase")
            print()
            return True, False  # continue, don't exit
        
        # Execute promotion
        result = self.staged_flow_manager.promote_current_agent()
        print(result['message'])
        
        if result.get('all_promoted', False):
            # All agents promoted - transition to team phase
            transition_result = await self.staged_flow_manager.transition_to_team_phase()
            print(transition_result['message'])
            if transition_result.get('note'):
                print(transition_result['note'])
        else:
            # Show status for next agent
            print(f"Status: {self.staged_flow_manager.get_status_display()}")
            print()
            
        return True, False  # continue, don't exit
    
    async def _handle_unknown_command(self, command):
        """Handle unknown commands."""
        print(f"Unknown command: /{command}")
        print()
        return True, False  # continue, don't exit