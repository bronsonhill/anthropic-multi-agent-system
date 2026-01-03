from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage, UserMessage, AgentDefinition
import asyncio
import json
from datetime import datetime
from .prompts import RESEARCH_LEAD_AGENT_PROMPT, RESEARCH_SUBAGENT_PROMPT, RESEARCH_CITATION_AGENT_PROMPT

class ResearchLeadAgent:
    def __init__(self, model: str = "claude-sonnet-4-5"):
        self.model = model
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Format prompts with current date if needed
        lead_prompt = RESEARCH_LEAD_AGENT_PROMPT.replace("{{.CurrentDate}}", current_date)
        subagent_prompt = RESEARCH_SUBAGENT_PROMPT.replace("{{.CurrentDate}}", current_date)
        citation_agent_prompt = RESEARCH_CITATION_AGENT_PROMPT.replace("{{.CurrentDate}}", current_date)

        # Researcher agent definition
        self.researcher_agent = AgentDefinition(
            description="Use this agent to search the web for information. Provide the agent with a detailed plan of action, and it will complete it for you. It is best to break down the task into smaller subtasks for multiple researchers to work on.",
            prompt=subagent_prompt,
            tools=["WebSearch", "Write"],
        )

        self.citation_agent = AgentDefinition(
            description="Use this agent to insert citations into the research.",
            prompt=citation_agent_prompt,
            tools=["Read", "Write"],
        )
        
        # ResearchOrchestratorAgent options
        self.options = ClaudeAgentOptions(
            system_prompt=lead_prompt,
            tools=["Task", "Read", "Write"],
            allowed_tools=["Task", "Read", "Write"],
            agents={"web_researcher_agents": self.researcher_agent, "citation_agent": self.citation_agent},
            model=self.model,
            permission_mode='bypassPermissions'
        )

    async def run(self, research_task: str) -> str:
        # use query(...) for single input and no conversation management
        result = ""
        async for message in query(
            prompt=research_task,
            options=self.options,
            ):
            # print(message)
            if isinstance(message, AssistantMessage):
                if message.error:
                    print(f"Assistant Error: {message.error}")
                for block in message.content:
                    if hasattr(block, "text"):
                        print(f"Claude: {block.text}")
                    elif hasattr(block, "thinking"): # <-- Missing: Reasoning
                        print(f"Thinking: {block.thinking}")
                    elif hasattr(block, "name"):     # <-- ToolUseBlock
                        print(f"Tool Call: {block.name}")
                        print(f"Arguments: {block.input}") # <-- Missing: Args
            
            elif isinstance(message, UserMessage):
                # Process blocks in UserMessage (which often contains tool results)
                for block in message.content:
                    if hasattr(block, "text"):
                        result = block.text
                    elif hasattr(block, "tool_use_id"): # <-- Missing: Tool Results
                        print(f"Tool Result for {block.tool_use_id}: {block.content}")

            elif isinstance(message, ResultMessage):
                print(f"Summary: {message.subtype}")
                if message.usage: # <-- Missing: Token Usage
                    print(f"Usage: {message.usage.get('total_tokens')} tokens")
                if message.total_cost_usd: # <-- Missing: Cost
                    print(f"Cost: ${message.total_cost_usd:.4f}")
        
        return result
