import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from src.agents.researcher import ResearchAgent
from src.agents.orchestrator import ResearchOrchestratorAgent
from claude_agent_sdk import AssistantMessage

class TestSDKAgents(unittest.TestCase):
    def test_research_agent_run(self):
        # Mock query
        with patch('src.agents.researcher.query') as mock_query:
            
            # Helper to create an async iterator mock
            async def async_iter(items):
                for item in items:
                    yield item

            # Create a mock AssistantMessage
            mock_message = AssistantMessage(
                model="test-model",
                content=[MagicMock(text="SDK Result")]
            )
            
            mock_query.return_value = async_iter([mock_message])
            
            agent = ResearchAgent()
            
            # Test run
            result = asyncio.run(agent.run("Task"))
            self.assertEqual(result, "SDK Result")

    def test_orchestrator_agent_run(self):
         with patch('src.agents.orchestrator.query') as mock_query, \
              patch('src.agents.orchestrator.ResearchAgent') as MockResearchAgentClass:

            # Mock Orchestrator query responses
            # First call: Decomposition
            mock_msg_decompose = AssistantMessage(
                model="test-model",
                content=[MagicMock(text='["Task A", "Task B"]')]
            )
            # Second call: Aggregation
            mock_msg_aggregate = AssistantMessage(
                model="test-model",
                content=[MagicMock(text="Final Answer")]
            )

            # We need side_effect to return different iterators for each call
            async def async_iter_decompose(*args, **kwargs):
                yield mock_msg_decompose
                
            async def async_iter_aggregate(*args, **kwargs):
                yield mock_msg_aggregate

            mock_query.side_effect = [async_iter_decompose(), async_iter_aggregate()]

            # Mock Researcher
            mock_researcher = MockResearchAgentClass.return_value
            async def async_research(task):
                return f"Result for {task}"
            mock_researcher.run.side_effect = async_research
            
            orchestrator = ResearchOrchestratorAgent()
            result = asyncio.run(orchestrator.run("Query"))
            
            self.assertEqual(result, "Final Answer")
            # Verify decomposition happened (2 query calls: 1 decompose, 1 aggregate)
            self.assertEqual(mock_query.call_count, 2)

if __name__ == '__main__':
    unittest.main()
