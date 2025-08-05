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
        
        # Transcript storage for context assembly (Phase 2)
        self.agent_transcripts = []  # List of {agent_name, model_name, messages[]}
        
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
            
        # Use existing single agent response handling with current agent index
        await self.message_handler.handle_single_agent_response(message, self.current_agent_index)
        
        return True
    
    def promote_current_agent(self):
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
            
        # Mark transcript as promoted (Phase 2 implementation)
        # For Phase 1, we just track that this agent was promoted
        
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
                'all_promoted': False
            }
            
        return promoted_info
    
    def get_status_display(self):
        """Get current status for display to user."""
        if self.is_individual_phase():
            if self.has_more_agents():
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
    
    async def transition_to_team_phase(self):
        """Transition from individual phase to team debate phase.
        
        For Phase 1: Just marks transition complete
        For Phase 2: Will assemble context and create team
        
        Returns:
            dict: Transition status information
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
        
        # Phase 1: Simple transition marker
        self.phase = "team"
        
        return {
            'success': True,
            'message': 'Transitioned to team debate phase',
            'phase': self.phase,
            'note': 'Phase 1: Team debate not yet implemented'
        }