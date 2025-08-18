import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the source directory to the path for module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.tracey_agent import TraceyAgent
from agents.graph_state import GraphState

class TestAgenticBehavior:    
    def setup_method(self):
        with patch('agents.tracey_agent.ChatGroq') as mock_chatgroq:
            mock_llm = MagicMock()
            mock_chatgroq.return_value = mock_llm
            self.agent = TraceyAgent(groq_api_key="test_key")
            self.mock_llm = mock_llm

    def test_agent_decides_to_get_transactions_when_none_exist(self):
        """
        Given: A state with no transaction data
        When: Agent reasoning is triggered
        Then: Agent should decide to get transactions first
        """
        # Arrange: State with no transactions
        mock_state = {
            "user_context": {"name": "Test User", "location": "KL"},
            "budget": {"Food": 1000, "Entertainment": 500},
            "transactions": [],  # No transactions yet
            "tool_results": [],
            "current_step": 0,
            "messages": [],
            "tool_calls": []
        }
        
        # Mock LLM to decide it needs transactions
        mock_response = Mock()
        mock_response.content = '''
        {
            "needs_tool": true,
            "reasoning": "I need transaction data to analyze the user's spending patterns",
            "tool_call": {
                "tool": "get_transactions",
                "args": {}
            }
        }
        '''
        self.mock_llm.invoke.return_value = mock_response
        
        # Act: Run agent reasoning
        result_state = self.agent.agent_node(mock_state)
        
        # Assert: Agent should request transactions
        assert "tool_calls" in result_state
        assert len(result_state["tool_calls"]) > 0
        tool_call = result_state["tool_calls"][0]
        assert tool_call["tool"] == "get_transactions"
        assert result_state["agent_reasoning"] == "I need transaction data to analyze the user's spending patterns"

    def test_agent_decides_to_categorize_uncategorized_transactions(self):
        """
        Given: Transactions exist but are uncategorized
        When: Agent reasoning is triggered
        Then: Agent should decide to categorize them
        """
        # Arrange: State with uncategorized transactions
        mock_state = {
            "user_context": {"name": "Test User", "location": "KL"},
            "budget": {"Food": 1000, "Entertainment": 500},
            "transactions": [
                {"amount": 200, "description": "Restaurant"},  # No budget_category
                {"amount": 50, "description": "Movie"}
            ],
            "tool_results": [{"tool": "get_transactions", "transactions_retrieved": 2}],
            "current_step": 1,
            "messages": [],
            "tool_calls": []
        }
        
        # Mock LLM to decide it needs categorization
        mock_response = Mock()
        mock_response.content = '''
        {
            "needs_tool": true,
            "reasoning": "I have transactions but they're uncategorized, so I can't identify spending patterns",
            "tool_call": {
                "tool": "categorize_transactions",
                "args": {}
            }
        }
        '''
        self.mock_llm.invoke.return_value = mock_response
        
        # Act
        result_state = self.agent.agent_node(mock_state)
        
        # Assert
        assert result_state["tool_calls"][0]["tool"] == "categorize_transactions"
        assert "uncategorized" in result_state["agent_reasoning"]

    def test_agent_analyzes_spending_after_categorization(self):
        """
        Given: Categorized transactions but no analysis
        When: Agent reasoning is triggered  
        Then: Agent should decide to analyze spending
        """
        # Arrange: State with categorized transactions
        mock_state = {
            "user_context": {"name": "Test User", "location": "KL"},
            "budget": {"Food": 1000, "Entertainment": 500},
            "transactions": [
                {"amount": 200, "description": "Restaurant", "budget_category": "Food"},
                {"amount": 50, "description": "Movie", "budget_category": "Entertainment"}
            ],
            "tool_results": [
                {"tool": "get_transactions", "transactions_retrieved": 2},
                {"tool": "categorize_transactions", "transactions_categorized": 2}
            ],
            "current_step": 2,
            "messages": [],
            "tool_calls": []
        }
        
        # Mock LLM to decide it needs analysis
        mock_response = Mock()
        mock_response.content = '''
        {
            "needs_tool": true,
            "reasoning": "I need to understand if there are any budget concerns by analyzing spending patterns",
            "tool_call": {
                "tool": "analyze_spending",
                "args": {}
            }
        }
        '''
        self.mock_llm.invoke.return_value = mock_response
        
        # Act
        result_state = self.agent.agent_node(mock_state)
        
        # Assert
        assert result_state["tool_calls"][0]["tool"] == "analyze_spending"

    def test_agent_optimizes_budget_when_overspending_detected(self):
        """
        Given: Spending analysis shows deviation
        When: Agent reasoning is triggered
        Then: Agent should decide to optimize budget
        """
        # Arrange: State with detected overspending
        mock_state = {
            "user_context": {"name": "Test User", "location": "KL"},
            "budget": {"Food": 1000, "Entertainment": 500},
            "transactions": [{"amount": 1200, "budget_category": "Food"}],
            "deviation_detected": True,
            "deviation_details": {"Food": {"overage": 200}},
            "spending_analysis": {"spending_by_category": {"Food": 1200, "Entertainment": 0}},
            "tool_results": [
                {"tool": "get_transactions"},
                {"tool": "categorize_transactions"},
                {"tool": "analyze_spending", "deviation_detected": True}
            ],
            "current_step": 3,
            "messages": [],
            "tool_calls": []
        }
        
        # Mock LLM to decide optimization is needed
        mock_response = Mock()
        mock_response.content = '''
        {
            "needs_tool": true,
            "reasoning": "User is overspending significantly, I should help them rebalance their budget",
            "tool_call": {
                "tool": "optimize_budget",
                "args": {}
            }
        }
        '''
        self.mock_llm.invoke.return_value = mock_response
        
        # Act
        result_state = self.agent.agent_node(mock_state)
        
        # Assert
        assert result_state["tool_calls"][0]["tool"] == "optimize_budget"
        assert "overspending" in result_state["agent_reasoning"]

    def test_agent_researches_tips_for_specific_problems(self):
        """
        Given: Budget optimization has been done, but user needs practical advice
        When: Agent reasoning is triggered
        Then: Agent should decide to research specific tips
        """
        # Arrange: State after optimization
        mock_state = {
            "user_context": {"name": "Test User", "location": "KL"},
            "budget": {"Food": 1000, "Entertainment": 500},
            "deviation_detected": True,
            "deviation_details": {"Food": {"overage": 200}},
            "tool_results": [
                {"tool": "get_transactions"},
                {"tool": "categorize_transactions"},
                {"tool": "analyze_spending", "deviation_detected": True},
                {"tool": "optimize_budget", "recommendations": []}
            ],
            "current_step": 4,
            "messages": [],
            "tool_calls": []
        }
        
        # Mock LLM to decide research is needed
        mock_response = Mock()
        mock_response.content = '''
        {
            "needs_tool": true,
            "reasoning": "User needs practical advice for their specific overspending areas",
            "tool_call": {
                "tool": "research_tips",
                "args": {"topic": "food overspending", "category": "Food"}
            }
        }
        '''
        self.mock_llm.invoke.return_value = mock_response
        
        # Act
        result_state = self.agent.agent_node(mock_state)
        
        # Assert
        assert result_state["tool_calls"][0]["tool"] == "research_tips"
        assert result_state["tool_calls"][0]["args"]["category"] == "Food"

    def test_agent_concludes_when_sufficient_information_gathered(self):
        """
        Given: Comprehensive analysis has been completed
        When: Agent reasoning is triggered
        Then: Agent should decide to conclude with final recommendations
        """
        # Arrange: State with complete analysis
        mock_state = {
            "user_context": {"name": "Test User", "location": "KL"},
            "budget": {"Food": 1000, "Entertainment": 500},
            "deviation_detected": True,
            "spending_analysis": {"spending_by_category": {"Food": 1200}},
            "budget_optimization": {"optimization_needed": True, "recommendations": []},
            "tool_results": [
                {"tool": "get_transactions"},
                {"tool": "categorize_transactions"},
                {"tool": "analyze_spending", "deviation_detected": True},
                {"tool": "optimize_budget", "recommendations": []},
                {"tool": "research_tips", "recommendations": []}
            ],
            "current_step": 5,
            "messages": [],
            "tool_calls": []
        }
        
        # Mock LLM to decide analysis is complete
        mock_response = Mock()
        mock_response.content = '''
        {
            "ready_for_conclusion": true,
            "reasoning": "I have sufficient information to provide a comprehensive financial assessment",
            "status": "alert",
            "key_insights": ["Food category overspending detected"],
            "recommendations": ["Follow budget optimization plan", "Implement cost-saving tips"]
        }
        '''
        self.mock_llm.invoke.return_value = mock_response
        
        # Act
        result_state = self.agent.agent_node(mock_state)
        
        # Assert
        assert result_state.get("tool_calls", []) == []  # No more tool calls
        assert "final_plan" in result_state
        assert result_state["final_plan"]["status"] == "alert"
        assert len(result_state["final_plan"]["recommendations"]) > 0

    def test_agent_handles_no_overspending_scenario(self):
        """
        Given: Analysis shows no budget deviations
        When: Agent reasoning is triggered
        Then: Agent should conclude with positive assessment
        """
        # Arrange: State with good spending
        mock_state = {
            "user_context": {"name": "Test User", "location": "KL"},
            "budget": {"Food": 1000, "Entertainment": 500},
            "deviation_detected": False,
            "spending_analysis": {"spending_by_category": {"Food": 800, "Entertainment": 400}},
            "tool_results": [
                {"tool": "get_transactions"},
                {"tool": "categorize_transactions"},
                {"tool": "analyze_spending", "deviation_detected": False}
            ],
            "current_step": 3,
            "messages": [],
            "tool_calls": []
        }
        
        # Mock LLM to conclude positively
        mock_response = Mock()
        mock_response.content = '''
        {
            "ready_for_conclusion": true,
            "reasoning": "Analysis shows healthy spending patterns within budget limits",
            "status": "good",
            "key_insights": ["All categories within budget", "Good financial discipline"],
            "recommendations": ["Continue current spending patterns"]
        }
        '''
        self.mock_llm.invoke.return_value = mock_response
        
        # Act
        result_state = self.agent.agent_node(mock_state)
        
        # Assert
        assert result_state["final_plan"]["status"] == "good"
        assert "healthy" in result_state["agent_reasoning"]

    def test_safety_mechanisms_prevent_infinite_loops(self):
        """
        Given: Agent has reached maximum step limit
        When: Agent reasoning is triggered
        Then: Agent should force completion to prevent infinite loops
        """
        # Arrange: State at step limit
        mock_state = {
            "current_step": 10,  # At the safety limit
            "messages": [],
            "tool_calls": []
        }
        
        # Act: Agent should force completion regardless of LLM response
        result_state = self.agent.agent_node(mock_state)
        
        # Assert: Should generate final response and stop
        assert result_state.get("tool_calls", []) == []
        assert "final_plan" in result_state
        assert "safety" in result_state["final_plan"]["message"].lower()

    def test_agent_handles_malformed_llm_response(self):
        """
        Given: LLM returns malformed JSON
        When: Agent tries to parse response
        Then: Agent should use fallback logic to continue
        """
        # Arrange: State requiring decision
        mock_state = {
            "current_step": 1,
            "transactions": [],
            "budget": {"Food": 1000},
            "user_context": {"name": "Test User"},
            "tool_results": [],
            "messages": [],
            "tool_calls": []
        }
        
        # Mock LLM to return malformed response
        mock_response = Mock()
        mock_response.content = "I think I need to categorize the transactions but this isn't JSON"
        self.mock_llm.invoke.return_value = mock_response
        
        # Act
        result_state = self.agent.agent_node(mock_state)
        
        # Assert: Should either use fallback tool or generate final response
        is_valid_result = (
            (result_state.get("tool_calls") and 
             result_state["tool_calls"][0]["tool"] in ["categorize_transactions", "get_transactions"]) 
            or "final_plan" in result_state
        )
        assert is_valid_result


class TestToolRepetitionPrevention:
    """Test the tool repetition prevention mechanisms."""
    
    def setup_method(self):
        with patch('agents.tracey_agent.ChatGroq') as mock_chatgroq:
            mock_llm = MagicMock()
            mock_chatgroq.return_value = mock_llm
            self.agent = TraceyAgent(groq_api_key="test_key")

    def test_prevents_tool_repetition_loops(self):
        """
        Given: Recent tool results show repetitive pattern
        When: Agent checks if it should continue
        Then: Should return False to prevent loops
        """
        # Arrange: State with repetitive tool calls
        mock_state = {
            "current_step": 5,
            "tool_results": [
                {"tool": "analyze_spending"},
                {"tool": "optimize_budget"},
                {"tool": "analyze_spending"},
                {"tool": "analyze_spending"}  # Same tool called 3 times
            ]
        }
        
        # Act
        should_continue = self.agent._should_agent_continue(mock_state)
        
        # Assert
        assert should_continue is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
