from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage, UserMessage, AgentDefinition
import asyncio
import json
from datetime import datetime
from .prompts import RESEARCH_LEAD_AGENT_PROMPT, RESEARCH_SUBAGENT_PROMPT

class ResearchLeadAgent:
    def __init__(self, model: str = "claude-opus-4-5-20251101"):
        self.model = model
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Format prompts with current date if needed
        lead_prompt = RESEARCH_LEAD_AGENT_PROMPT.replace("{{.CurrentDate}}", current_date)
        subagent_prompt = RESEARCH_SUBAGENT_PROMPT.replace("{{.CurrentDate}}", current_date)

        # Researcher agent definition
        self.researcher_agent = AgentDefinition(
            description="Use this agent to search the web for information. Provide the agent with a detailed plan of action, and it will complete it for you. It is best to break down the task into smaller subtasks for multiple researchers to work on.",
            prompt=subagent_prompt,
            tools=["WebSearch", "Write"],
            allowed_tools=["WebSearch", "Write"],
        )
        
        # ResearchOrchestratorAgent options
        self.options = ClaudeAgentOptions(
            system_prompt=lead_prompt,
            tools=["Task", "Read"],
            allowed_tools=["Task", "Read"],
            agents={"web_researcher_agents": self.researcher_agent},
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
                for block in message.content:
                    if hasattr(block, "text"):
                        print(block.text)              # Claude's reasoning
                    elif hasattr(block, "name"):
                        print(f"Tool: {block.name}")   # Tool being called
            if isinstance(message, UserMessage):
                for block in message.content:
                    if hasattr(block, "text"):
                        result = block.text
            elif isinstance(message, ResultMessage):
                print(f"Done: {message.subtype}")      # Final result
        
        return result
