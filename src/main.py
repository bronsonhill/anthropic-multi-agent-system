import os
import argparse
import asyncio
from dotenv import load_dotenv
from src.agents.orchestrator import ResearchLeadAgent

async def main_async():
    load_dotenv()
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in environment variables.")
        return

    parser = argparse.ArgumentParser(description="Anthropic Multi-Agent Research System (SDK Version)")
    parser.add_argument("--query", type=str, help="The research query to execute", required=True)
    
    args = parser.parse_args()
    
    print("Initializing Agents (SDK)...")
    orchestrator = ResearchLeadAgent()
    
    print(f"Starting research on: {args.query}")
    print("-" * 50)
    
    await orchestrator.run(args.query)
    
    print("-" * 50)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
