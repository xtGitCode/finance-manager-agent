import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# add the source directory to the path to allow for module imports.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.tracey_agent import TraceyAgent
from agents.graph_state import GraphState

class TestAgentSOPAdherence:
    def setup_method(self):
        # set up a new agent and mock the llm before each test.
        with patch('agents.tracey_agent.ChatGroq') as mock_chatgroq:
            mock_llm = MagicMock()
            mock_chatgroq.return_value = mock_llm
            self.agent = TraceyAgent(groq_api_key="test_key")
            self.mock_llm = mock_llm
    
    def test_case_1_overspending_triggers_optimize_budget(self):
        """
        given a state with a detected spending deviation,
        when the agent node is run,
        then it should call the optimize_budget tool.
        """
        # arrange: create a state with a detected spending deviation.
        mock_state = {
            "user_context": {"name": "Test User", "location": "KL"},
            "budget": {"Food": 1000, "Entertainment": 500},
            "transactions": [
                {"budget_category": "Food", "amount": 200, "description": "Restaurant"}
            ],
            "deviation_detected": True,
            "deviation_details": {"Food": {"overage": 200}},
            "spending_analysis": {"spending_by_category": {"Food": 1200}},
            "tool_results": [
                {"tool": "get_transactions", "transactions_retrieved": 5},
                {"tool": "categorize_transactions", "transactions_categorized": 5},
                {"tool": "analyze_spending", "analysis_type": "spending_analysis", "deviation_detected": True}
            ],
            "current_step": 3,
            "messages": [],
            "tool_calls": []
        }
        
        # mock the llm to call the optimize_budget tool.
        mock_response = Mock()
        mock_response.content = '''
        {
            "needs_tool": true,
            "reasoning": "deviation detected, need to optimize.",
            "tool_call": {
                "tool": "optimize_budget",
                "args": {}
            }
        }
        '''
        self.mock_llm.invoke.return_value = mock_response
        
        # act: run the agent node with the mock state.
        result_state = self.agent.agent_node(mock_state)
        
        # assert: verify that optimize_budget was the next tool called.
        assert "tool_calls" in result_state
        assert len(result_state["tool_calls"]) > 0
        
        tool_call = result_state["tool_calls"][0]
        assert tool_call["tool"] == "optimize_budget"
    
    def test_case_2_no_overspending_completes_analysis(self):
        # arrange: create a state where analysis is done and no deviation was found.
        mock_state = {
            "user_context": {"name": "Test User", "location": "KL"},
            "budget": {"Food": 1000, "Entertainment": 500},
            "transactions": [
                {"budget_category": "Food", "amount": 200, "description": "Restaurant"}
            ],
            "deviation_detected": False,
            "deviation_details": {},
            "spending_analysis": {"spending_by_category": {"Food": 800}},
            "tool_results": [
                {"tool": "get_transactions"},
                {"tool": "categorize_transactions"},
                {"tool": "analyze_spending", "deviation_detected": False}
            ],
            "current_step": 3,
            "messages": [],
            "tool_calls": []
        }
        
        # act: check the completion status and run the agent node.
        is_complete_before = self.agent._is_analysis_complete(mock_state)
        result_state = self.agent.agent_node(mock_state)
        
        # assert: the analysis should be marked complete with no further tool calls.
        assert is_complete_before is True
        assert result_state.get("tool_calls", []) == []
        assert "final_plan" in result_state
        assert result_state["final_plan"]["status"] in ["good", "alert"]
    
    def test_sop_requires_both_optimization_and_research_after_deviation(self):
        """
        validates that after a deviation, the sop requires both optimize_budget
        and research_tips to run before analysis is considered complete.
        """
        # arrange: simulate a state where deviation was detected but only optimize_budget has run.
        state_with_only_optimization = {
            "deviation_detected": True,
            "tool_results": [
                {"tool": "get_transactions"},
                {"tool": "categorize_transactions"},
                {"tool": "analyze_spending"},
                {"tool": "optimize_budget"}  # research_tips is missing.
            ]
        }
        
        # act & assert: analysis should not be complete yet.
        is_complete_partial = self.agent._is_analysis_complete(state_with_only_optimization)
        assert is_complete_partial is False
        
        # arrange: now, simulate a state where both required tools have run.
        state_with_both_tools = {
            "deviation_detected": True,
            "tool_results": [
                {"tool": "get_transactions"},
                {"tool": "categorize_transactions"},
                {"tool": "analyze_spending"},
                {"tool": "optimize_budget"},
                {"tool": "research_tips"}  # both tools have run.
            ]
        }
        
        # act & assert: analysis should now be complete.
        is_complete_full = self.agent._is_analysis_complete(state_with_both_tools)
        assert is_complete_full is True
    
    def test_agent_prevents_infinite_loops(self):
        # arrange: create a state that has reached the maximum step limit.
        mock_state = {
            "current_step": 10,
            "messages": [],
            "tool_calls": []
        }
        
        # act: run the agent node.
        result_state = self.agent.agent_node(mock_state)
        
        # assert: the agent should stop and generate a final plan, not call more tools.
        assert result_state.get("tool_calls", []) == []
        assert "final_plan" in result_state
    
    def test_agent_fallback_parsing_works(self):
        # arrange: create a state that requires a tool call.
        mock_state = {
            "current_step": 1,
            "messages": [],
            "tool_calls": [],
            "tool_results": [],
            "transactions": [],
            "budget": {"Food": 1000},
            "user_context": {"name": "Test User", "location": "KL"}
        }
        
        # mock the llm to return a malformed, non-json response.
        mock_response = Mock()
        mock_response.content = "i need to categorize the transactions first before proceeding"
        self.mock_llm.invoke.return_value = mock_response
        
        # act: run the agent node.
        result_state = self.agent.agent_node(mock_state)
        
        # assert: the agent should use its fallback parsing to select an appropriate tool.
        if "tool_calls" in result_state and result_state["tool_calls"]:
            tool_call = result_state["tool_calls"][0]
            assert tool_call["tool"] in ["categorize_transactions", "get_transactions"]
        else:
            # if parsing fails completely, generating a final response is acceptable.
            assert "final_plan" in result_state

if __name__ == "__main__":
    pytest.main([__file__])