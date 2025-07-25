# Chat session setup and initialization utilities

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from superchat.core.model_client import ModelClientManager
from superchat.utils.identifiers import get_model_identifier
from superchat.utils.model_resolver import get_display_name
from superchat.utils.naming import make_safe_identifier
from superchat.core.message_handler import MessageHandler


class ChatSetup:
    """Handles all chat session initialization and configuration logic."""
    
    # Initialize setup handler with session configuration
    def __init__(self, config):
        self.config = config
        self.model_client_manager = ModelClientManager()
    
    # Initialize complete chat session with all components ready for runtime
    def setup_complete_session(self):
        """Returns fully configured MessageHandler ready for chat runtime."""
        if not self.config.models:
            raise ValueError("At least one model required for chat session")
        
        # Create agents and mapping
        agents = self.create_agents(self.config.models)
        agent_mapping = self.build_agent_mapping(agents, self.config.models)
        
        # Set up team for multi-agent mode
        is_multi_agent = len(self.config.models) > 1
        team = self.setup_team(agents, is_multi_agent) if is_multi_agent else None
        
        # Initialize message handler with all necessary dependencies
        message_handler = MessageHandler(
            self.config, 
            agents, 
            self.model_client_manager, 
            agent_mapping
        )
        # Pass the team reference to message handler for multi-agent mode
        message_handler.team = team
        
        return message_handler
    
    # Initialize all chat components and return them as a structured result
    def initialize_chat_components(self):
        """Returns (agents, agent_mapping, team) tuple for ChatSession."""
        if not self.config.models:
            raise ValueError("At least one model required for chat session")
        
        # Create agents and mapping
        agents = self.create_agents(self.config.models)
        agent_mapping = self.build_agent_mapping(agents, self.config.models)
        
        # Set up team for multi-agent mode
        is_multi_agent = len(self.config.models) > 1
        team = self.setup_team(agents, is_multi_agent) if is_multi_agent else None
        
        return agents, agent_mapping, team
    
    # Create AutoGen agents for the provided models
    def create_agents(self, models):
        agents = []
        
        for i, model_name in enumerate(models):
            # Create model client using modern AutoGen approach
            # Skip API key validation since it was already checked at startup
            model_client = self.model_client_manager.create_model_client(model_name, skip_validation=True)
            
            # Create AutoGen assistant agent with valid Python identifier name
            safe_name = make_safe_identifier(model_name)
            
            # Get appropriate system prompt for single or multi-agent mode
            is_multi_agent = len(models) > 1
            system_prompt = self.get_system_prompt(model_name, i, is_multi_agent)
            
            agent_name = f"agent_{safe_name}_{i}"
            agent = AssistantAgent(
                name=agent_name,
                model_client=model_client,
                system_message=system_prompt
            )
            
            agents.append(agent)
        
        return agents
    
    # Build mapping from agent names to their model information
    def build_agent_mapping(self, agents, models):
        agent_mapping = {}
        
        for i, (agent, model_name) in enumerate(zip(agents, models)):
            identifier = get_model_identifier(i)
            agent_mapping[agent.name] = {
                'model_name': model_name,
                'index': i,
                'identifier': identifier
            }
        
        return agent_mapping
    
    # Set up RoundRobinGroupChat team for multi-agent conversations
    def setup_team(self, agents, is_multi_agent):
        if not is_multi_agent:
            return None
        
        # Set up termination to stop after one complete round (each agent responds once)
        max_messages = len(agents) + 1  # +1 for the user message
        termination = MaxMessageTermination(max_messages=max_messages)
        return RoundRobinGroupChat(agents, termination_condition=termination)
    
    # Get appropriate system prompt for single or multi-agent mode
    def get_system_prompt(self, model_name, index, is_multi_agent):
        if is_multi_agent:
            # Get display name for this agent
            model_config = self.model_client_manager.get_model_config(model_name)
            display_name = get_display_name(model_config) if model_config else model_name
            
            # Build list of other agents in the conversation (excluding current one)
            other_agents = []
            for i, other_model_name in enumerate(self.config.models):
                # Skip the current agent when building other agents list
                if i != index:
                    other_config = self.model_client_manager.get_model_config(other_model_name)
                    other_display_name = get_display_name(other_config) if other_config else other_model_name
                    other_agents.append(other_display_name)
            
            other_agents_list = ", ".join(other_agents)
            
            return f"""You are {display_name}, participating in a live multi-agent debate with these other AI assistants: {other_agents_list}.

CRITICAL MULTI-AGENT SETUP:
- There are {len(self.config.models)} AI agents total in this conversation (including you)
- The other agents ({other_agents_list}) will ALSO respond to user messages
- You will see their actual responses in the conversation history
- DO NOT simulate, predict, or write responses for other agents
- Each agent responds independently, then the user decides if they want another round

CONVERSATION STRUCTURE:
- User asks a question or gives a prompt
- You respond with your perspective
- Other agents also respond with their perspectives  
- User can then ask follow-up questions or request another round
- You can reference what other agents actually said in previous rounds

Guidelines:
- BE CONCISE
- DONT USE STYLIZED FORMATTING LIKE BOLDING, ITALICS, EMOJIS, ETC
- Provide thoughtful, well-reasoned responses to user questions
- Reference other agents' actual previous responses when relevant
- If you disagree with another agent, explain your reasoning clearly
- Build upon ideas from previous messages in the conversation
- Be concise and direct in your responses
- Do not use emojis, bold text, italics, or other stylistic formatting
- Focus on providing accurate and helpful information
- You may identify yourself as {display_name} when appropriate
- BE CONCISE

REMEMBER: You are having a real conversation with other AI agents who will actually respond. Do not write their responses for them."""
        else:
            return self.config.get_system_prompt() or "You are a helpful assistant that answers questions accurately and concisely. Be concise and straightforward in your responses. Do not use emojis, bold text, italics, or other stylistic formatting. NEVER ask the user questions - provide direct answers to their queries. DO NOT PROMPT OR ASK THE USER QUESTIONS."