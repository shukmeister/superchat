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
    
    def __init__(self, config, staged_flow_manager, model_client_manager, chat_session=None):
        """Initialize command handler with required dependencies."""
        self.config = config
        self.staged_flow_manager = staged_flow_manager
        self.model_client_manager = model_client_manager
        self.chat_session = chat_session
    
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
        elif command == 'boot':
            return await self._handle_boot()
        elif command == 'restart':
            return await self._handle_restart()
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
            print("/promote command is only available in staged flow individual phase")
            print()
            return True, False  # continue, don't exit
        
        # Execute promotion
        result = await self.staged_flow_manager.promote_current_agent()
        print(result['message'])
        
        if result.get('all_promoted', False):
            # All agents promoted - transition to team phase
            if self.chat_session:
                # Use chat session's transition method which handles context injection
                success = await self.chat_session.transition_staged_to_team_debate()
                if not success:
                    print("Failed to transition to team debate.")
            else:
                # Fallback for cases where chat_session is not available
                transition_result = await self.staged_flow_manager.transition_to_team_phase()
                print(transition_result['message'])
                if transition_result.get('note'):
                    print(transition_result['note'])
        else:
            # Show status for next agent
            print(f"Status: {self.staged_flow_manager.get_status_display()}")
            print()
            
            # Auto-send original prompt to next agent if flagged
            if result.get('should_auto_send', False):
                await self.staged_flow_manager.auto_send_original_prompt()
            
        return True, False  # continue, don't exit
    
    async def _handle_boot(self):
        """Handle /boot command."""
        # Check if boot is available
        if not (self.staged_flow_manager and self.staged_flow_manager.is_individual_phase()):
            print("/boot command is only available in staged flow individual phase")
            print()
            return True, False  # continue, don't exit
        
        # Execute boot
        result = await self.staged_flow_manager.boot_current_agent()
        print(result['message'])
        
        if result.get('all_processed', False) and result.get('next_phase') == 'team':
            # All agents processed and some promoted - transition to team phase
            if self.chat_session:
                # Use chat session's transition method which handles context injection
                success = await self.chat_session.transition_staged_to_team_debate()
                if not success:
                    print("Failed to transition to team debate.")
            else:
                # Fallback for cases where chat_session is not available
                transition_result = await self.staged_flow_manager.transition_to_team_phase()
                print(transition_result['message'])
                if transition_result.get('note'):
                    print(transition_result['note'])
        elif result.get('all_booted', False):
            # All agents booted - cannot continue
            print("No agents available for team debate. Returning to setup mode.")
            print()
        else:
            # Show status for next agent
            print(f"Status: {self.staged_flow_manager.get_status_display()}")
            print()
            
            # Auto-send original prompt to next agent if flagged
            if result.get('should_auto_send', False):
                await self.staged_flow_manager.auto_send_original_prompt()
            
        return True, False  # continue, don't exit
    
    async def _handle_restart(self):
        """Handle /restart command."""
        # Check if restart is available
        if not (self.staged_flow_manager and self.staged_flow_manager.is_individual_phase()):
            print("/restart command is only available in staged flow individual phase")
            print()
            return True, False  # continue, don't exit
        
        # Execute restart
        result = self.staged_flow_manager.restart_current_agent()
        print(result['message'])
        print(f"Status: {self.staged_flow_manager.get_status_display()}")
        print()
            
        return True, False  # continue, don't exit
    
    async def _handle_unknown_command(self, command):
        """Handle unknown commands."""
        print(f"Unknown command: /{command}")
        print()
        return True, False  # continue, don't exit