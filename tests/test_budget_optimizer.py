import pytest
import sys
import os

# add the source directory to the python path for imports.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from tools.budget_optimizer import BudgetOptimizer

class TestBudgetOptimizer:
    """
    test suite for the budgetoptimizer tool.
    """
    def setup_method(self):
        """
        initializes a new budgetoptimizer instance before each test.
        """
        self.optimizer = BudgetOptimizer()
    
    def test_budget_optimization_with_overspending(self):
        """
        tests that a reallocation is proposed when one category is overspent
        and another has a surplus.
        """
        # define a scenario where food is over budget and entertainment is under-utilized.
        current_budget = {
            "Housing": 1800,
            "Food": 1200,
            "Transportation": 900,
            "Utilities": 600,
            "Healthcare": 300,
            "Entertainment": 900
        }
        
        baseline_spending = {
            "Housing": 1600,
            "Food": 800,
            "Transportation": 700,
            "Utilities": 400,
            "Healthcare": 200,
            "Entertainment": 400  # significantly under budget
        }
        
        # a new transaction that results in 'food' being over budget.
        new_transactions = {
            "Food": 500
        }
        
        mock_transactions = [
            {"budget_category": "Food", "amount": 150, "description": "Restaurant dining"},
            {"budget_category": "Food", "amount": 200, "description": "Grocery shopping"},
            {"budget_category": "Food", "amount": 150, "description": "Takeout food"}
        ]
        
        # calculate the total spending by combining baseline and new transactions.
        total_spending = baseline_spending.copy()
        for category, amount in new_transactions.items():
            total_spending[category] = total_spending.get(category, 0) + amount

        # execute the optimization analysis.
        result = self.optimizer.analyze_and_optimize(
            current_budget=current_budget,
            total_spending=total_spending,
            transactions=mock_transactions
        )
        
        # verify that an optimization is correctly identified and proposed.
        assert result["optimization_needed"] is True
        assert "recommendations" in result and len(result["recommendations"]) > 0
        
        # find the specific recommendation for reallocating from entertainment to food.
        food_reallocation = next(
            (rec for rec in result["recommendations"] 
             if rec["to_category"] == "Food" and rec["from_category"] == "Entertainment"), 
            None
        )
        
        assert food_reallocation is not None
        assert food_reallocation["amount"] > 0
        
        # check that the proposed budget reflects the reallocation.
        proposed_budget = result["proposed_budget"]
        assert proposed_budget["Food"] > current_budget["Food"]
        assert proposed_budget["Entertainment"] < current_budget["Entertainment"]
    
    def test_no_optimization_needed_when_all_within_budget(self):
        """
        ensures no optimization is proposed if all spending is within the budget limits.
        """
        # define a budget where all spending is comfortably within limits.
        current_budget = {
            "Housing": 1800,
            "Food": 1200,
            "Transportation": 900,
            "Utilities": 600,
            "Healthcare": 300,
            "Entertainment": 900
        }
        
        total_spending = {
            "Housing": 1600,
            "Food": 900,
            "Transportation": 700,
            "Utilities": 400,
            "Healthcare": 200,
            "Entertainment": 600
        }
        
        # run the optimization analysis.
        result = self.optimizer.analyze_and_optimize(
            current_budget=current_budget,
            total_spending=total_spending,
            transactions=[]
        )
        
        # assert that no optimization is needed.
        assert result["optimization_needed"] is False
        assert "message" in result
    
    def test_reallocation_respects_category_relationships(self):
        """
        validates that reallocations adhere to the predefined rules
        governing which categories can transfer funds to others.
        """
        # set up a scenario where housing is over budget and entertainment has a surplus.
        current_budget = {
            "Housing": 1800,
            "Food": 1200,
            "Transportation": 900,
            "Utilities": 600,
            "Healthcare": 300,
            "Entertainment": 900
        }
        
        baseline_spending = {
            "Housing": 1700,
            "Food": 1000,
            "Transportation": 800,
            "Utilities": 500,
            "Healthcare": 250,
            "Entertainment": 300  # large surplus
        }
        
        new_transactions = {
            "Housing": 200,  # pushes housing over budget
        }
        
        mock_transactions = [
            {"budget_category": "Housing", "amount": 200, "description": "Emergency repair"}
        ]
        
        # combine baseline and new spending to get total spending.
        total_spending = baseline_spending.copy()
        for category, amount in new_transactions.items():
            total_spending[category] = total_spending.get(category, 0) + amount
        
        # run the optimization analysis.
        result = self.optimizer.analyze_and_optimize(
            current_budget=current_budget,
            total_spending=total_spending,
            transactions=mock_transactions
        )
        
        # verify an optimization is needed.
        assert result["optimization_needed"] is True
        
        # check that a reallocation from entertainment to housing is proposed,
        # which is a valid transfer according to the tool's rules.
        housing_reallocation = next(
            (rec for rec in result["recommendations"] 
             if rec["to_category"] == "Housing" and rec["from_category"] == "Entertainment"), 
            None
        )
        
        assert housing_reallocation is not None

# this allows running the tests directly from the script.
if __name__ == "__main__":
    pytest.main([__file__])