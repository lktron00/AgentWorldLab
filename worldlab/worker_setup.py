def register():
    """Ray worker hook: register our policy using AgentSociety's public registry."""
    from agentsociety2.registry import get_registry
    from worldlab.scripted_agent import LabAgent
    get_registry().register_agent_module("LabAgent", LabAgent)
