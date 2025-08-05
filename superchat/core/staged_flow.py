"""Staged chat flow manager for staged conversations.

This module manages the staged chat flow where users have individual conversations
with each agent first, then transition to a team debate with shared context.

Key responsibilities:
- Track progression through individual agent conversations
- Store original prompt and conversation transcripts
- Handle /promote command to advance through agents
- Manage transition from 1:1 phase to team debate phase
- Assemble comprehensive context for team phase

Think of it as the "conversation choreographer" - it orchestrates the staged
flow from individual discussions to team collaboration.
"""

import asyncio
from autogen_agentchat.teams import RoundRobinGroupChat
from superchat.utils.identifiers import get_model_identifier
from superchat.utils.model_resolver import get_display_name


class StagedFlowManager:
    """Manages staged chat flow: 1:1 conversations followed by team debate."""
    
    def __init__(self, config, agents, message_handler, agent_model_mapping):
        """Initialize staged flow manager with chat components.
        
        Args:
            config: SessionConfig instance
            agents: List of AutoGen agents
            message_handler: MessageHandler instance
            agent_model_mapping: Dict mapping agent names to model info
        """
        self.config = config
        self.agents = agents
        self.message_handler = message_handler
        self.agent_model_mapping = agent_model_mapping
        
        # Flow state management
        self.current_agent_index = 0
        self.phase = "individual"  # "individual" or "team"
        self.original_prompt = None
        self.awaiting_initial_question = True  # Flag to show special prompt for first question
        
        # Transcript storage for context assembly
        self.agent_transcripts = {}  # Dict mapping agent_index to {agent_name, model_name, messages[], promoted}
        
    def get_current_agent(self):
        """Get the current agent for 1:1 conversation."""
        if self.current_agent_index < len(self.agents):
            return self.agents[self.current_agent_index]
        return None
    
    def get_current_agent_info(self):
        """Get display information for current agent."""
        current_agent = self.get_current_agent()
        if not current_agent:
            return None
            
        # Get agent mapping info
        agent_info = self.agent_model_mapping.get(current_agent.name, {})
        model_name = agent_info.get('model_name', 'unknown')
        identifier = agent_info.get('identifier', '?')
        
        return {
            'agent': current_agent,
            'model_name': model_name,
            'identifier': identifier,
            'display_name': self._get_model_display_name(model_name)
        }
    
    def _get_model_display_name(self, model_name):
        """Get display name for a model."""
        model_config = self.message_handler.model_client_manager.get_model_config(model_name)
        if model_config:
            return get_display_name(model_config)
        return model_name
    
    def is_individual_phase(self):
        """Check if currently in individual conversation phase."""
        return self.phase == "individual"
    
    def is_team_phase(self):
        """Check if currently in team debate phase."""
        return self.phase == "team"
    
    def has_more_agents(self):
        """Check if there are more agents to chat with individually."""
        return self.current_agent_index < len(self.agents)
    
    async def handle_individual_message(self, message):
        """Handle message in individual conversation phase.
        
        Args:
            message: User message string
            
        Returns:
            bool: True if message was handled, False if phase completed
        """
        if not self.has_more_agents():
            return False
            
        current_agent = self.get_current_agent()
        if not current_agent:
            return False
        
        # Store original prompt if this is the first message
        if self.original_prompt is None:
            self.original_prompt = message
            self.awaiting_initial_question = False  # No longer awaiting initial question
            # Show status for first agent immediately after capturing initial question
            print(f"Status: {self.get_status_display()}")
            print()
            
        # Initialize transcript storage for current agent if not exists
        if self.current_agent_index not in self.agent_transcripts:
            agent_info = self.get_current_agent_info()
            self.agent_transcripts[self.current_agent_index] = {
                'agent_name': current_agent.name,
                'model_name': agent_info['model_name'],
                'display_name': agent_info['display_name'],
                'messages': [],
                'promoted': False
            }
            
        # Use existing single agent response handling with current agent index
        exchange_data = await self.message_handler.handle_single_agent_response(message, self.current_agent_index)
        
        # Capture the exchange in transcript
        if exchange_data:
            self.agent_transcripts[self.current_agent_index]['messages'].append({
                'user_message': exchange_data['user_message'],
                'agent_response': exchange_data['agent_response']
            })
        
        return True
    
    async def promote_current_agent(self):
        """Promote current agent and advance to next agent.
        
        Returns:
            dict: Status information about the promotion
        """
        if not self.has_more_agents():
            return {
                'success': False,
                'message': 'No current agent to promote',
                'phase': self.phase
            }
            
        current_agent_info = self.get_current_agent_info()
        if not current_agent_info:
            return {
                'success': False,
                'message': 'Could not get current agent info',
                'phase': self.phase
            }
            
        # Mark transcript as promoted
        if self.current_agent_index in self.agent_transcripts:
            self.agent_transcripts[self.current_agent_index]['promoted'] = True
        
        # Advance to next agent
        self.current_agent_index += 1
        
        # Check if we've promoted all agents
        if not self.has_more_agents():
            # All agents promoted - ready for team phase
            promoted_info = {
                'success': True,
                'message': f'Promoted {current_agent_info["display_name"]}. All agents promoted.',
                'phase': 'completing',
                'next_phase': 'team',
                'all_promoted': True
            }
        else:
            # More agents remaining
            next_agent_info = self.get_current_agent_info()
            promoted_info = {
                'success': True,
                'message': f'Promoted {current_agent_info["display_name"]}. Next: {next_agent_info["display_name"]}',
                'phase': self.phase,
                'next_agent': next_agent_info,
                'all_promoted': False,
                'should_auto_send': True  # Flag to indicate that original prompt should be sent after status display
            }
            
        return promoted_info
    
    async def auto_send_original_prompt(self):
        """Send original prompt to current agent if available.
        
        Returns:
            bool: True if prompt was sent, False otherwise
        """
        if self.original_prompt and self.has_more_agents():
            # Display the original prompt in grey to show what the AI is responding to
            print(f"\033[90m>> {self.original_prompt}\033[0m")
            print()
            
            await self.handle_individual_message(self.original_prompt)
            return True
        return False
    
    def get_status_display(self):
        """Get current status for display to user."""
        if self.is_individual_phase():
            if self.awaiting_initial_question:
                return "Input initial discussion question:"
            elif self.has_more_agents():
                agent_info = self.get_current_agent_info()
                if agent_info:
                    return f"1:1 with {agent_info['display_name']} [{agent_info['identifier']}]"
                else:
                    return "1:1 phase - no current agent"
            else:
                return "1:1 phase complete - ready for team debate"
        elif self.is_team_phase():
            return "Team debate phase"
        else:
            return f"Staged flow - {self.phase} phase"
    
    async def boot_current_agent(self):
        """Boot current agent (exclude from team debate) and advance to next agent.
        
        Returns:
            dict: Status information about the boot operation
        """
        if not self.has_more_agents():
            return {
                'success': False,
                'message': 'No current agent to boot',
                'phase': self.phase
            }
            
        current_agent_info = self.get_current_agent_info()
        if not current_agent_info:
            return {
                'success': False,
                'message': 'Could not get current agent info',
                'phase': self.phase
            }
            
        # Mark transcript as not promoted (booted)
        if self.current_agent_index in self.agent_transcripts:
            self.agent_transcripts[self.current_agent_index]['promoted'] = False
            
        # Advance to next agent
        self.current_agent_index += 1
        
        # Check if we've processed all agents
        if not self.has_more_agents():
            # All agents processed - check if any were promoted
            promoted_count = sum(1 for transcript in self.agent_transcripts.values() if transcript['promoted'])
            if promoted_count == 0:
                return {
                    'success': True,
                    'message': f'Booted {current_agent_info["display_name"]}. No agents promoted - cannot start team debate.',
                    'phase': 'completing',
                    'all_booted': True
                }
            else:
                return {
                    'success': True,
                    'message': f'Booted {current_agent_info["display_name"]}. Ready for team debate with {promoted_count} promoted agents.',
                    'phase': 'completing',
                    'next_phase': 'team',
                    'all_processed': True
                }
        else:
            # More agents remaining
            next_agent_info = self.get_current_agent_info()
            boot_info = {
                'success': True,
                'message': f'Booted {current_agent_info["display_name"]}. Next: {next_agent_info["display_name"]}',
                'phase': self.phase,
                'next_agent': next_agent_info,
                'all_processed': False,
                'should_auto_send': True  # Flag to indicate that original prompt should be sent after status display
            }
                
            return boot_info
    
    def restart_current_agent(self):
        """Restart current agent conversation (clear transcript and start fresh).
        
        Returns:
            dict: Status information about the restart operation
        """
        if not self.has_more_agents():
            return {
                'success': False,
                'message': 'No current agent to restart',
                'phase': self.phase
            }
            
        current_agent_info = self.get_current_agent_info()
        if not current_agent_info:
            return {
                'success': False,
                'message': 'Could not get current agent info',
                'phase': self.phase
            }
            
        # Clear transcript for current agent
        if self.current_agent_index in self.agent_transcripts:
            self.agent_transcripts[self.current_agent_index]['messages'] = []
            self.agent_transcripts[self.current_agent_index]['promoted'] = False
            
        return {
            'success': True,
            'message': f'Restarted conversation with {current_agent_info["display_name"]}. Transcript cleared.',
            'phase': self.phase,
            'current_agent': current_agent_info
        }
    
    def assemble_comprehensive_context(self):
        """Assemble comprehensive context for team debate phase.
        
        Format: Original Prompt + Agent A full transcript + Agent B full transcript + ...
        Only includes promoted transcripts, preserves agent setup order.
        
        Returns:
            str: Assembled context string ready for team debate
        """
        if not self.original_prompt:
            return ""
            
        context_parts = [f"Original Prompt:\n{self.original_prompt}\n"]
        
        # Process agents in setup order (by agent index)
        for agent_index in sorted(self.agent_transcripts.keys()):
            transcript = self.agent_transcripts[agent_index]
            
            # Only include promoted transcripts
            if not transcript['promoted'] or not transcript['messages']:
                continue
                
            # Add agent transcript section
            context_parts.append(f"\n--- {transcript['display_name']} Conversation ---")
            
            # Add all message exchanges in chronological order
            for exchange in transcript['messages']:
                context_parts.append(f"\nUser: {exchange['user_message']}")
                context_parts.append(f"{transcript['display_name']}: {exchange['agent_response']}")
                
        context_parts.append("\n--- Begin Team Debate ---")
        
        return "\n".join(context_parts)
    
    def get_promoted_agents(self):
        """Get list of promoted agents for team debate.
        
        Returns:
            list: List of agent objects that were promoted
        """
        promoted_agents = []
        for agent_index in sorted(self.agent_transcripts.keys()):
            transcript = self.agent_transcripts[agent_index]
            if transcript['promoted']:
                # Get the actual agent object
                if agent_index < len(self.agents):
                    promoted_agents.append(self.agents[agent_index])
                    
        return promoted_agents
    
    def create_team_with_context(self, promoted_agents, assembled_context):
        """Create new RoundRobinGroupChat team with assembled context.
        
        Args:
            promoted_agents: List of promoted agent objects
            assembled_context: Pre-assembled context string
            
        Returns:
            RoundRobinGroupChat: New team ready for debate with context
        """
        if not promoted_agents or len(promoted_agents) < 2:
            raise ValueError("Need at least 2 promoted agents to create team")
            
        # Create new team with promoted agents
        # Set max_turns = number of agents (each agent responds once per user message)
        team = RoundRobinGroupChat(promoted_agents, max_turns=len(promoted_agents))
        
        return team

    async def transition_to_team_phase(self):
        """Transition from individual phase to team debate phase.
        
        Assembles comprehensive context and prepares for team debate.
        
        Returns:
            dict: Transition status information with assembled context
        """
        if self.phase == "team":
            return {
                'success': False,
                'message': 'Already in team phase',
                'phase': self.phase
            }
            
        if self.has_more_agents():
            return {
                'success': False,
                'message': 'Cannot transition to team phase - agents still need promotion',
                'phase': self.phase,
                'remaining_agents': len(self.agents) - self.current_agent_index
            }
        
        # Check if any agents were promoted
        promoted_agents = self.get_promoted_agents()
        if not promoted_agents:
            return {
                'success': False,
                'message': 'Cannot start team debate - no agents were promoted',
                'phase': self.phase
            }
            
        if len(promoted_agents) < 2:
            return {
                'success': False,
                'message': 'Cannot start team debate - need at least 2 promoted agents',
                'phase': self.phase,
                'promoted_count': len(promoted_agents)
            }
        
        # Assemble comprehensive context
        assembled_context = self.assemble_comprehensive_context()
        
        # Create new team with promoted agents
        team = self.create_team_with_context(promoted_agents, assembled_context)
        
        # Mark transition to team phase
        self.phase = "team"
        
        return {
            'success': True,
            'message': f'Transitioned to team debate phase with {len(promoted_agents)} agents',
            'phase': self.phase,
            'promoted_agents': promoted_agents,
            'assembled_context': assembled_context,
            'context_length': len(assembled_context),
            'team': team
        }