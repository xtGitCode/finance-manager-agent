import sys
import os
from typing import Dict, Any, Literal
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from langgraph.graph import StateGraph, END
from agents.graph_state import GraphState
from agents.tracey_agent import TraceyAgent 
from tools.plaid_tool import PlaidTool
from tools.research_tool import ResearchTool
from tools.categorization_tool import SemanticCategorizer
from tools.budget_optimizer import BudgetOptimizer

load_dotenv()

class FinancialGuardianSystem:
    def __init__(self):
        print("🤖 Initializing Financial Agent System...")
        self.agent = TraceyAgent(groq_api_key=os.getenv("GROQ_API_KEY"))
        
        # initialize tools
        self.plaid_tool = PlaidTool()
        self.categorizer = SemanticCategorizer()
        self.budget_optimizer = BudgetOptimizer()
        
        tavily_key = os.getenv("TAVILY_API_KEY")
        self.research_tool = ResearchTool(tavily_key) if tavily_key else None
        
        self.app = self._build_graph()
        print("✅ Financial Agent System ready!")
    
    def _build_graph(self):
        workflow = StateGraph(GraphState)
        
        # add nodes
        workflow.add_node("agent", self.autonomous_agent_wrapper)
        workflow.add_node("tool_node", self.enhanced_tool_node)
        
        # set entry point
        workflow.set_entry_point("agent")
        
        # add conditional routing
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {"tool_node": "tool_node", END: END}
        )
        
        # loop back from tools to agent for continued reasoning
        workflow.add_edge("tool_node", "agent")
        
        return workflow.compile(debug=True)
    
    def autonomous_agent_wrapper(self, state: GraphState) -> GraphState:
        print(f"\n🧠 Agent Reasoning (Step {state.get('current_step', 0) + 1})")
        
        current_step = state.get("current_step", 0)
        if current_step >= 10:  # limit to prevent infinity loops
            print("   - Safety: Maximum exploration reached")
            return self.agent._generate_final_response(state, "Comprehensive analysis completed")
        
        # check for tool repetition patterns
        recent_tools = [result.get("tool", "") for result in state.get("tool_results", [])[-3:]]
        if len(recent_tools) >= 2 and len(set(recent_tools)) <= 1:
            print(f"   - Safety: Tool repetition detected, ending analysis")
            return self.agent._generate_final_response(state, "Analysis complete - prevented infinite loop")
        
        return self.agent.agent_node(state)
    
    def enhanced_tool_node(self, state: GraphState) -> GraphState:
        updated_state = state.copy()
        tool_calls = state.get("tool_calls", [])
        
        if not tool_calls:
            return updated_state
        
        if updated_state.get("tool_results") is None:
            updated_state["tool_results"] = []
        
        for call in tool_calls:
            tool_name = call.get("tool")
            args = call.get("args", {})
            
            print(f"    🔧 Executing: {tool_name}")
            
            try:
                # IMPORTANT: Pass the updated_state instead of the original state
                # This ensures each tool gets the latest state with previous tool results
                tool_output = self._execute_tool(tool_name, args, updated_state)
                
                print(f"    🔧 Tool {tool_name} returned: {list(tool_output.keys()) if tool_output else 'EMPTY'}")
                
                updated_state = self._update_state_with_tool_result(
                    updated_state, tool_name, tool_output
                )
                updated_state["tool_results"].append(tool_output)
                
                print(f"    🔧 State after {tool_name}: {list(updated_state.keys())}")
                if tool_name == "analyze_spending":
                    print(f"    🔧 VERIFY: spending_analysis in state: {'spending_analysis' in updated_state}")
                
            except Exception as e:
                error_output = {"error": f"Tool {tool_name} failed: {str(e)}"}
                updated_state["tool_results"].append(error_output)
                print(f"Tool Error: {e}")
        
        # clear tool calls for next iteration
        updated_state["tool_calls"] = []
        return updated_state
    
    def _execute_tool(self, tool_name: str, args: Dict, state: GraphState) -> Dict[str, Any]:
        if tool_name == "get_transactions":
            transactions = self.plaid_tool.get_transactions()
            return {
                "tool": "get_transactions",
                "transactions_retrieved": len(transactions),
                "transactions": transactions
            }
        
        elif tool_name == "categorize_transactions":
            categorized_txns = self.categorizer.run(state['transactions'])
            return {
                "tool": "categorize_transactions",
                "transactions_categorized": len(categorized_txns),
                "categorized_transactions": categorized_txns
            }
        
        elif tool_name == "analyze_spending":
            analysis = self.plaid_tool.analyze_spending(
                state['transactions'], 
                state['budget'],
                # This is the new line that passes the baseline spending data
                state.get('baseline_spending', {})
            )
            return {
                "tool": "analyze_spending",
                "analysis_type": "spending_analysis",
                **analysis
            }
        
        elif tool_name == "research_tips":
            return self._execute_autonomous_research(args, state)
        
        elif tool_name == "optimize_budget":
            # --- THIS IS THE FIX ---
            
            print(f"\n🔧 MAIN.PY DEBUG - optimize_budget (DETAILED):")
            print(f"  Full state keys: {list(state.keys())}")
            print(f"  Deviation detected in state: {state.get('deviation_detected', 'NOT FOUND')}")
            print(f"  Deviation details in state: {state.get('deviation_details', 'NOT FOUND')}")
            
            # Get the complete analysis result FROM THE STATE where it was stored
            analysis_result = state.get("spending_analysis", {})
            
            print(f"  Analysis result found: {bool(analysis_result)}")
            print(f"  Analysis result keys: {list(analysis_result.keys()) if analysis_result else 'EMPTY'}")
            
            # Check that we actually got something, just in case
            if not analysis_result:
                print(f"  ERROR: Spending analysis data not found in state.")
                return {"error": "Spending analysis data not found in state."}
            
            # Get the final, correct total spending dictionary from the analysis result
            total_spending_data = analysis_result.get("spending_by_category", {})
            
            print(f"  Total spending data extracted: {total_spending_data}")
            print(f"  Total spending data empty: {not bool(total_spending_data)}")
            
            if not total_spending_data:
                print(f"  ERROR: No spending_by_category found in analysis result")
                return {"error": "No spending data found in analysis result"}
            
            # --- END OF FIX ---
            
            # Call the simplified optimizer tool with the correct data
            optimization = self.budget_optimizer.analyze_and_optimize(
                current_budget=state['budget'],
                total_spending=total_spending_data,  # <-- PASS THE CORRECT TOTALS
                transactions=state.get('transactions', [])
            )
            return {"tool": "optimize_budget", **optimization}
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def _execute_autonomous_research(self, args: Dict, state: GraphState) -> Dict[str, Any]:
        if not self.research_tool:
            return {"error": "Research tool not available"}
        
        # agent can specify research parameters
        topic = args.get("topic", "financial optimization")
        category = args.get("category", "general")
        
        # extract context for better research
        user_context = state.get("user_context", {})
        location = user_context.get("location", "general")
        
        # calculate relevant financial context from detected deviations
        budget_deficit = 0
        transaction_details = None
        research_category = "general"
        
        # use the actual deviation details for targeted research
        deviation_details = state.get("deviation_details", {})
        if deviation_details:
            # find the category with the highest overage for research
            max_overage_category = max(deviation_details.items(), 
                                     key=lambda x: x[1].get('overage', 0))
            research_category = max_overage_category[0] 
            budget_deficit = max_overage_category[1].get('overage', 0)
            transaction_details = max_overage_category[1]
            
            print(f"   - Research target: {research_category} (RM{budget_deficit:.0f} overage)")
            print(f"   - Sample transactions: {[t.get('description', '') for t in transaction_details.get('transaction_details', [])[:2]]}")
        
        return self.research_tool.search_cost_saving_tips(
            topic=f"{research_category.lower()} overspending",  # more specific topic
            category=research_category,  # use the actual overspent category
            location=location, 
            budget_deficit=budget_deficit, 
            transaction_details=transaction_details
        )
    
    def _update_state_with_tool_result(self, state: GraphState, tool_name: str, result: Dict) -> GraphState:
        print(f"\n🔧 UPDATING STATE with {tool_name} result:")
        print(f"  Result keys: {list(result.keys()) if result else 'EMPTY RESULT'}")
        print(f"  State keys before update: {list(state.keys())}")
        
        if tool_name == "get_transactions" and "transactions" in result:
            state["transactions"] = result["transactions"]
            print(f"  Updated transactions: {len(state['transactions'])} items")
        
        elif tool_name == "categorize_transactions" and "categorized_transactions" in result:
            state["transactions"] = result["categorized_transactions"]
            print(f"  Updated categorized transactions: {len(state['transactions'])} items")
        
        elif tool_name == "analyze_spending":
            print(f"  *** CRITICAL STATE UPDATE FOR analyze_spending ***")
            print(f"  Result deviation_detected: {result.get('deviation_detected', 'NOT FOUND')}")
            print(f"  Result spending_by_category keys: {list(result.get('spending_by_category', {}).keys())}")
            
            state["deviation_detected"] = result.get("deviation_detected", False)
            state["deviation_details"] = result.get("deviation_details", {})
            state["spending_analysis"] = result
            
            print(f"  State after update - deviation_detected: {state.get('deviation_detected')}")
            print(f"  State after update - spending_analysis keys: {list(state.get('spending_analysis', {}).keys())}")
            print(f"  *** END CRITICAL UPDATE ***")
        
        elif tool_name == "optimize_budget":
            state["budget_optimization"] = result
            # if optimization proposes a new budget, store it for the UI
            if result.get("optimization_needed") and result.get("proposed_budget"):
                state["rebalanced_budgets"] = result["proposed_budget"]
            print(f"  Updated budget_optimization: optimization_needed = {result.get('optimization_needed')}")
        
        print(f"  State keys after update: {list(state.keys())}")
        return state
    
    def _should_continue(self, state: GraphState) -> Literal["tool_node", "__end__"]:
        if state.get("tool_calls"):
            return "tool_node"
        return END
    
    def create_initial_state(self, user_context: Dict, budget: Dict) -> GraphState:
        return {
            "user_context": user_context,
            "budget": budget,
            "transactions": [],
            "messages": [{"role": "user", "content": "Please analyze my financial situation"}],
            "tool_results": [],
            "current_step": 0,
            "max_steps": 10, 
            "deviation_detected": False,
            "deviation_details": {},
            "research_queries": [],
            "tool_calls": [],
            "recovery_recommendations": [],
            "budget_status": "unknown"
        }
    
    def run_analysis(self, user_context: Dict, budget: Dict):
        initial_state = self.create_initial_state(user_context, budget)
        
        print("Starting Autonomous Financial Analysis...")
        print(f"User: {user_context.get('name', 'Unknown')}")
        print(f"Location: {user_context.get('location', 'Unknown')}")
        print(f"Budget Categories: {list(budget.keys())}")
        
        for output in self.app.stream(initial_state, {"recursion_limit": 20}):
            yield output
