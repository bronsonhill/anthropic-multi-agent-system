import unittest
from unittest.mock import MagicMock, patch
from src.agents.researcher import ResearchAgent
from src.agents.orchestrator import ResearchOrchestratorAgent
from src.tools.search import MockSearchTool

class TestAgents(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.search_tool = MockSearchTool()

    def test_research_agent_run(self):
        # Mock the response chain for ResearchAgent
        # 1. First call returns tool search request
        # 2. Second call returns final answer
        
        mock_msg_1 = MagicMock()
        mock_msg_1.stop_reason = "tool_use"
        mock_msg_1.content = [
            MagicMock(type="text", text="Thinking..."),
            MagicMock(type="tool_use", name="search", input={"query": "test query"}, id="tool_1")
        ]
        
        mock_msg_2 = MagicMock()
        mock_msg_2.stop_reason = "end_turn"
        mock_msg_2.content = [MagicMock(type="text", text="Final answer based on search")]
        
        self.mock_client.messages.create.side_effect = [mock_msg_1, mock_msg_2]
        
        agent = ResearchAgent(self.mock_client, self.search_tool)
        result = agent.run("Research test")
        
        self.assertEqual(result, "Final answer based on search")
        self.assertEqual(self.mock_client.messages.create.call_count, 2)

    def test_orchestrator_agent_run(self):
        # Mock Orchestrator flow
        # 1. Break down task -> returns JSON list
        # 2. Researcher runs (we mock ResearchAgent class for this)
        # 3. Aggregate results -> returns final summary
        
        # Mock 1: Decomposition
        mock_msg_decompose = MagicMock()
        mock_msg_decompose.content = [MagicMock(text='["Task 1", "Task 2"]')]
        
        # Mock 3: Aggregation
        mock_msg_aggregate = MagicMock()
        mock_msg_aggregate.content = [MagicMock(text="Final Aggregated Report")]
        
        self.mock_client.messages.create.side_effect = [mock_msg_decompose, mock_msg_aggregate]
        
        # We need to mock ResearchAgent to avoid nested client calls complexity here
        with patch('src.agents.orchestrator.ResearchAgent') as MockResearcher:
            instance = MockResearcher.return_value
            instance.run.return_value = "Sub-task result"
            
            orchestrator = ResearchOrchestratorAgent(self.mock_client, self.search_tool)
            result = orchestrator.run("Complex User Query")
            
            self.assertEqual(result, "Final Aggregated Report")
            # Should have created 2 researchers for 2 tasks
            self.assertEqual(MockResearcher.call_count, 2)

if __name__ == '__main__':
    unittest.main()
