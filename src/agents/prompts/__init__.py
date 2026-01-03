from pathlib import Path

# Get the directory of the current file
PROMPTS_DIR = Path(__file__).parent

def _load_prompt(filename: str) -> str:
    """Helper function to load prompt content from a markdown file."""
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        return ""
    return prompt_path.read_text(encoding="utf-8")

# Exported prompt strings
RESEARCH_LEAD_AGENT_PROMPT = _load_prompt("research_lead_agent.md")
RESEARCH_SUBAGENT_PROMPT = _load_prompt("research_subagent.md")
CITATIONS_AGENT_PROMPT = _load_prompt("citations_agent.md")

__all__ = [
    "RESEARCH_LEAD_AGENT_PROMPT",
    "RESEARCH_SUBAGENT_PROMPT",
    "CITATIONS_AGENT_PROMPT",
]
