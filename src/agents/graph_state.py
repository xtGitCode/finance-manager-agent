# src/agents/graph_state.py
from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime

class GraphState(TypedDict):    
    # financial data
    transactions: List[Dict[str, Any]]
    budget: Dict[str, float]
    user_context: Dict[str, str]
    baseline_spending: Dict[str, float]  # 🔥 CRITICAL: Add missing baseline_spending field
    
    # memory
    messages: List[Dict[str, str]]
    
    # decision tracking and analysis
    current_analysis: Optional[str]
    deviation_detected: bool
    deviation_details: Optional[Dict[str, Any]]
    research_queries: List[str]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    
    # analysis results (🔥 CRITICAL: Add missing analysis fields)
    spending_analysis: Optional[Dict[str, Any]]
    budget_optimization: Optional[Dict[str, Any]]
    
    # final output
    final_plan: Optional[Dict[str, Any]]
    budget_status: str  # "good" or "alert"
    recovery_recommendations: List[Dict[str, Any]]
    
    # execution tracking
    current_step: int
    max_steps: int  # to prevent overthinking and stuck in loop
